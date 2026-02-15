"""
CircuitBreakerEnv — Custom Gymnasium Environment
==================================================
Wraps the entire Algorithmic Circuit Breaker simulation loop into
an OpenAI Gymnasium-compatible environment for PPO training.

The PPO agent acts as a **meta-controller** that adjusts PID gains
(Kp, Ki, Kd) and the friction_threshold at every step, while the
underlying PID still performs the real-time control.

Architecture:  PPO (slow, strategic)  →  PID (fast, tactical)
               ↑________________________↓
                    reward feedback
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from circuit_breaker.core.config import PIDConfig, RLConfig
from circuit_breaker.models.user_agent import UserAgent
from circuit_breaker.controllers.pid_controller import CircuitBreaker


# ── TPP Kernel (inlined to avoid circular imports) ────────────
MU0         = 0.3
ALPHA1_BASE = 0.2
GAMMA_TOX   = 0.4
BETA1       = 5.0
ALPHA2      = 0.3
BETA2       = 0.5

# PID gain ranges (absolute bounds for safety)
KP_RANGE = (0.2, 3.0)
KI_RANGE = (0.01, 0.5)
KD_RANGE = (0.01, 1.0)
FRICTION_THRESH_RANGE = (0.1, 0.6)

# Soft friction hard-cap (seconds).  Fix 3 requirement.
MAX_FRICTION_DELAY = 2.5


class _RecursiveTPPKernel:
    """Minimal O(1) bi-exponential Hawkes kernel."""

    def __init__(self, beta1, beta2, mu0):
        self.beta1, self.beta2, self.mu0 = beta1, beta2, mu0
        self.A1 = self.A2 = 0.0
        self.t_last = 0.0

    def _decay(self, t):
        dt = t - self.t_last
        if dt > 0:
            self.A1 *= np.exp(-self.beta1 * dt)
            self.A2 *= np.exp(-self.beta2 * dt)
            self.t_last = t

    def add_event(self, t):
        self._decay(t)
        self.A1 += 1.0
        self.A2 += 1.0

    def intensity(self, t, a1_eff, a2):
        dt = t - self.t_last
        a1 = self.A1 * np.exp(-self.beta1 * dt) if dt > 0 else self.A1
        a2_ = self.A2 * np.exp(-self.beta2 * dt) if dt > 0 else self.A2
        return self.mu0 + a1_eff * self.beta1 * a1 + a2 * self.beta2 * a2_


def _ogata_thinning(t_start, window, kernel, a1_eff, a2, rng, max_events=50):
    """Ogata thinning with safety cap to prevent infinite loops."""
    # Clamp branching ratio: a1_eff + a2 must be < 1.0
    a1_safe = min(a1_eff, 0.9 - a2)
    a1_safe = max(a1_safe, 0.0)

    lam_star = max(kernel.intensity(t_start, a1_safe, a2) * 1.5,
                   kernel.mu0 * 1.2)
    accepted = []
    t = t_start
    t_end = t_start + window
    while t < t_end and len(accepted) < max_events:
        u1 = rng.random()
        dt_c = -np.log(max(u1, 1e-12)) / lam_star
        t += dt_c
        if t >= t_end:
            break
        lam_t = kernel.intensity(t, a1_safe, a2)
        if rng.random() <= lam_t / lam_star:
            kernel.add_event(t)
            accepted.append(t)
            lam_star = max(kernel.intensity(t, a1_safe, a2) * 1.5, lam_star)
    return accepted


class CircuitBreakerEnv(gym.Env):
    """
    Gymnasium Environment for PPO-PID Hierarchical Control.

    Observation (5-D, all normalized to [0, 1]):
        [toxicity, dopamine_level, risk_index, velocity_norm, prev_control_signal]

    Action (4-D, continuous [-1, 1], mapped to deltas):
        [ΔKp, ΔKi, ΔKd, Δfriction_threshold]

    Reward:
        +1.0  if dopamine < 0.5 and velocity stable
        -5.0  if dopamine > 0.8  (addiction not controlled)
        -10.0 if friction_delay > 2.5s  (system too aggressive)
    """

    metadata = {"render_modes": []}

    def __init__(self, max_steps: int = 500, seed: int = 42):
        super().__init__()
        self.max_steps = max_steps

        # Spaces
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(5,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(4,), dtype=np.float32
        )

        # Internal defaults
        self._seed = seed
        self._init_internals()

    def _init_internals(self):
        """Reset all simulation state."""
        self.rng = np.random.default_rng(self._seed)

        # RL agent (Rescorla-Wagner)
        self.rl_config = RLConfig(alpha=0.1, initial_expected_reward=0.2)
        self.user = UserAgent(config=self.rl_config)

        # PID controller (will be tuned by PPO)
        self.pid_config = PIDConfig(
            kp=1.2, ki=0.1, kd=0.2,
            w1=0.6, w2=0.3, w3=0.1,
            circuit_break_threshold=0.45,
        )
        self.controller = CircuitBreaker(config=self.pid_config)

        # TPP kernel
        self.kernel = _RecursiveTPPKernel(BETA1, BETA2, MU0)

        # Simulation state
        self.time_elapsed = 0.0
        self.toxicity = 0.1
        self.step_count = 0
        self.prev_control_signal = 0.0
        self.prev_velocity_norm = 0.5
        self.current_friction_delay = 0.0

        # ── Fix 2: Sliding window (5 steps × 3 features) ──
        self.state_window = np.zeros((5, 3), dtype=np.float32)

        # History for logging
        self.history = []

    def reset(self, seed=None, options=None):
        if seed is not None:
            self._seed = seed
        self._init_internals()
        obs = self._get_obs()
        return obs, {}

    def _get_obs(self) -> np.ndarray:
        """Build 5-D observation for PPO."""
        return np.array([
            self.toxicity,
            self.user.get_addiction_score(),
            0.0,  # risk_index placeholder (will be computed in step)
            self.prev_velocity_norm,
            self.prev_control_signal,
        ], dtype=np.float32)

    def step(self, action: np.ndarray):
        # ── Apply PPO action: adjust PID gains ──────────────
        delta_kp = float(action[0]) * 0.3   # ΔKp ∈ [-0.3, +0.3]
        delta_ki = float(action[1]) * 0.05  # ΔKi ∈ [-0.05, +0.05]
        delta_kd = float(action[2]) * 0.1   # ΔKd ∈ [-0.1, +0.1]
        delta_ft = float(action[3]) * 0.05  # Δfriction_threshold ∈ [-0.05, +0.05]

        self.controller.kp = float(np.clip(
            self.controller.kp + delta_kp, *KP_RANGE))
        self.controller.ki = float(np.clip(
            self.controller.ki + delta_ki, *KI_RANGE))
        self.controller.kd = float(np.clip(
            self.controller.kd + delta_kd, *KD_RANGE))
        self.controller.friction_threshold = float(np.clip(
            self.controller.friction_threshold + delta_ft, *FRICTION_THRESH_RANGE))

        # ── 1. Adversarial Toxicity (Fix 1) ─────────────────
        base_cycle = 0.5 + 0.4 * np.sin(self.time_elapsed / 800.0)
        noise = self.rng.normal(0, 0.15)
        self.toxicity = float(np.clip(base_cycle + noise, 0.0, 1.0))

        # Adversarial spike: if velocity dropped, platform retaliates
        if self.prev_velocity_norm < 0.3:
            spike = self.rng.uniform(0.85, 1.0)
            self.toxicity = float(np.clip(
                self.toxicity * 0.3 + spike * 0.7, 0.0, 1.0))

        # ── 2. PID control signal ───────────────────────────
        addiction_score = self.user.get_addiction_score()
        control_signal, risk_index = self.controller.compute_control_signal(
            addiction_score=addiction_score,
            toxicity_score=self.toxicity,
            session_duration=self.time_elapsed,
            dt=1.0,
        )

        # ── 3. Decay factor for α¹ ─────────────────────────
        decay_factor = self.controller.compute_decay_factor(control_signal)
        alpha1_base = ALPHA1_BASE + GAMMA_TOX * self.toxicity
        alpha1_eff = min(alpha1_base * decay_factor, 0.6)  # safety clamp

        # ── 4. TPP event sampling ───────────────────────────
        window = 10.0
        events = _ogata_thinning(
            self.time_elapsed, window, self.kernel,
            alpha1_eff, ALPHA2, self.rng
        )
        clicks = len(events)

        # ── 5. Soft Friction (Fix 3) ────────────────────────
        # Hard-cap friction at MAX_FRICTION_DELAY (2.5s)
        friction_delay_per_click = 0.0
        if control_signal > self.controller.friction_threshold:
            raw_delay = control_signal * 2.5  # linear, max 2.5s
            friction_delay_per_click = min(raw_delay, MAX_FRICTION_DELAY)

        base_dwell = (self.rng.pareto(a=1.5) + 1) * 5.0
        total_friction = clicks * friction_delay_per_click
        # Record for reward check
        self.current_friction_delay = friction_delay_per_click

        dwell_time = base_dwell + total_friction
        velocity = (clicks * self.rl_config.px_per_interaction) / max(dwell_time, 0.1)
        velocity_norm = min(velocity / self.rl_config.max_velocity_px_s, 1.0)

        # ── 6. Update sliding window (Fix 2) ────────────────
        self.state_window = np.roll(self.state_window, -1, axis=0)
        self.state_window[-1] = [velocity_norm, self.toxicity,
                                  min(dwell_time / 60.0, 1.0)]

        # ── 7. RPE on post-intervention velocity ────────────
        self.user.calculate_rpe(velocity, self.toxicity)
        dopamine = self.user.get_addiction_score()

        # ── 8. Advance time ─────────────────────────────────
        self.time_elapsed += dwell_time
        self.step_count += 1

        # Store for next obs
        self.prev_control_signal = control_signal
        self.prev_velocity_norm = velocity_norm

        # ── 9. Compute Reward ───────────────────────────────
        reward = self._compute_reward(dopamine, velocity_norm,
                                       friction_delay_per_click)

        # ── 10. Build observation ───────────────────────────
        obs = np.array([
            self.toxicity,
            dopamine,
            risk_index,
            velocity_norm,
            control_signal,
        ], dtype=np.float32)

        # ── 11. Record history ──────────────────────────────
        intervention = self.controller.determine_intervention(control_signal)
        self.history.append({
            "step": self.step_count - 1,
            "simulated_time_sec": self.time_elapsed,
            "velocity_clicks_per_min": velocity,
            "toxicity": self.toxicity,
            "expected_reward": self.user.expected_reward,
            "rpe": self.user.rpe,
            "dopamine_level": dopamine,
            "dopamine_baseline": 0.2,
            "tolerance": self.user.expected_reward,
            "risk_index": risk_index,
            "control_signal_u": control_signal,
            "intervention_type": intervention.value,
            "interaction_type": "click",
            "lambda_intensity": self.kernel.intensity(
                self.time_elapsed, alpha1_eff, ALPHA2),
            "alpha1_effective": alpha1_eff,
            "alpha2": ALPHA2,
            "decay_factor": decay_factor,
        })

        terminated = self.step_count >= self.max_steps
        truncated = False

        return obs, reward, terminated, truncated, {}

    def _compute_reward(self, dopamine, velocity_norm, friction_delay):
        """
        Reward shaping for PPO (smooth gradient for learning):
            Base: +1.0 if dopamine < 0.5 AND velocity > 0.15 (healthy)
            Penalty: -5.0 if dopamine > 0.8 (addiction uncontrolled)
            Penalty: -10.0 if friction_delay > 2.5s (system too aggressive)
            Gradient: smooth interpolation in between for learnability.
        """
        reward = 0.0

        # ── Friction penalty (hard wall) ──
        if friction_delay > MAX_FRICTION_DELAY:
            return -10.0

        # ── Dopamine component (smooth gradient) ──
        if dopamine < 0.3:
            reward += 1.0        # Ideal: well controlled
        elif dopamine < 0.5:
            reward += 0.5        # Acceptable
        elif dopamine < 0.8:
            reward += -1.0 * (dopamine - 0.5) / 0.3   # Linear ramp to -1
        else:
            reward += -5.0       # Addiction not controlled

        # ── Velocity component (penalize extremes) ──
        if velocity_norm > 0.15:
            reward += 0.2        # User still engaged (not churned)
        else:
            reward -= 0.5        # Velocity too low = user leaving

        # ── Friction gentleness bonus ──
        if friction_delay < 1.0:
            reward += 0.3        # Minimal friction = good UX

        return float(reward)

    def get_history_dataframe(self):
        import pandas as pd
        return pd.DataFrame(self.history)
