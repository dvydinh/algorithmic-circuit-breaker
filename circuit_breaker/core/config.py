"""
Configuration dataclasses for the Algorithmic Circuit Breaker.
Strict hyperparameter typing.
"""

from dataclasses import dataclass

@dataclass
class PIDConfig:
    """Hyperparameters for the PID Controller"""
    kp: float = 1.2
    ki: float = 0.1
    kd: float = 0.2
    
    # Weights for Risk Index = w1*addiction + w2*toxicity + w3*session
    w1: float = 0.6
    w2: float = 0.3
    w3: float = 0.1
    
    # Intervention thresholds
    friction_threshold: float = 0.3
    reroute_threshold: float = 0.6
    circuit_break_threshold: float = 0.45
    
    # Integration limits for anti-windup
    integral_max: float = 2.0
    integral_min: float = -0.5
    
    # Threshold learning
    threshold: float = 0.0
    threshold_learning_rate: float = 0.01
    
    # Risk calculation constants
    max_session_minutes: float = 45.0
    safe_zone_threshold: float = 0.3

@dataclass
class RLConfig:
    """Hyperparameters for the Rescorla-Wagner RPE Agent"""
    alpha: float = 0.1  # Learning rate
    initial_expected_reward: float = 0.0
    
    # Scientific scaling factors
    px_per_interaction: float = 600.0  # Heuristic: 1 simulated click equals approx 1 viewport scroll (600px)
    max_velocity_px_s: float = 800.0
    toxicity_reward_weight: float = 0.5
    rpe_scaling_factor: float = 2.5
