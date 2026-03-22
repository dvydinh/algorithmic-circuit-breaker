"""
Algorithmic Circuit Breaker — Simulation Runner
=================================================
Generates synthetic user-browsing sessions using a **Bi-exponential
Temporal Point-Process (TPP)** kernel that models dual cognitive
systems (Kahneman's System-1 / System-2).

Intervention is **smooth**: the PID control signal acts as a decay
factor on the System-1 kernel weight α¹, gradually reducing scroll
velocity instead of forcing an abrupt break.

Mathematical Model
------------------
Bi-exponential TPP kernel (conditional intensity):

    λ(t) = μ₀ + Σᵢ κ(t − tᵢ)

    κ(Δt) = α¹_eff · β¹ · exp(−β¹ · Δt)  +  α² · β² · exp(−β² · Δt)

Where:
    μ₀             = background base rate (spontaneous browsing impulse)
    α¹_base(T)     = α¹₀ + γ · toxicity   (System-1 scales with toxicity)
    α¹_eff         = α¹_base · decay_factor (PID suppression)
    decay_factor   ∈ [0, 1]                 (from CircuitBreaker.compute_decay_factor)

Intensity is computed in O(1) per step using the recursive property
of exponential kernels (algebraically identical to the naive sum).
"""

import numpy as np
import pandas as pd
import sys
import os

# Add path so we can import the models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_breaker.core.config import PIDConfig, RLConfig
from circuit_breaker.models.user_agent import UserAgent
from circuit_breaker.controllers.pid_controller import CircuitBreaker


# ──────────────────────────────────────────────────────────────
# TPP Kernel Hyperparameters
# ──────────────────────────────────────────────────────────────
MU0         = 0.3        # μ₀   — background base rate (events/sec)
ALPHA1_BASE = 0.4        # α¹₀  — baseline System-1 weight
GAMMA       = 0.5        # γ    — toxicity sensitivity for α¹
BETA1       = 5.0        # β¹   — System-1 decay rate (fast bursts)
ALPHA2      = 0.3        # α²   — System-2 weight (deliberate reading)
BETA2       = 0.5        # β²   — System-2 decay rate (slow, sustained)


class RecursiveTPPKernel:
    """
    O(1) recursive computation of the bi-exponential Hawkes-type
    intensity with background rate μ₀.

    For an exponential kernel κ(Δt) = α·β·exp(−β·Δt), the cumulative
    triggering sum A(t) over all past events satisfies the recursion:

        A(tₖ) = exp(−β·Δt) · A(tₖ₋₁) + 1       (when event at tₖ)
        A(t)  = exp(−β·(t − t_last)) · A(t_last) (between events)

    This is *algebraically identical* to:
        A(t) = Σᵢ exp(−β·(t − tᵢ))

    The full intensity is:
        λ(t) = μ₀ + α¹_eff · β¹ · A₁(t) + α² · β² · A₂(t)
    """

    def __init__(self, beta1: float, beta2: float, mu0: float):
        self.beta1 = beta1
        self.beta2 = beta2
        self.mu0   = mu0
        # Running recursive sums for each kernel component
        self.A1 = 0.0
        self.A2 = 0.0
        self.t_last = 0.0  # timestamp of the last update

    def _decay_to(self, t: float):
        """Decay both running sums forward to time t (no new event)."""
        dt = t - self.t_last
        if dt > 0:
            self.A1 *= np.exp(-self.beta1 * dt)
            self.A2 *= np.exp(-self.beta2 * dt)
            self.t_last = t

    def add_event(self, t_event: float):
        """Register a new event at t_event and update running sums."""
        self._decay_to(t_event)
        self.A1 += 1.0
        self.A2 += 1.0

    def intensity(self, t: float, alpha1_eff: float, alpha2: float) -> float:
        """
        Compute λ(t) = μ₀ + α¹_eff·β¹·A₁(t) + α²·β²·A₂(t)
        without mutating internal state.
        """
        dt = t - self.t_last
        a1 = self.A1 * np.exp(-self.beta1 * dt) if dt > 0 else self.A1
        a2 = self.A2 * np.exp(-self.beta2 * dt) if dt > 0 else self.A2
        return self.mu0 + alpha1_eff * self.beta1 * a1 + alpha2 * self.beta2 * a2


def ogata_thinning_step(
    t_start: float,
    window: float,
    kernel: RecursiveTPPKernel,
    alpha1_eff: float,
    alpha2: float,
    rng: np.random.Generator,
) -> list:
    """
    Sample events in [t_start, t_start + window] via Ogata's thinning.

    Uses the recursive kernel for O(1) intensity queries.
    Returns list of accepted event timestamps.
    """
    # Upper bound λ* — intensity is highest right at t_start (self-exciting)
    lambda_star = kernel.intensity(t_start, alpha1_eff, alpha2) * 1.5
    lambda_star = max(lambda_star, kernel.mu0 * 1.2)  # at least base rate

    accepted = []
    t = t_start
    t_end = t_start + window

    while t < t_end:
        # Draw inter-arrival from Exp(λ*)
        u1 = rng.random()
        dt_candidate = -np.log(max(u1, 1e-12)) / lambda_star
        t += dt_candidate

        if t >= t_end:
            break

        # True intensity at candidate time
        lam_t = kernel.intensity(t, alpha1_eff, alpha2)

        # Accept with probability λ(t) / λ*
        if rng.random() <= lam_t / lambda_star:
            kernel.add_event(t)
            accepted.append(t)
            # Update upper bound after accepted event (intensity may spike)
            lambda_star = max(
                kernel.intensity(t, alpha1_eff, alpha2) * 1.5,
                lambda_star,
            )

    return accepted


