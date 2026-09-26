"""Interactive nominal MuJoCo viewer with the same keyframe as the checks."""

from pathlib import Path
import time
import argparse

import mujoco
import mujoco.viewer


MODEL_PATH = Path(__file__).with_name("wheelbot_nominal.xml")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true", help="advance MuJoCo dynamics")
    args = parser.parse_args()
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    key_id = model.key("nominal_stand").id
    mujoco.mj_resetDataKeyframe(model, data, key_id)
    mujoco.mj_forward(model, data)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
        viewer.cam.fixedcamid = model.camera("inspection_view").id
        viewer.sync()
        while viewer.is_running():
            step_start = time.perf_counter()
            if args.simulate:
                data.ctrl[:] = 0.0
                mujoco.mj_step(model, data)
            viewer.sync()
            remaining = model.opt.timestep - (time.perf_counter() - step_start)
            if remaining > 0:
                time.sleep(remaining)


if __name__ == "__main__":
    main()
