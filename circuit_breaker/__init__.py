"""
Algorithmic Circuit Breaker
===========================
A PID-controlled system to mitigate user addiction in Recommender Systems.

This package provides simulation tools for modeling:
- User behavior with dopamine-driven engagement
- PID controller for risk monitoring and intervention
"""

__version__ = "3.0.0"
__author__ = "Simulation Architect"

from .models.user_agent import UserAgent
from .controllers.pid_controller import CircuitBreaker
from .core.enums import InteractionType, InterventionType

__all__ = [
    "UserAgent",
    "CircuitBreaker",
    "InteractionType",
    "InterventionType",
]
