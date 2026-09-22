# WheelBot Phase 1 SLAM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a hardware-ready ROS 2 Jazzy phase-one pipeline for IMU/wheel state adaptation, EKF odometry, sensor TF, and `slam_toolbox` mapping, with fake-data validation available before the physical robot is assembled.

**Architecture:** Keep the existing serial bridge responsible for the C Board protocol and raw `wheelbot/state`; add a small state adapter that converts the standard state message into `sensor_msgs/Imu` and `nav_msgs/Odometry`. Fuse those inputs with `robot_localization`, publish the single authoritative `odom -> base_link` transform, and feed `/scan` plus TF into `slam_toolbox`. Package configuration and launch files separately so real and fake inputs can be switched without changing algorithm code.

**Tech Stack:** ROS 2 Jazzy, Python 3, `rclpy`, `sensor_msgs`, `nav_msgs`, `robot_localization`, `slam_toolbox`, `robot_state_publisher`, `pytest`, `colcon`.

**Spec:** `docs/superpowers/specs/2026-09-21-wheelbot-phase1-slam-design.md`

## Global Constraints

- Do not reset, revert, or overwrite unrelated existing worktree changes.
- Do not fabricate the second wheel's feedback; default the adapter to configured wheel index `[0]` until firmware exposes both wheels reliably.
- Keep all physical dimensions and sensor extrinsics in YAML/URDF configuration, not Python constants.
- Do not claim physical SLAM validation without real `/scan`, TF, and robot motion data.
- Maintain the existing protocol and TCP-to-PTY tests.

---

### Task 1: State conversion and differential-drive odometry core

**Files:**
- Create: `ros2/wheelbot_ws/src/wheelbot_bridge/wheelbot_bridge/state_adapter.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_bridge/test/test_state_adapter.py`

**Interfaces:**
- `quaternion_wxyz_to_xyzw(quaternion: Sequence[float]) -> tuple[float, float, float, float]`
- `WheelOdometer(radius_m: float, track_m: float, wheel_indices: Sequence[int], wheel_signs: Sequence[float])`
- `WheelOdometer.update(wheel_velocity_rpm: Sequence[float], stamp_s: float) -> WheelOdomSample`
- `WheelOdomSample` exposes `x_m`, `y_m`, `yaw_rad`, `linear_x_mps`, `angular_z_rps`, `has_valid_motion`, and `yaw_covariance`.

- [x] **Step 1: Write failing tests** for quaternion ordering, first odometry sample, two-wheel straight motion, two-wheel in-place rotation, single-wheel forward motion with high yaw covariance, and invalid wheel configuration.
- [x] **Step 2: Run the focused test** with `pytest -q ros2/wheelbot_ws/src/wheelbot_bridge/test/test_state_adapter.py`; confirm it fails because the module is absent.
- [x] **Step 3: Implement the smallest pure-Python conversion and odometry module** using wheel RPM to rad/s, configurable wheel signs, and explicit single-wheel behavior.
- [x] **Step 4: Run the focused test** and confirm all cases pass.
- [x] **Step 5: Run existing bridge tests** to ensure no protocol behavior regressed.

### Task 2: ROS state adapter node

**Files:**
- Modify: `ros2/wheelbot_ws/src/wheelbot_bridge/package.xml`
- Modify: `ros2/wheelbot_ws/src/wheelbot_bridge/setup.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_bridge/wheelbot_bridge/state_adapter_node.py`
- Modify: `ros2/wheelbot_ws/src/wheelbot_bridge/wheelbot_bridge/fake_bridge_node.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_bridge/test/test_state_adapter_node.py`

**Interfaces:**
- Input: `/wheelbot/state` (`wheelbot_interfaces/msg/RobotState`).
- Outputs: `/imu/data` (`sensor_msgs/msg/Imu`), `/wheelbot/wheel_odom` (`nav_msgs/msg/Odometry`).
- Parameters: `imu_frame`, `odom_frame`, `base_frame`, `wheel_radius_m`, `wheel_track_m`, `wheel_indices`, `wheel_signs`.

- [x] **Step 1: Write failing node-level tests** for output frame IDs and conversion of a representative `RobotState` into IMU and wheel odometry messages.
- [x] **Step 2: Run the focused tests** and verify the missing node/conversion behavior fails for the intended reason.
- [x] **Step 3: Implement the node** using the pure conversion core; publish no TF from this node; use ROS receive time for output headers.
- [x] **Step 4: Update fake bridge** to publish realistic `RobotState` samples with configurable forward motion and both-wheel fields, while keeping existing fake topics.
- [x] **Step 5: Add the console entry point and ROS dependencies**, then run focused tests and package import checks.

