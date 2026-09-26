"""Run the shared hold controller against the nominal MuJoCo model."""

from pathlib import Path

import mujoco
import numpy as np

from wheelbot_contract import action_to_command, command_to_mujoco_ctrl


ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "simulation" / "mujoco" / "wheelbot_nominal.xml"


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("nominal_stand").id)
    mujoco.mj_forward(model, data)

    command = action_to_command(np.zeros(6, dtype=np.float32))
    for _ in range(500):
        data.ctrl[:] = command_to_mujoco_ctrl(command)
        mujoco.mj_step(model, data)

    print(f"base_pos={np.array2string(data.qpos[:3], precision=5)}")
    print(f"joint_ctrl={np.array2string(data.ctrl[:4], precision=5)}")
    print(f"wheel_ctrl_rad_s={np.array2string(data.ctrl[4:], precision=5)}")
    print(f"contacts={data.ncon}")


if __name__ == "__main__":
    main()
