import numpy as np
import pandas as pd
import sys
import os

# Add path so we can import the models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_breaker.core.config import PIDConfig, RLConfig
from circuit_breaker.models.user_agent import UserAgent
from circuit_breaker.controllers.pid_controller import CircuitBreaker

def run_simulation(steps=10000):
    print("=" * 60)
    print("ALGORITHMIC CIRCUIT BREAKER - 10,000 STEP SIMULATION")
    print("Testing PID stabilization on Rescorla-Wagner RPE index")
    print("=" * 60)

    # Initialize components
    rl_config = RLConfig(alpha=0.1, initial_expected_reward=0.2)
    pid_config = PIDConfig(kp=1.2, ki=0.1, kd=0.2, w1=0.6, w2=0.3, w3=0.1, circuit_break_threshold=0.45)
    
    user = UserAgent(config=rl_config)
    controller = CircuitBreaker(config=pid_config)

    history = []
    
    # Simulation state variables
    time_elapsed = 0.0
    toxicity = 0.1
    in_break = False
    break_timer = 0
    
    for step in range(steps):
        if in_break:
            # During a break, no content is consumed
            velocity = 0.0
            toxicity = 0.0
            dwell_time = 1.0
            
            # Let RPE naturally decay due to zero reward
            user.calculate_rpe(velocity, toxicity)
            
            break_timer -= 1
            if break_timer <= 0:
                in_break = False
                controller.reset()
        else:
            # Generate synthetic user behavior
            # 1. Clicks (Velocity logic): Poisson distribution (average 3 clicks per 'batch')
            clicks = np.random.poisson(lam=3.5)
            # 2. Dwell time: Pareto distribution for heavy-tailed consumption times (shape a=1.5)
            # Add minimum dwell time of 5 seconds
            dwell_time = (np.random.pareto(a=1.5) + 1) * 5.0
            
            # Simulated velocity metric (clicks representing scrolling interaction per min equivalent)
            velocity = (clicks * rl_config.px_per_interaction) / dwell_time
            
            # 3. Environmental Toxicity: Slowly shifting random walk based on environmental exposure
            toxicity = np.clip(toxicity + np.random.normal(0, 0.05), 0.0, 1.0)
            
            # Evaluate RL Agent RPE & Addiction
            user.calculate_rpe(velocity, toxicity)
        
        # Calculate Risk and Control Signal
        addiction_score = user.get_addiction_score()
        session_duration = time_elapsed
        
        control_signal, risk_index = controller.compute_control_signal(
            addiction_score=addiction_score, 
            toxicity_score=toxicity, 
            session_duration=session_duration,
            dt=dwell_time
        )
        
        # Circuit Breaker Logic
        intervention_triggered = False
        if control_signal > pid_config.circuit_break_threshold and not in_break:
            in_break = True
            break_timer = 300  # Break for 300 steps
            intervention_triggered = True
            
        # Determine intervention type string
        if in_break:
            intervention_str = 'break'
        elif control_signal > pid_config.circuit_break_threshold:
            intervention_str = 'break'
        elif control_signal > pid_config.reroute_threshold:
            intervention_str = 'reroute'
        elif control_signal > pid_config.friction_threshold:
            intervention_str = 'friction'
        else:
            intervention_str = 'none'
            
        time_elapsed += dwell_time
        
        history.append({
            "step": step,
            "simulated_time_sec": time_elapsed,
            "velocity_clicks_per_min": velocity,
            "toxicity": toxicity,
            "expected_reward": user.expected_reward,
            "rpe": user.rpe,
            "dopamine_level": addiction_score,
            "dopamine_baseline": 0.2,
            "tolerance": user.expected_reward,
            "risk_index": risk_index,
            "control_signal_u": control_signal,
            "intervention_type": intervention_str,
            "interaction_type": 'click'
        })

    # Convert to DataFrame
    df = pd.DataFrame(history)
    
    # Print Summary
    print("\nSimulation Complete.")
    print(f"Total simulated time: {time_elapsed/3600:.2f} hours")
    breaks_mask = (df['intervention_type'] == 'break').astype(int)
    print(f"Number of Circuit Breaks triggered: {breaks_mask.diff().clip(lower=0).sum()}")
    print(f"Average Dopamine Level (RPE-based Proxy): {df['dopamine_level'].mean():.4f}")
    print(f"Average Risk Index: {df['risk_index'].mean():.4f}")
    
    # Save results
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    csv_file = os.path.join(output_dir, "simulation_log.csv")
    df.to_csv(csv_file, index=False)
    print(f"\nResults saved to {csv_file}")
    
    return df

if __name__ == "__main__":
    run_simulation(10000)