### Task 3: Localization package and EKF configuration

**Files:**
- Create: `ros2/wheelbot_ws/src/wheelbot_localization/package.xml`
- Create: `ros2/wheelbot_ws/src/wheelbot_localization/setup.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_localization/resource/wheelbot_localization`
- Create: `ros2/wheelbot_ws/src/wheelbot_localization/wheelbot_localization/__init__.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_localization/config/ekf.yaml`
- Create: `ros2/wheelbot_ws/src/wheelbot_localization/launch/ekf.launch.py`

**Interfaces:**
- Consumes `/imu/data` and `/wheelbot/wheel_odom`.
- Produces `/odometry/filtered` and the sole `odom -> base_link` TF.

- [x] **Step 1: Add package/config tests** that parse `ekf.yaml` and assert `world_frame=odom`, `base_link_frame=base_link`, `two_d_mode=true`, and the two expected inputs.
- [x] **Step 2: Run the config tests** and confirm the package/config files are initially missing.
- [x] **Step 3: Add the package and launch file** with `robot_localization` as a runtime dependency.
- [x] **Step 4: Add conservative EKF settings**: use wheel odometry for planar velocity/pose, use IMU angular velocity and yaw-related orientation input, disable duplicate TF publishing from input sources, and set `publish_tf=true` only on EKF.
- [x] **Step 5: Run config tests and Python syntax/import checks.

### Task 4: Sensor description and phase-one launch orchestration

**Files:**
- Modify: `ros2/wheelbot_ws/src/wheelbot_description/urdf/wheelbot.urdf`
- Modify: `ros2/wheelbot_ws/src/wheelbot_description/setup.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_description/launch/sensors.launch.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_bringup/package.xml`
- Create: `ros2/wheelbot_ws/src/wheelbot_bringup/setup.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_bringup/launch/phase1.launch.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_bringup/test/test_phase1_config.py`

**Interfaces:**
- URDF frames: `base_link`, `imu_link`, `laser_frame`.
- Launch arguments: `use_real_bridge`, `use_fake_bridge`, `use_lidar`, `use_ekf`, `use_slam`, `use_description`.

- [x] **Step 1: Write failing tests** for the required frame names and phase-one launch argument names.
- [x] **Step 2: Run focused config tests** and confirm failure because the new frames/launch do not exist.
- [x] **Step 3: Add minimal fixed sensor links** to the URDF with zero default extrinsics; keep the values visibly marked as calibration inputs rather than claiming they are measured.
- [x] **Step 4: Add launch orchestration** that composes fake or real bridge, sensor description, lidar, EKF, and SLAM conditionally without duplicating `odom -> base_link`.
- [x] **Step 5: Run syntax/import/config tests.

### Task 5: Mapping package and documentation

**Files:**
- Create: `ros2/wheelbot_ws/src/wheelbot_mapping/package.xml`
- Create: `ros2/wheelbot_ws/src/wheelbot_mapping/setup.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_mapping/resource/wheelbot_mapping`
- Create: `ros2/wheelbot_ws/src/wheelbot_mapping/wheelbot_mapping/__init__.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_mapping/config/mapper_params_online_sync.yaml`
- Create: `ros2/wheelbot_ws/src/wheelbot_mapping/launch/mapping.launch.py`
- Create: `docs/ros2/phase1-slam-bringup.md`

**Interfaces:**
- Consumes `/scan`, `/odometry/filtered`, and `map -> odom` prerequisites.
- Produces `/map` and `map -> odom` through `slam_toolbox`.

- [x] **Step 1: Write failing config tests** for frames, scan topic, resolution, and synchronous mapping mode.
- [x] **Step 2: Run focused tests** and confirm missing package/config failure.
- [x] **Step 3: Add `slam_toolbox` configuration** with the selected frames and 0.05 m map resolution.
- [x] **Step 4: Add a mapping launch file** with a configurable serialized-map path and optional RViz disabled by default.
- [x] **Step 5: Document build, fake-data checks, real-hardware checks, map save, and known calibration gates.

### Task 6: Full verification

**Files:**
- No new production files unless verification exposes a scoped defect.

- [x] **Step 1: Run all ROS package Python tests** with `pytest -q ros2/wheelbot_ws/src`.
- [x] **Step 2: Run `python3 -m compileall` over all new Python packages.
- [x] **Step 3: Run the selected-package `colcon build --symlink-install` with `wheelbot_lidar` included as a dependency.
- [x] **Step 4: Run launch/config inspection without hardware; record that `/scan` and physical SLAM remain unverified.
- [x] **Step 5: Review `git diff` and `git status` to confirm only scoped files plus the already-existing worktree state changed.