# ──────────────────────────────────────────────────────────────
# Main simulation
# ──────────────────────────────────────────────────────────────
def run_simulation(steps: int = 10000):
    print("=" * 60)
    print("ALGORITHMIC CIRCUIT BREAKER — 10,000 STEP SIMULATION")
    print("Bi-exponential TPP kernel  |  Smooth PID intervention")
    print("=" * 60)

    # Initialize components
    rl_config  = RLConfig(alpha=0.1, initial_expected_reward=0.2)
    pid_config = PIDConfig(
        kp=1.2, ki=0.1, kd=0.2,
        w1=0.6, w2=0.3, w3=0.1,
        circuit_break_threshold=0.45,
    )

    user       = UserAgent(config=rl_config)
    controller = CircuitBreaker(config=pid_config)
    rng        = np.random.default_rng(seed=42)
    kernel     = RecursiveTPPKernel(beta1=BETA1, beta2=BETA2, mu0=MU0)

    history = []

    # Simulation state
    time_elapsed = 0.0
    toxicity     = 0.1

    for step in range(steps):
        # ── 1. Toxicity random walk ──────────────────────────
        toxicity = float(np.clip(
            toxicity + rng.normal(0, 0.05), 0.0, 1.0
        ))

        # ── 2. Compute PID control signal (from previous state) ─
        addiction_score = user.get_addiction_score()
        control_signal, risk_index = controller.compute_control_signal(
            addiction_score=addiction_score,
            toxicity_score=toxicity,
            session_duration=time_elapsed,
            dt=1.0,
        )

        # ── 3. Smooth decay factor for α¹ ────────────────────
        decay_factor = controller.compute_decay_factor(control_signal)

        # α¹_base scales with toxicity:  α¹₀ + γ · T
        alpha1_base = ALPHA1_BASE + GAMMA * toxicity
        alpha1_eff  = alpha1_base * decay_factor

        # ── 4. Sample events from TPP (Ogata thinning) ───────
        window = 10.0  # seconds per step
        new_events = ogata_thinning_step(
            t_start=time_elapsed,
            window=window,
            kernel=kernel,
            alpha1_eff=alpha1_eff,
            alpha2=ALPHA2,
            rng=rng,
        )

        # Dwell time for this step (Pareto heavy-tail + 5 s floor)
        dwell_time = (rng.pareto(a=1.5) + 1) * 5.0

        # ── 5. Velocity from accepted events ──────────────────
        clicks   = len(new_events)
        velocity = (clicks * rl_config.px_per_interaction) / dwell_time

        # ── 6. λ(t) for logging ──────────────────────────────
        lambda_now = kernel.intensity(
            time_elapsed + window, alpha1_eff, ALPHA2
        )

        # ── 7. RPE on post-intervention velocity ─────────────
        user.calculate_rpe(velocity, toxicity)

        # ── 8. Intervention label (descriptive, not enforced) ─
        intervention = controller.determine_intervention(control_signal)

        time_elapsed += dwell_time

        # ── 9. Record ────────────────────────────────────────
        history.append({
            "step":                    step,
            "simulated_time_sec":      time_elapsed,
            "velocity_clicks_per_min": velocity,
            "toxicity":                toxicity,
            "expected_reward":         user.expected_reward,
            "rpe":                     user.rpe,
            "dopamine_level":          addiction_score,
            "dopamine_baseline":       0.2,
            "tolerance":               user.expected_reward,
            "risk_index":              risk_index,
            "control_signal_u":        control_signal,
            "intervention_type":       intervention.value,
            "interaction_type":        "click",
            # New columns for TPP analysis
            "alpha1_effective":        alpha1_eff,
            "alpha2":                  ALPHA2,
            "lambda_intensity":        lambda_now,
            "decay_factor":            decay_factor,
        })

    # ── Results ──────────────────────────────────────────────
    df = pd.DataFrame(history)

    print("\nSimulation Complete.")
    print(f"Total simulated time: {time_elapsed / 3600:.2f} hours")

    breaks_mask = (df["intervention_type"] == "break").astype(int)
    n_breaks = int(breaks_mask.diff().clip(lower=0).sum())
    print(f"Number of Break-level interventions: {n_breaks}")
    print(f"Average Dopamine Level: {df['dopamine_level'].mean():.4f}")
    print(f"Average Risk Index:     {df['risk_index'].mean():.4f}")
    print(f"Average Decay Factor:   {df['decay_factor'].mean():.4f}")
    print(f"Average Velocity:       {df['velocity_clicks_per_min'].mean():.2f}")
    print(f"Zero-velocity steps:    {(df['velocity_clicks_per_min'] == 0).sum()}")

    # Save results
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    csv_file = os.path.join(output_dir, "simulation_log.csv")
    df.to_csv(csv_file, index=False)
    print(f"\nResults saved to {csv_file}")

    return df


if __name__ == "__main__":
    run_simulation(10000)
