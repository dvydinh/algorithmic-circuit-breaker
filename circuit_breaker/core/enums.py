"""
Enumeration types for the Circuit Breaker simulation.
"""

from enum import Enum


class InteractionType(Enum):
    """Types of user interactions with content."""
    CLICK = "click"
    SKIP = "skip"


class InterventionType(Enum):
    """
    Types of circuit breaker interventions.
    
    Intervention Thresholds:
    - NONE: control_signal <= 0.3
    - FRICTION: 0.3 < control_signal <= 0.6 (Add delay)
    - REROUTE: 0.6 < control_signal <= 0.8 (Change content)
    - BREAK: control_signal > 0.8 (Stop session)
    """
    NONE = "none"
    FRICTION = "friction"      # u(t) > 0.3: Add delay
    REROUTE = "reroute"        # u(t) > 0.6: Change content
    BREAK = "break"            # u(t) > 0.8: Stop session
