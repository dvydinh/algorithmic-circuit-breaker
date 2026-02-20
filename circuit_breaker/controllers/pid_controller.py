"""
PID Controller Module - Enhanced with Multi-factor Risk Assessment
===================================================================
Implements the Circuit Breaker using PID Control Theory with
enhanced risk metrics including extremity and session duration.
"""

import numpy as np
from typing import Tuple, Optional

from ..core.enums import InterventionType
from ..core.config import PIDConfig


class CircuitBreaker:
    """
    Enhanced PID Controller for addiction mitigation.
    
    Extended Risk Index Formula:
    I_risk = w1 * Addiction_Score + w2 * Toxicity_Score + w3 * Session_Duration
    
    This provides a more comprehensive view of user risk state using the RL Agent's output.
    """
    
    def __init__(self, config: Optional[PIDConfig] = None):
        self.config = config or PIDConfig()
        
        # PID gains
        self.kp = self.config.kp
        self.ki = self.config.ki
        self.kd = self.config.kd
        
        # Threshold
        self.threshold = self.config.threshold
        
        # Risk weights (3 components now)
        self.w1 = self.config.w1  # Addiction Score (RPE)
        self.w2 = self.config.w2  # Toxicity
        self.w3 = self.config.w3  # Session duration
        
        # Intervention thresholds
        self.friction_threshold = self.config.friction_threshold
        self.reroute_threshold = self.config.reroute_threshold
        self.circuit_break_threshold = self.config.circuit_break_threshold
        
        # PID state
        self.integral_error = 0.0
        self.previous_error = 0.0
        
        # Adaptive threshold (learns from user)
        self.adaptive_threshold = self.threshold
        self.threshold_learning_rate = self.config.threshold_learning_rate
        
    def calculate_risk_index(
        self, 
        addiction_score: float, 
        toxicity_score: float,
        session_duration: float = 0.0
    ) -> float:
        """
        Calculate composite risk index with 3 core components.
        
        Enhanced Formula:
        I_risk = w1 * A + w2 * T + w3 * S
        
        Where:
        - A: Addiction Score (RPE mapped to 0-1)
        - T: Toxicity Score (Local from frontend, 0-1)
        - S: Session duration factor
        """
        # Addiction score is already mapped 0-1 from RL agent
        normalized_addiction = min(max(addiction_score, 0.0), 1.0)
        
        # Toxicity is absolute 0-1 from client
        normalized_toxicity = min(max(toxicity_score, 0.0), 1.0)
        
        # Session duration: longer sessions = higher risk
        session_minutes = session_duration / 60.0
        normalized_session = min(session_minutes / self.config.max_session_minutes, 1.0)
        
        # Weighted sum: Error is the sum of these metrics against a setpoint of 0.
        risk = (
            self.w1 * normalized_addiction +
            self.w2 * normalized_toxicity +
            self.w3 * normalized_session
        )
        
        return np.clip(risk, 0.0, 1.0)
    
    def compute_control_signal(
        self, 
        addiction_score: float, 
        toxicity_score: float,
        session_duration: float = 0.0,
        dt: float = 1.0
    ) -> Tuple[float, float]:
        """
        Compute PID control signal with RL + Toxicity risk metrics.
        """
        risk_index = self.calculate_risk_index(
            addiction_score, toxicity_score, session_duration
        )
        
        # Use adaptive threshold
        error = risk_index - self.adaptive_threshold
        
        # Proportional
        p_term = self.kp * error
        
        # Integral with anti-windup
        self.integral_error += error * dt
        self.integral_error = np.clip(
            self.integral_error, 
            self.config.integral_min, 
            self.config.integral_max
        )
        i_term = self.ki * self.integral_error
        
        # Derivative
        derivative = (error - self.previous_error) / dt
        d_term = self.kd * derivative
        self.previous_error = error
        
        # Combine
        control_signal = p_term + i_term + d_term
        control_signal = np.clip(control_signal, 0.0, 1.0)
        
        # Update adaptive threshold (slowly learn user's "normal")
        if risk_index < self.config.safe_zone_threshold:  # User in safe zone
            self.adaptive_threshold = (
                (1 - self.threshold_learning_rate) * self.adaptive_threshold +
                self.threshold_learning_rate * self.threshold
            )
        
        return control_signal, risk_index
    
    def determine_intervention(self, control_signal: float) -> InterventionType:
        """
        Determine intervention with configurable thresholds.
        """
        if control_signal > self.circuit_break_threshold:
            return InterventionType.BREAK
        elif control_signal > self.reroute_threshold:
            return InterventionType.REROUTE
        elif control_signal > self.friction_threshold:
            return InterventionType.FRICTION
        else:
            return InterventionType.NONE
    
    def reset(self):
        """Reset controller state."""
        self.integral_error = 0.0
        self.previous_error = 0.0
        self.adaptive_threshold = self.threshold
