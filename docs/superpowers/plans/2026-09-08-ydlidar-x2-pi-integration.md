# YDLIDAR X2 Pi Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate the official YDLIDAR ROS 2 driver with the existing FishBot TCP-to-PTY transport on Raspberry Pi without starting runtime validation.

**Architecture:** FishBot Laser Board remains a transparent UART-to-TCP bridge. A persistent local PTY exposes the TCP byte stream as `/dev/wheelbot-lidar`; the official YDLIDAR ROS 2 driver consumes that device and publishes `/scan` when later enabled.

**Tech Stack:** ROS 2 Jazzy, CMake, Python 3, systemd, YDLIDAR official ROS 2 SDK.

**Spec:** User-approved chat design on 2026-09-08.

## Global Constraints

- Do not modify X2 protocol parsing.
- Do not start the YDLIDAR node or perform `/scan` runtime verification in this task.
- Preserve the existing TCP port `8889` and X2 baudrate `115200`.
- Keep service units installed but disabled until explicit runtime validation.

### Task 1: Add official-driver source and workspace manifest

**Files:**
- Modify: `ros2/wheelbot_ws/src/ydlidar_ros2` on Raspberry Pi only
- Test: `ros2/wheelbot_ws/src/ydlidar_ros2` package discovery

- [ ] Obtain the official YDLIDAR ROS 2 repository without replacing existing packages.
- [ ] Add it under the Pi workspace `src` directory.
- [ ] Keep the source at the upstream revision recorded by Git.

### Task 2: Make the PTY device persistent

**Files:**
- Create: `deploy/raspberry_pi/wheelbot-lidar-tcp.service`
- Modify: `ros2/wheelbot_ws/src/wheelbot_lidar/wheelbot_lidar/tcp_to_pty.py`

- [ ] Add a `--device-link` option that atomically points `/dev/wheelbot-lidar` to the current PTY.
- [ ] Add a service unit for the TCP-to-PTY bridge, disabled by default.
- [ ] Install the service and create the device link only when the bridge is explicitly started later.

### Task 3: Add X2 launch/configuration

**Files:**
- Create: `ros2/wheelbot_ws/src/wheelbot_lidar/launch/x2.launch.py`
- Modify: `ros2/wheelbot_ws/src/wheelbot_lidar/config/x2.yaml`
- Create: `deploy/raspberry_pi/ydlidar-x2.service`

- [ ] Configure official X2 parameters at `/dev/wheelbot-lidar`, 115200 baud, single channel.
- [ ] Add a launch file that can be run later but is not started by installation.
- [ ] Install the driver service disabled and without enabling dependencies automatically.

### Task 4: Build-only configuration check

- [ ] Build the Pi workspace with the official package and local packages.
- [ ] Check that launch/config files are installed.
- [ ] Confirm both services are disabled and stopped.
- [ ] Do not launch either service and do not inspect `/scan`.
