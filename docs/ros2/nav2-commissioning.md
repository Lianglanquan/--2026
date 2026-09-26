# Nav2 接入与真机门槛

`wheelbot_navigation` 复用官方 `nav2_bringup/navigation_launch.py`，不复制 Nav2，也不使用
TurtleBot 默认几何。启动时必须显式提供本机实测的参数文件：

```bash
ros2 launch wheelbot_bringup phase1.launch.py \
  use_real_bridge:=true use_fake_bridge:=false use_lidar:=true \
  use_ekf:=true use_slam:=true use_nav2:=true \
  nav2_params_file:=/home/fool/wheelbot_config/nav2_params.yaml
```

参数文件至少要包含与本机一致的 planner、controller、BT navigator、行为、costmap 和
lifecycle 配置。启用前必须确认：

1. 轮半径、轮距和方向已实测，`/cmd_vel` 到 RPM 已架空轮验收。
2. `base_link` 的真实 footprint/robot radius 已测量，包含载物区外廓。
3. 雷达外参已测量，`map -> odom -> base_link -> laser_frame` 唯一。
4. 已有可重复加载的地图或稳定 SLAM，障碍膨胀半径包含停车误差。
5. C Board USB 失联 200 ms 自动停车已在台架实测。
6. `navigate_to_pose` 能在低速、有人看护、空载条件下成功和取消。

完成后再测量 `semantic_locations.yaml` 的 `home`、`workbench`、`arm_zone`，逐项把
`commissioned` 改为 `true`。未通过上述门槛时保持 `use_nav2:=false`。
