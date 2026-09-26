"""Minimal Gymnasium-style environment for the nominal wheelbot model."""

from __future__ import annotations

from pathlib import Path

import mujoco
import numpy as np

from wheelbot_contract import (
    ACTION_SIZE,
    NOMINAL_STAND_JOINT_TARGET_RAD,
    action_to_command,
    command_to_mujoco_ctrl,
)

try:
    from gymnasium import spaces
except ModuleNotFoundError:  # Keep model checks runnable before RL dependencies are installed.
    class _Box:
        def __init__(self, low, high, shape, dtype=np.float32):
            self.low = np.full(shape, low, dtype=dtype)
            self.high = np.full(shape, high, dtype=dtype)
            self.shape = shape
            self.dtype = dtype

        def contains(self, value):
            array = np.asarray(value, dtype=self.dtype)
            return array.shape == self.shape and np.all(array >= self.low) and np.all(array <= self.high)

    class spaces:  # noqa: N801
        Box = _Box


ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(__file__).with_name("wheelbot_nominal.xml")
CONTROL_DECIMATION = 10  # 50 Hz policy updates over the 500 Hz MuJoCo step.
MAX_EPISODE_STEPS = 1000


class WheelbotEnv:
    """Small, deterministic environment boundary before PPO integration."""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 50}

    def __init__(self, render_mode: str | None = None, model_path: Path = MODEL_PATH):
        if render_mode not in (None, "human", "rgb_array"):
            raise ValueError("render_mode must be None, 'human', or 'rgb_array'")
        self.render_mode = render_mode
        self.model = mujoco.MjModel.from_xml_path(str(model_path))
        self.data = mujoco.MjData(self.model)
        self.action_space = spaces.Box(-1.0, 1.0, (ACTION_SIZE,), dtype=np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, (19,), dtype=np.float32)
        self.last_ctrl = np.zeros(self.model.nu, dtype=np.float32)
        self._step_count = 0
        self._renderer = None
        self._viewer = None

    def reset(self, *, seed: int | None = None, options=None):
        del options
        if seed is not None:
            np.random.seed(seed)
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.model.key("nominal_stand").id)
        mujoco.mj_forward(self.model, self.data)
        self.last_ctrl.fill(0.0)
        self._step_count = 0
        return self._get_obs(), {"keyframe": "nominal_stand"}

    def step(self, action):
        command = action_to_command(action, NOMINAL_STAND_JOINT_TARGET_RAD)
        self.last_ctrl = command_to_mujoco_ctrl(command)
        for _ in range(CONTROL_DECIMATION):
            self.data.ctrl[:] = self.last_ctrl
            mujoco.mj_step(self.model, self.data)
        self._step_count += 1
        observation = self._get_obs()
        reward = self._reward()
        terminated = self._is_fallen()
        truncated = self._step_count >= MAX_EPISODE_STEPS
        info = {
            "sim_time_s": float(self.data.time),
            "contact_count": int(self.data.ncon),
            "keyframe": "nominal_stand",
        }
        return observation, reward, bool(terminated), bool(truncated), info

    def render(self):
        if self.render_mode == "rgb_array":
            if self._renderer is None:
                self._renderer = mujoco.Renderer(self.model, height=480, width=640)
            self._renderer.update_scene(self.data, camera="inspection_view")
            return self._renderer.render()
        if self.render_mode == "human":
            if self._viewer is None:
                import mujoco.viewer
                self._viewer = mujoco.viewer.launch_passive(self.model, self.data)
            self._viewer.sync()
        return None

    def close(self):
        if self._viewer is not None:
            self._viewer.close()
            self._viewer = None
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None

    def _get_obs(self):
        base_quat = self.data.qpos[3:7]
        base_angvel = self.data.qvel[3:6]
        joint_positions = self.data.qpos[7:13]
        joint_velocities = self.data.qvel[6:12]
        return np.concatenate((base_quat, base_angvel, joint_positions, joint_velocities)).astype(np.float32)

    def _reward(self):
        pitch_error = float(self.data.qpos[4])
        roll_error = float(self.data.qpos[5])
        joint_error = float(np.linalg.norm(self.data.qpos[7:11] - NOMINAL_STAND_JOINT_TARGET_RAD))
        return 1.0 - 2.0 * (pitch_error * pitch_error + roll_error * roll_error) - 0.05 * joint_error

    def _is_fallen(self):
        return bool(self.data.qpos[2] < 0.015 or abs(float(self.data.qpos[4])) > 0.8 or abs(float(self.data.qpos[5])) > 0.8)
