# Topology Baseline

This is the gate for the first simulation stage. It answers one question before
training: does the nominal MJCF preserve the robot's motion topology?

## Verified now

- The MJCF body tree matches the complete source URDF:
  `base_link -> thigh -> calf -> wheel` on both left and right branches.
- All six joint parent relationships match the URDF.
- All six joint axes match in world coordinates.
- Joint-center error between the URDF and MJCF is below `1e-5 m`.
- The default zero-joint pose places both simplified wheel collision envelopes
  tangent to the ground plane.

## Adapter placement decision

The project design decision is that the HA8/QD4310 adapters only replace the
actuators. They do not change the four HA8 joint centers, joint axes, or the two
wheel axle frames from the source URDF. This decision is recorded in
`adapter_placement_baseline.json`, so the topology audit can accept the URDF
frames even though the current STEP report does not contain absolute assembly
coordinates.

This allows the project to begin basic standing and low-speed simulation. It is
not the final hardware-calibrated dynamics model: physical validation is still
required before deploying a learned policy to the robot.

## Next gate

When the robot is assembled, measure the six frames and compare them with the
URDF baseline. If they differ, update only the placement parameters, rerun
`topology_audit.py`, and recalibrate the dynamics before hardware deployment.

The current nominal standing keyframe is the source-URDF zero-joint pose. It is
accepted as the first pose because both wheels contact the ground, the left and
right wheel heights match, the center-of-mass projection is between the two
wheel lines, and the four HA8 targets are within their limits. With the source
URDF inertial data, the longitudinal center-of-mass offset from the wheel axle
line is approximately 10.95 mm; this is a physical baseline value, not a
topology error. A two-wheel robot still needs an active balance controller;
this check does not claim passive stability.
