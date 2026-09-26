"""Load the nominal model and run a short zero-action safety check."""

from pathlib import Path

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "simulation" / "mujoco" / "wheelbot_nominal.xml"


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("nominal_stand").id)
    mujoco.mj_forward(model, data)

    for _ in range(500):
        data.ctrl[:] = 0.0
        mujoco.mj_step(model, data)

    print(f"model={MODEL_PATH}")
    print(f"nq={model.nq} nv={model.nv} nu={model.nu}")
    print(f"base_pos={np.array2string(data.qpos[:3], precision=5)}")
    print(f"max_abs_ctrl={float(np.max(np.abs(data.ctrl))):.3f}")
    print(f"contacts={data.ncon}")


if __name__ == "__main__":
    main()
