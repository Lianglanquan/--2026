import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SIMULATION = ROOT / "simulation" / "mujoco"
sys.path.insert(0, str(SIMULATION))

from wheelbot_env import WheelbotEnv  # noqa: E402


def test_env_reset_returns_fixed_shape_observation_and_info():
    env = WheelbotEnv()
    observation, info = env.reset(seed=7)

    assert observation.shape == env.observation_space.shape
    assert np.all(np.isfinite(observation))
    assert info["keyframe"] == "nominal_stand"

    env.close()


def test_env_step_returns_gymnasium_style_transition():
    env = WheelbotEnv()
    env.reset(seed=7)

    observation, reward, terminated, truncated, info = env.step(
        np.zeros(6, dtype=np.float32)
    )

    assert observation.shape == env.observation_space.shape
    assert np.isfinite(reward)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert info["sim_time_s"] > 0.0

    env.close()


def test_env_forward_command_uses_shared_wheel_axis_contract():
    env = WheelbotEnv()
    env.reset(seed=7)
    env.step(np.array([0, 0, 0, 0, 1, 1], dtype=np.float32))

    assert env.last_ctrl[4] > 0.0
    assert env.last_ctrl[5] < 0.0

    env.close()
