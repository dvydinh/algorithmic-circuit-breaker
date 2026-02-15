import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Đảm bảo đường dẫn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_breaker.core.config import PIDConfig, RLConfig
from circuit_breaker.models.user_agent import UserAgent
from circuit_breaker.controllers.pid_controller import CircuitBreaker
from env.circuit_breaker_env import CircuitBreakerEnv

# ── Hàm chạy mô phỏng môi trường tĩnh (Baseline & Static PID) ──
def run_static_scenario(pid_config, steps=2000):
    from run_simulation import RecursiveTPPKernel, ogata_thinning_step, \
                               ALPHA1_BASE, GAMMA, BETA1, ALPHA2, BETA2, MU0
    
    rl_config = RLConfig(alpha=0.1, initial_expected_reward=0.2)
    user = UserAgent(config=rl_config)
    controller = CircuitBreaker(config=pid_config)
    rng = np.random.default_rng(seed=42)
    kernel = RecursiveTPPKernel(beta1=BETA1, beta2=BETA2, mu0=MU0)

    history = []
    time_elapsed = 0.0
    toxicity = 0.1
    prev_velocity_norm = 0.5
    state_window = np.zeros((5, 3), dtype=np.float32)
    MAX_FRICTION_DELAY = 2.5

    for step in range(steps):
        # Adversarial Toxicity
        base_cycle = 0.5 + 0.4 * np.sin(time_elapsed / 800.0)
        noise_spike = rng.normal(0, 0.15)
        toxicity = float(np.clip(base_cycle + noise_spike, 0.0, 1.0))
        if prev_velocity_norm < 0.3:
            spike = rng.uniform(0.85, 1.0)
            toxicity = float(np.clip(toxicity * 0.3 + spike * 0.7, 0.0, 1.0))

        addiction_score = user.get_addiction_score()
        control_signal, risk_index = controller.compute_control_signal(
            addiction_score, toxicity, time_elapsed, 1.0
        )
        
        decay_factor = controller.compute_decay_factor(control_signal)
        alpha1_eff = min((ALPHA1_BASE + GAMMA * toxicity) * decay_factor, 0.6)

        window = 10.0
        new_events = ogata_thinning_step(time_elapsed, window, kernel, alpha1_eff, ALPHA2, rng)
        base_dwell = (rng.pareto(a=1.5) + 1) * 5.0
        clicks = len(new_events)
        
        friction_delay_per_click = 0.0
        if control_signal > pid_config.friction_threshold:
            raw_delay = control_signal * 2.5
            friction_delay_per_click = min(raw_delay, MAX_FRICTION_DELAY)
            
        dwell_time = base_dwell + (clicks * friction_delay_per_click)
        velocity = (clicks * rl_config.px_per_interaction) / max(dwell_time, 0.1)
        velocity_norm = min(velocity / rl_config.max_velocity_px_s, 1.0)

        # Trượt lịch sử
        state_window = np.roll(state_window, -1, axis=0)
        state_window[-1] = [velocity_norm, toxicity, min(dwell_time / 60.0, 1.0)]
        prev_velocity_norm = velocity_norm

        lambda_now = kernel.intensity(time_elapsed + window, alpha1_eff, ALPHA2)
        user.calculate_rpe(velocity, toxicity)
        time_elapsed += dwell_time

        history.append({
            "step": step,
            "simulated_time_sec": time_elapsed,
            "dopamine_level": addiction_score,
            "toxicity": toxicity,
            "control_signal_u": control_signal,
            "friction_delay_applied": friction_delay_per_click
        })

    return pd.DataFrame(history)

# ── Hàm chạy mô phỏng PPO ──
def run_ppo_scenario(model_path, steps=2000):
    try:
        from stable_baselines3 import PPO
        model = PPO.load(model_path)
    except:
        print(f"Warning: Không thể load mô hình {model_path}, trả về DF rỗng.")
        return pd.DataFrame({'step': range(steps), 'dopamine_level': 0, 'friction_delay_applied': 0})
        
    env = CircuitBreakerEnv(max_steps=steps, seed=123)
    obs, _ = env.reset()
    history = []
    
    for i in range(steps):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        hist = env.history[-1]
        history.append({
            "step": i,
            "simulated_time_sec": hist["simulated_time_sec"],
            "dopamine_level": hist["dopamine_level"],
            "toxicity": hist["toxicity"],
            "control_signal_u": hist["control_signal_u"],
            "friction_delay_applied": env.current_friction_delay
        })
        if terminated or truncated:
            break
            
    return pd.DataFrame(history)

