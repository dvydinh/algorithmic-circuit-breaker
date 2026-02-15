"""
Train PPO Agent for Hierarchical PID Control
==============================================
Uses Stable-Baselines3 PPO to learn optimal PID gain adjustments.

The PPO meta-controller observes the system state and outputs
delta-adjustments to [Kp, Ki, Kd, friction_threshold] at every
timestep. The underlying PID controller still performs real-time
risk assessment and intervention.

Usage:
    python train_rl_agent.py                  # Train + Evaluate
    python train_rl_agent.py --timesteps 200000  # Custom timesteps
"""

import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from env.circuit_breaker_env import CircuitBreakerEnv


# ─────────────────────────────────────────────────────────────
# Training callback for progress logging
# ─────────────────────────────────────────────────────────────
class ProgressCallback(BaseCallback):
    """Print training progress every N steps."""

    def __init__(self, print_freq=10_000, verbose=1):
        super().__init__(verbose)
        self.print_freq = print_freq

    def _on_step(self) -> bool:
        if self.num_timesteps % self.print_freq == 0:
            # Safely access info buffer
            if len(self.model.ep_info_buffer) > 0:
                mean_reward = np.mean(
                    [ep["r"] for ep in self.model.ep_info_buffer]
                )
                mean_len = np.mean(
                    [ep["l"] for ep in self.model.ep_info_buffer]
                )
                print(
                    f"  [Step {self.num_timesteps:>7,}] "
                    f"Mean Reward: {mean_reward:+.2f}  |  "
                    f"Mean Ep Len: {mean_len:.0f}"
                )
        return True


# ─────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────
def train(timesteps: int = 100_000, save_path: str = "output/ppo_circuit_breaker"):
    print("=" * 60)
    print("PPO-PID HIERARCHICAL CONTROLLER — TRAINING")
    print(f"Total timesteps: {timesteps:,}")
    print("=" * 60)

    env = CircuitBreakerEnv(max_steps=500, seed=42)

    model = PPO(
        "MlpPolicy",
        env,
        verbose=0,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        seed=42,
    )

    print("\nTraining PPO agent...")
    model.learn(
        total_timesteps=timesteps,
        callback=ProgressCallback(print_freq=10_000),
    )

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    model.save(save_path)
    print(f"\nModel saved to: {save_path}.zip")

    return model


# ─────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────
def evaluate(model, eval_steps: int = 2000):
    print("\n" + "=" * 60)
    print(f"EVALUATING TRAINED PPO-PID CONTROLLER — {eval_steps} STEPS")
    print("=" * 60)

    env = CircuitBreakerEnv(max_steps=eval_steps, seed=123)
    obs, _ = env.reset()
    total_reward = 0.0

    for i in range(eval_steps):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        if terminated or truncated:
            break

    df = env.get_history_dataframe()

    # ── Save CSV ─────────────────────────────────────────────
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "simulation_log.csv")
    df.to_csv(csv_path, index=False)

    # ── Print summary ────────────────────────────────────────
    print(f"\nTotal Reward:          {total_reward:+.2f}")
    print(f"Total Simulated Time:  {df['simulated_time_sec'].max() / 3600:.2f} hours")
    print(f"Avg Dopamine Level:    {df['dopamine_level'].mean():.4f}")
    print(f"Avg Risk Index:        {df['risk_index'].mean():.4f}")
    print(f"Avg Decay Factor:      {df['decay_factor'].mean():.4f}")
    print(f"Avg Velocity:          {df['velocity_clicks_per_min'].mean():.2f}")
    n_breaks = (df['intervention_type'] == 'break').sum()
    print(f"Break interventions:   {n_breaks}")
    print(f"\nResults saved to: {csv_path}")

    return df


# ─────────────────────────────────────────────────────────────
# Visualization
# ─────────────────────────────────────────────────────────────
def visualize():
    """Run the existing visualization pipeline."""
    print("\nGenerating visualization dashboard...")
    import subprocess
    subprocess.run(
        [sys.executable, "visualize_results.py",
         "--input", "output/simulation_log.csv",
         "--output", "simulation_result.png"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    print("Dashboard saved to: simulation_result.png")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Train & Evaluate PPO-PID Hierarchical Controller"
    )
    parser.add_argument(
        "--timesteps", type=int, default=100_000,
        help="Total PPO training timesteps (default: 100000)"
    )
    parser.add_argument(
        "--eval-steps", type=int, default=2000,
        help="Evaluation episode length (default: 2000)"
    )
    parser.add_argument(
        "--skip-train", action="store_true",
        help="Skip training, load existing model"
    )
    args = parser.parse_args()

    model_path = "output/ppo_circuit_breaker"

    if args.skip_train:
        print("Loading pre-trained model...")
        model = PPO.load(model_path)
    else:
        model = train(timesteps=args.timesteps, save_path=model_path)

    df = evaluate(model, eval_steps=args.eval_steps)
    visualize()

    print("\n" + "=" * 60)
    print("ALL DONE. Pipeline complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
