# Wheelbot software bring-up (2026-09-26)

## Current executable path

- The Raspberry Pi bridge accepts `/wheelbot/command` (`RobotCommand`), maps
  `idle=0`, `joint=1`, `wheel=2`, `combined=3`, and sends a CRC-checked WB v1
  binary command over USB CDC. Array order is LF, LR, RF, RR for HA8 and
  QD4310 ID 1, ID 2 for wheels. Joint values on the wire are **servo degrees**;
  wheel values are **motor RPM**.
- The C Board parses USB CDC as a stream (fragments/coalesced frames), rejects
  invalid modes and non-finite targets, and acts only on an explicit new
  command. `enable=false` or `mode=idle` explicitly stops and disables wheels.
  If a CAN transmit mailbox is full, commands are retried before a generation
  is considered applied. Explicit idle also cancels queued HA8 targets.
  There is no emergency-stop command or command-age timeout in this path.
- The C Board queries all four HA8 units through the single USART6-owning task
  and both QD4310 units on CAN1; it publishes IMU, battery voltage, joint and
  wheel feedback in the WB v1 state frame. The Pi publishes `/wheelbot/state`,
  `/imu/data`, `/joint_states`, `/battery_state`, and `/wheelbot/wheel_odom`.
  JointState uses radians. Battery percentage is unknown (NaN), not inferred
  from an uncharacterized discharge curve.
  State `faults` bit 0-3 marks unreadable HA8 units, 4-5 marks missing/failed
  QD4310 feedback (including feedback older than 500 ms), and 6 marks
  unavailable IMU pointers; these are diagnostic
  indicators, not automatic control actions.
  Wheel odometry does not integrate stale velocity while a configured motor
  feedback fault is present.
- The Wheelbot build does not create the DJI sample calibration, chassis,
  gimbal, PWM-servo, USB-text, or test tasks. In particular, the legacy
  calibration task must not send CAN reset-ID commands to commissioned motors.
- `/cmd_vel` to wheel RPM conversion is available but disabled by default. Set
  measured wheel radius/track and tested motor signs in the installed
  `wheel_geometry.yaml`, then launch `bridge.launch.py use_cmd_vel:=true`.
  Navigation velocity commands are not emitted without these measurements.

## Physical commissioning gates

1. Verify USB CDC command and state framing with the C Board on a bench. The
   source has been built, but no firmware was flashed as part of this change.
2. Confirm each HA8's mechanical zero, forward rotation sign, and travel range
   after assembly. ID assignment alone is not a mechanical calibration.
   `WHEELBOT_HA8_MOTION_ENABLED` remains OFF in the CMake build until verified.
3. Verify both wheel directions and measured wheel radius/track, then configure
   ROS geometry and odometry signs. Odometry keeps the existing single-wheel
   default until both signs are measured; its yaw estimate is otherwise invalid.
4. Integrate a leg kinematics/controller mode with limit-aware servo transforms,
   then a standing controller and policy interface. The policy must output
   intent through the same WB command path; no direct actuator writes from ROS.

Unlike microduck's hardware layout, this robot uses Pi for navigation and C
Board for the actuator owner. The useful architectural analogy is keeping the
high-level intent separate from low-level joint control, not reusing its pins
or motion parameters.

Without an automatic command-age stop, a lost USB link does not itself clear
the last wheel speed on the C Board. Do not operate the mobile robot untethered
or flash a motion-enabled image before bench-level link-loss behavior and
mechanical parameters have been reviewed.
