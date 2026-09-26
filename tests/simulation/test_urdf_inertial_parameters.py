import sys
from pathlib import Path

import mujoco
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
SIMULATION = ROOT / "simulation" / "mujoco"
sys.path.insert(0, str(SIMULATION))


def _body_inertia_tensor(model, body_id):
    rotation = np.empty(9)
    mujoco.mju_quat2Mat(rotation, model.body_iquat[body_id])
    rotation = rotation.reshape(3, 3)
    return rotation @ np.diag(model.body_inertia[body_id]) @ rotation.T


def test_mjcf_uses_source_urdf_link_masses_and_inertia():
    model = mujoco.MjModel.from_xml_path(str(SIMULATION / "wheelbot_nominal.xml"))

    expected = {
        "base_link": (0.2660000, [[0.0006309, 0.0000006, -0.0000468], [0.0000006, 0.0003008, 0.0000003], [-0.0000468, 0.0000003, 0.0007489]]),
        # The rounded URDF LT tensor needs a +5e-9 kg*m^2 izz correction to
        # satisfy MuJoCo's rigid-body inertia triangle inequality.
        "left_thigh": (0.0080000, [[0.0000041, 0, 0.0000002], [0, 0.0000046, 0.0000001], [0.0000002, 0.0000001, 0.000000505]]),
        "left_calf": (0.0166292, [[1.92606315320937e-05, -8.82655659688194e-09, -3.55356649539172e-07], [-8.82655659688194e-09, 1.99807316204063e-05, 4.41228359669666e-07], [-3.55356649539172e-07, 4.41228359669666e-07, 1.55379596081475e-06]]),
        "left_wheel": (0.0559681585451639, np.diag([0.0000121, 0.0000209, 0.0000121])),
        "right_thigh": (0.0080000, [[0.0000041, 0, 0.0000002], [0, 0.0000046, 0.0000001], [0.0000002, 0.0000001, 0.000000505]]),
        "right_calf": (0.0166292, [[0.0000240, 0, 0.0000004], [0, 0.0000245, -0.00000006], [0.0000004, -0.00000006, 0.0000016]]),
        "right_wheel": (0.0559681585451639, np.diag([0.0000121, 0.0000209, 0.0000121])),
    }

    for body_name, (mass, inertia) in expected.items():
        body_id = model.body(body_name).id
        assert model.body_mass[body_id] == pytest.approx(mass, rel=1e-6)
        assert np.allclose(
            _body_inertia_tensor(model, body_id), inertia, rtol=1e-6, atol=2e-10
        )
