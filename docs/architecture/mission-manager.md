# Mission Manager 与小智任务接口

## 数据流

```text
语音 -> 小智 ASR/LLM -> ESP32 设备侧 MCP 工具
     -> HTTPS/HTTP JSON -> Raspberry Pi Mission Manager
     -> Nav2 NavigateToPose -> /cmd_vel -> C Board 安全控制
     -> 机械臂高层任务边界（不含机械臂实现）
     -> /wheelbot/mission/status + REST/事件流 -> 小智/Web
```

ESP32 只负责自然语言入口和结构化任务提交。任务调度、状态仲裁、导航与失败处理位于树莓派。

## 任务类型

- `NAVIGATE`：前往一个已标定语义位置。
- `FETCH_ITEM`：前往工作区，等待机械臂明确报告装载成功，再返回。
- `RETURN_HOME`：取消当前任务并创建返航任务。

同一时刻只允许一个活动任务。完全相同的 `request_id` 重试返回原任务，不重复执行；如果同一
`request_id` 携带不同任务内容则拒绝。返航替换会先完整校验新请求，再原子取消旧任务，避免
异常或重试请求误取消当前任务。

## 状态机

```text
PENDING -> NAVIGATING -> ARRIVED -> COMPLETED
                         |
                         +-> WAITING_FOR_ARM -> ARM_RUNNING -> LOADED
                                                      -> RETURNING -> COMPLETED

任一非终态 -> FAILED 或 CANCELLED
```

服务重启时，未完成任务恢复为 `FAILED/MANAGER_RESTARTED`，不会自动重放物理动作。

## REST API

默认监听 `0.0.0.0:8080`，除 `/healthz` 外使用 `Authorization: Bearer <token>`。

```http
POST /api/v1/missions
Content-Type: application/json

{
  "request_id": "xiaozhi-001",
  "task_type": "FETCH_ITEM",
  "target_item": "矿泉水",
  "target_location": "arm_zone",
  "return_location": "home"
}
```

查询与取消：

- `GET /api/v1/missions/current`
- `GET /api/v1/missions/{mission_id}`
- `GET /api/v1/missions`
- `GET /api/v1/system/status`（位姿、C 板、电池、故障、导航/机械臂阶段和感知可用性）
- `GET /api/v1/events?after=<event_id>&wait_ms=<0..25000>`（有序任务事件长轮询）
- `POST /api/v1/missions/{mission_id}/cancel`

所有 Web 客户端都应读取这个 API 或 `/wheelbot/mission/status`，不要维护第二套任务状态。
浏览器访问 `http://<robot-ip>:8080/` 可打开随包部署的 Mission Console；Bearer token 仅保存在
浏览器当前会话，页面展示任务阶段、底盘链路、电池、故障、位姿和最近事件，并支持取消/返航。

## 机器人到小智反馈

每次状态变化会生成一个 `wheelbot.mission_state_changed` 事件，并映射为 `speak_text`，例如
“已经到达工作区，正在等待机械臂”“东西已经拿到了，我正在回来”“任务完成”。配置
`feedback_webhook_url` 后，Mission Manager 在独立线程中向小智服务端适配器 POST 事件，使用
`feedback_webhook_token` 作为 Bearer token，并进行有界重试；网络慢或服务端离线不会阻塞 ROS
导航执行器。

官方小智固件的异步 `notify` 要求云端提供 Ogg Opus `audio_url`，官方开源服务端目前没有可直接
复用的通用任务通知 HTTP 入口。因此 webhook 是有意保留的服务端边界：适配器负责 TTS/音频托管
并通过所用小智部署向设备下发 `notify`。在未配置适配器时，任务仍可通过 MCP 查询、REST 和 Web
事件流完整观察，但不能宣称已经完成主动语音播报联调。

## ROS 接口

- Nav2 action：`navigate_to_pose`
- 状态：`/wheelbot/mission/status`，`std_msgs/String` JSON
- 机械臂请求：`/wheelbot/arm/task_requests`，`std_msgs/String` JSON
- 机械臂结果：`/wheelbot/arm/task_results`，状态为 `ACCEPTED`、`RUNNING`、`SUCCEEDED`、
  `FAILED` 或 `CANCELLED`
- 机械臂取消：`/wheelbot/arm/cancel`

机械臂内部采用固定轨迹、视觉伺服、ACT 或 VLA 均不改变上述边界。

## 启动与软件验收

先把 `config/semantic_locations.yaml` 中真实测量过的点改为 `commissioned: true`。开发机可用
fake 导航验证任务链，不代表真机导航：

```bash
ros2 launch wheelbot_mission mission.launch.py \
  navigation_mode:=fake allow_uncommissioned_locations:=true \
  use_fake_arm:=true require_robot_state:=false \
  api_token:=change-me-before-deploy
```

`use_fake_arm` 只用于验证“导航-装载-返航”软件状态链，绝不能作为机械臂验收结果。

真机模式使用 `navigation_mode:=nav2`。在启动前必须已有可用地图/定位、唯一 TF 链、已测量
footprint、真实轮参数、Nav2 action server 和 C Board 失联停车保护。

真机默认要求 `/wheelbot/state` 新鲜、`cboard_link == up` 且 fault mask 为 0。导航阶段默认 300 秒
超时，机械臂等待/执行阶段默认 180 秒超时；超时、C 板掉线或控制器故障会取消下游动作并把任务
置为 `FAILED`，不会继续错误流程。参数可以按现场距离调整，但不应关闭安全门槛来掩盖故障。
