"""
PID Controller Module — Temporal Point-Process Aware
=====================================================
Implements the Circuit Breaker using PID Control Theory with
multi-factor risk assessment.

Instead of a hard "break" lockout, the controller outputs a
**smooth decay factor** that suppresses the System-1 (unconscious
scrolling) kernel weight α¹, allowing velocity to decrease
gradually rather than dropping to zero.
"""

import numpy as np
from typing import Tuple, Optional

from ..core.enums import InterventionType
from ..core.config import PIDConfig


class CircuitBreaker:
    """
    PID Controller for addiction mitigation with smooth intervention.
    
    Extended Risk Index Formula:
        I_risk = w1 * Addiction_Score + w2 * Toxicity_Score + w3 * Session_Duration
    
    Intervention Output:
        decay_factor ∈ [0, 1]  —  applied as  α¹_eff = α¹_base · decay_factor
        1.0 = no suppression,  0.0 = full suppression of System-1.
    """
    
    def __init__(self, config: Optional[PIDConfig] = None):
        self.config = config or PIDConfig()
        
        # PID gains
        self.kp = self.config.kp
        self.ki = self.config.ki
        self.kd = self.config.kd
        
        # Threshold
        self.threshold = self.config.threshold
        
        # Risk weights (3 components)
        self.w1 = self.config.w1  # Addiction Score (RPE)
        self.w2 = self.config.w2  # Toxicity
        self.w3 = self.config.w3  # Session duration
        
        # Intervention thresholds (used for labeling only)
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
        
        Formula:
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
        
        # Weighted sum
        risk = (
            self.w1 * normalized_addiction +
            self.w2 * normalized_toxicity +
            self.w3 * normalized_session
        )
        
        return float(np.clip(risk, 0.0, 1.0))
    
    def compute_control_signal(
        self, 
        addiction_score: float, 
        toxicity_score: float,
        session_duration: float = 0.0,
        dt: float = 1.0
    ) -> Tuple[float, float]:
        """
        Compute PID control signal u(t) with RL + Toxicity risk metrics.
        
        Returns:
            (control_signal, risk_index) — both clipped to [0, 1].
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
        control_signal = float(np.clip(control_signal, 0.0, 1.0))
        
        # Update adaptive threshold (slowly learn user's "normal")
        if risk_index < self.config.safe_zone_threshold:  # User in safe zone
            self.adaptive_threshold = (
                (1 - self.threshold_learning_rate) * self.adaptive_threshold +
                self.threshold_learning_rate * self.threshold
            )
        
        return control_signal, risk_index
    
    # ------------------------------------------------------------------
    # NEW: Smooth decay factor for α¹ suppression
    # ------------------------------------------------------------------
    def compute_decay_factor(self, control_signal: float) -> float:
        """
        Convert control signal u(t) into a smooth decay factor for α¹.
        
        Returns a value in [0, 1]:
            1.0  →  no suppression  (control_signal ≤ friction_threshold)
            0.0  →  full suppression (control_signal = 1.0)
        
        The mapping is a linear ramp between friction_threshold and 1.0,
        which produces a smooth, continuous reduction in System-1 intensity
        instead of a hard on/off break.
        """
        if control_signal <= self.friction_threshold:
            return 1.0  # Below minimum intervention — no suppression
        
        # Linear ramp: 1 → 0 as control_signal goes friction_threshold → 1
        suppression = (control_signal - self.friction_threshold) / (
            1.0 - self.friction_threshold
        )
        return float(np.clip(1.0 - suppression, 0.0, 1.0))
    
    def determine_intervention(self, control_signal: float) -> InterventionType:
        """
        Determine intervention label (for logging / visualization).
        This no longer drives a hard lockout — it is purely descriptive.
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
