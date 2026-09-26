# Wheelbot MuJoCo Baseline

This directory contains the first nominal model for the HA8 + QD4310 wheel-leg
robot. It is a simulation baseline, not an assertion that the digital model has
already been validated on the assembled hardware.

## Control contract

The policy runs at 50 Hz and emits six normalized actions in `[-1, 1]`:

```text
[ left_thigh, left_calf, right_thigh, right_calf, left_wheel, right_wheel ]
```

The first four actions are HA8 position offsets of `0.35 rad` around the
nominal joint target. The last two actions are QD4310 wheel speed commands,
bounded by the currently read configuration of `+/-50 rpm`. The current limit
is recorded as `1.65 A` for the actuator model and safety adapter.

Only strategy-relevant signals belong in the simulation boundary: joint
position/velocity, base orientation/angular velocity/acceleration, actuator
limits, timing, and faults. Wi-Fi, voice, lidar, ROS messages, and board-level
framing remain outside MuJoCo and connect through a hardware adapter later.

## Commands

From the repository root:

```bash
python3 simulation/mujoco/run_nominal_check.py
python3 simulation/mujoco/basic_hold_check.py
python3 simulation/mujoco/topology_audit.py
python3 simulation/mujoco/standing_pose_check.py
pytest -q tests/simulation/test_wheelbot_simulation.py
```

The topology gate and its current evidence are documented in
`TOPOLOGY_BASELINE.md`. The default zero-joint pose is only a ground-contact
baseline; it is not the final standing pose.

The mesh geometry comes from the original URDF package. The XML uses simplified
collision geoms and visual meshes, while its topology and joint axes follow the
complete source URDF. The nominal model uses a `66 mm` wheel envelope and
explicitly labels actuator, mass, center-of-mass, and assembly values as
calibration inputs for the later sim-to-real stage.

The nominal_stand keyframe is the source-URDF zero-joint pose. Its current
checks require both wheel envelopes to touch the ground, equal left/right wheel
height, all four HA8 joints to remain within limits, no unexpected self-contact,
and the center-of-mass projection to remain between the two wheel lines. The
source URDF mass distribution has a longitudinal offset of about 10.95 mm from
the wheel axle line; this is recorded as a dynamics baseline and is not used as
a topology failure. This remains a geometric and initial-contact check, not a
claim of passive dynamic balance.

The wheel command adapter accounts for the mirrored left/right wheel axes: a positive policy wheel speed means the same robot-forward rolling direction on both sides.
