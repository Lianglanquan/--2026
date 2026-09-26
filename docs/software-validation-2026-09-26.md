# 软件阶段验证报告（2026-09-26）

## 当前已有能力

- 小智官方固件能在专用板型上向树莓派提交语义导航、取物、返航、查询和取消任务。
- Mission Manager 统一管理任务 ID、幂等、状态、异常、取消、持久化、Nav2 和机械臂边界。
- REST API、Web Mission Console、事件流和 ROS 状态话题共享同一任务真值。
- 任务状态可异步推送到小智服务端适配器，包含统一中文 `speak_text`，不阻塞 ROS 执行器。
- C Board 对启用中的非 idle 命令执行 200 ms command-age watchdog。
- 真机任务默认要求 C Board 状态新鲜、链路在线且无 fault，并对导航和机械臂阶段设置超时。

## 本次发现的问题

- 原仓库没有实际 ESP32 源码，历史文档与代码不一致。
- DJI 子模块固定提交无法从上游取得，递归 clone 不能完全复现。
- 本轮 Windows 环境没有 ROS 2 Jazzy、ESP-IDF 6.1、实际串口和 `wheelbot-pi` SSH 别名，
  因而不能在本机完成 ROS graph、固件全量编译或真机验证。
- Nav2 需要真实地图、footprint、轮参数、雷达外参与语义点；仓库现值仍不能作为真机参数。
- 官方小智固件支持云端 `notify` 播放，但开源服务端没有可直接复用的通用任务通知 HTTP 入口；
  主动语音必须结合实际部署完成 webhook 到 TTS/音频托管/设备转发适配。

## 本次完成内容

- 导入并记录小智官方上游提交，增加 `wheelbot-s3-audio`、N16R8 配置和任务 MCP 工具。
- 新增 `wheelbot_mission` 包、REST/事件 API、Web 控制台、状态机、Nav2 action 适配和测试用
  fake arm。
- 增加反馈 webhook、阶段播报文本、导航/机械臂超时、C Board 链路/fault 安全门槛。
- 修复幂等冲突和返航重试竞态：相同 key 的不同载荷会拒绝，旧返航重放不会取消新任务，
  替换返航先停止旧下游动作再发布新任务。
- 补齐总启动的未标定语义点透传参数，增加公开 REST API 的完整取物状态序列 smoke test 和
  GitHub Actions ROS 2 Jazzy 构建/测试流水线。
- 将 Mission Manager 纳入总启动，并补齐 Pi 的 Navigation2 运行依赖。
- 新增 C Board 指令超时停车和 fault bit 7。
- 更新架构、能力缺口、构建和联调文档。

## 当前实际测试结果

- Mission model/API/事件/反馈/安全：20 个测试全部通过。
- ROS 2/任务 API 纯 Python 回归：43 个可在 Windows 运行的测试全部通过（包含上述 20 项与
  完整八阶段 REST smoke client 测试）。
- C 主机测试：command watchdog、battery protocol、USB command stream、C Board UART receiver
  共 4 个程序通过。
- 小智板型结构：Kconfig/CMake 一致性、默认 flash 配置、相对 include 共 4 个上游测试通过。
- Python compileall、Web 控制台 JavaScript 解析、package XML 和板型 JSON 解析通过。
- GitHub Actions 工作流 YAML 本地解析通过；首次 ROS 2 Jazzy runner 构建仍待推送权限恢复后执行。
- 小智上游完整 83 项主机测试中，本次引入的两项失败已修复；另 5 项在 Windows 临时目录
  清理阶段因文件锁报错，属于上游测试的 Windows 环境限制，不是功能断言失败。

## 还没有完成的事情

- ESP-IDF 6.1 全量编译、烧录和真实音频/MCP 联调。
- Raspberry Pi 上 `colcon build`、ROS graph、Nav2 action 与真实地图导航。
- 轮参数、外参、footprint、语义位置和 USB 拔线停车的真机验收。
- 主动语音 webhook 到实际小智服务端、TTS 音频和设备 `notify` 的联调。
- 机械臂、视觉、LeRobot/VLA；本阶段只完成服务边界。

## 下一步

在 Raspberry Pi/机器人旁按顺序完成：修复子模块 pin，`colcon build`，架空轮子验证 USB
失联停车，标定轮/雷达/footprint，保存地图并启动 Nav2，标定 `home` 与 `arm_zone`，最后
烧录小智固件并从语音创建第一条真实 `NAVIGATE` 任务。只有这些实测通过后，才进入机械臂联调。
