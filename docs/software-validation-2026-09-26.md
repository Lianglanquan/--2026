# 软件阶段验证报告（2026-09-26）

## 当前已有能力

- 小智官方固件能在专用板型上向树莓派提交语义导航、取物、返航、查询和取消任务。
- Mission Manager 统一管理任务 ID、幂等、状态、异常、取消、持久化、Nav2 和机械臂边界。
- REST API 和 ROS 状态话题可作为后续 Web 平台与语音反馈的同一数据源。
- C Board 对启用中的非 idle 命令执行 200 ms command-age watchdog。

## 本次发现的问题

- 原仓库没有实际 ESP32 源码，历史文档与代码不一致。
- DJI 子模块固定提交无法从上游取得，递归 clone 不能完全复现。
- 本轮 Windows 环境没有 ROS 2 Jazzy、ESP-IDF 6.1、实际串口和 `wheelbot-pi` SSH 别名，
  因而不能在本机完成 ROS graph、固件全量编译或真机验证。
- Nav2 需要真实地图、footprint、轮参数、雷达外参与语义点；仓库现值仍不能作为真机参数。

## 本次完成内容

- 导入并记录小智官方上游提交，增加 `wheelbot-s3-audio`、N16R8 配置和任务 MCP 工具。
- 新增 `wheelbot_mission` 包、REST API、状态机、Nav2 action 适配和测试用 fake arm。
- 将 Mission Manager 纳入总启动，并补齐 Pi 的 Navigation2 运行依赖。
- 新增 C Board 指令超时停车和 fault bit 7。
- 更新架构、能力缺口、构建和联调文档。

## 当前实际测试结果

- Mission model/HTTP API：7 个测试全部通过。
- ROS 2 纯 Python 回归：36 个可在 Windows 运行的测试全部通过。
- C 主机测试：command watchdog、battery protocol、USB command stream 共 3 个程序通过。
- 小智板型结构：Kconfig/CMake 一致性、默认 flash 配置、相对 include 共 4 个上游测试通过。
- Python compileall、package XML 和板型 JSON 解析通过。
- 小智上游完整 83 项主机测试中，本次引入的两项失败已修复；另 5 项在 Windows 临时目录
  清理阶段因文件锁报错，属于上游测试的 Windows 环境限制，不是功能断言失败。

## 还没有完成的事情

- ESP-IDF 6.1 全量编译、烧录和真实音频/MCP 联调。
- Raspberry Pi 上 `colcon build`、ROS graph、Nav2 action 与真实地图导航。
- 轮参数、外参、footprint、语义位置和 USB 拔线停车的真机验收。
- 主动语音进度播报与实际小智服务端的联调。
- 机械臂、视觉、LeRobot/VLA；本阶段只完成服务边界。

## 下一步

在 Raspberry Pi/机器人旁按顺序完成：修复子模块 pin，`colcon build`，架空轮子验证 USB
失联停车，标定轮/雷达/footprint，保存地图并启动 Nav2，标定 `home` 与 `arm_zone`，最后
烧录小智固件并从语音创建第一条真实 `NAVIGATE` 任务。只有这些实测通过后，才进入机械臂联调。