def main():
    print("=" * 60)
    print("CHẠY ABLATION STUDY: So sánh 3 kịch bản")
    print("=" * 60)
    
    os.makedirs("output", exist_ok=True)
    
    # 1. Baseline: Tắt hoàn toàn PID (Gain = 0, Ma sát = Mức không tưởng)
    print("1. Đang chạy mô phỏng Baseline (Không có cơ chế phòng vệ)...")
    base_config = PIDConfig(kp=0.0, ki=0.0, kd=0.0, friction_threshold=999.0)
    df_base = run_static_scenario(base_config, steps=2000)
    df_base.to_csv("output/baseline_ablation.csv", index=False)
    
    # 2. Static PID: Lấy cấu hình gốc chuẩn chỉnh
    print("2. Đang chạy mô phỏng Static PID (Sử dụng hệ số PID truyền thống)...")
    static_config = PIDConfig(kp=1.2, ki=0.1, kd=0.2, circuit_break_threshold=0.45)
    df_static = run_static_scenario(static_config, steps=2000)
    df_static.to_csv("output/static_pid_ablation.csv", index=False)
    
    # 3. PPO-PID: Sử dụng model đã train
    print("3. Đang chạy mô phỏng PPO-PID (Mô phỏng sử dụng siêu-điều khiển AI)...")
    df_ppo = run_ppo_scenario("output/ppo_circuit_breaker", steps=2000)
    df_ppo.to_csv("output/ppo_pid_ablation.csv", index=False)
    
    # ── VẼ ĐỒ THỊ ──
    print("\nĐang tạo biểu đồ đánh giá: ablation_result.png")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Giới hạn số bước vẽ cho dễ nhìn
    plot_steps = 1000
    
    # Vẽ Dopamine
    ax1.plot(df_base['step'][:plot_steps], df_base['dopamine_level'][:plot_steps], label='Baseline (No Intervention)', color='grey', alpha=0.7, linewidth=2, linestyle='--')
    ax1.plot(df_static['step'][:plot_steps], df_static['dopamine_level'][:plot_steps], label='Static PID', color='coral', alpha=0.9, linewidth=2)
    ax1.plot(df_ppo['step'][:plot_steps], df_ppo['dopamine_level'][:plot_steps], label='PPO-PID Hybrid', color='dodgerblue', alpha=0.9, linewidth=2.5)
    ax1.axhline(0.5, color='green', linestyle=':', label='Safe Dopamine Threshold (0.5)')
    ax1.axhline(0.8, color='red', linestyle=':', label='Addiction Threshold (0.8)')
    
    ax1.set_ylabel('Dopamine Level (RPE Integration)')
    ax1.set_title('Ablation Study: Dopamine Level Control Comparison', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, linestyle='--', alpha=0.5)
    
    # Vẽ Ma sát
    ax2.plot(df_base['step'][:plot_steps], df_base['friction_delay_applied'][:plot_steps], color='grey', alpha=0.7, linewidth=1.5)
    ax2.plot(df_static['step'][:plot_steps], df_static['friction_delay_applied'][:plot_steps], color='coral', alpha=0.9, linewidth=1.5)
    ax2.plot(df_ppo['step'][:plot_steps], df_ppo['friction_delay_applied'][:plot_steps], color='dodgerblue', alpha=0.9, linewidth=1.5)
    ax2.axhline(2.5, color='red', linestyle='--', alpha=0.5, label='Max Hard-Cap Friction (2.5s)')
    
    ax2.set_xlabel('Simulation Steps')
    ax2.set_ylabel('Applied Friction Delay (seconds)')
    ax2.set_title('Ablation Study: System Aggressiveness (Friction Injected)', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right')
    ax2.grid(True, linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig('output/ablation_result.png', dpi=300, facecolor='white')
    print("Hoàn tất! Biểu đồ lưu tại: output/ablation_result.png")

if __name__ == "__main__":
    main()
