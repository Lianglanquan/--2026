import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SIMULATION = ROOT / "simulation" / "mujoco"
sys.path.insert(0, str(SIMULATION))

from topology_audit import audit_topology  # noqa: E402


def test_mjcf_reproduces_complete_urdf_kinematic_chain():
    report = audit_topology(ROOT)

    assert report["urdf_mjcf"]["topology_match"] is True
    assert report["urdf_mjcf"]["all_joint_axes_match"] is True
    assert report["urdf_mjcf"]["max_joint_center_error_m"] < 1e-5


def test_adapter_placement_gate_accepts_executor_swap_baseline():
    report = audit_topology(ROOT)

    assert report["adapter_placement"]["preserves_urdf_frames"] is True
    assert report["adapter_placement"]["basis"] == "design_confirmation"
    assert report["adapter_placement"]["all_joint_frames_resolved"] is True
    assert report["adapter_placement"]["all_wheel_frames_resolved"] is True
    assert report["training_gate"] == "allowed"
