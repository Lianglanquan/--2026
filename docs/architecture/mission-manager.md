# Mission Manager 与小智任务接口

## 数据流

```text
语音 -> 小智 ASR/LLM -> ESP32 设备侧 MCP 工具
     -> HTTPS/HTTP JSON -> Raspberry Pi Mission Manager
     -> Nav2 NavigateToPose -> /cmd_vel -> C Board 安全控制
     -> 机械臂高层任务边界（不含机械臂实现）
     -> /wheelbot/mission/status + REST 查询 -> 小智/Web
```

ESP32 只负责自然语言入口和结构化任务提交。任务调度、状态仲裁、导航与失败处理位于树莓派。

## 任务类型

- `NAVIGATE`：前往一个已标定语义位置。
- `FETCH_ITEM`：前往工作区，等待机械臂明确报告装载成功，再返回。
- `RETURN_HOME`：取消当前任务并创建返航任务。

同一时刻只允许一个活动任务。`request_id` 重试返回原任务，不重复执行。

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
- `POST /api/v1/missions/{mission_id}/cancel`

所有 Web 客户端都应读取这个 API 或 `/wheelbot/mission/status`，不要维护第二套任务状态。

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
  use_fake_arm:=true api_token:=change-me-before-deploy
```

`use_fake_arm` 只用于验证“导航-装载-返航”软件状态链，绝不能作为机械臂验收结果。

真机模式使用 `navigation_mode:=nav2`。在启动前必须已有可用地图/定位、唯一 TF 链、已测量
footprint、真实轮参数、Nav2 action server 和 C Board 失联停车保护。
