"""
User Agent mapping to Rescorla-Wagner (RL) model.
Provides mathematical abstraction for RPE (Reward Prediction Error).
"""

from ..core.config import RLConfig

class UserAgent:
    def __init__(self, config: RLConfig = None):
        self.config = config or RLConfig()
        self.expected_reward = self.config.initial_expected_reward
        self.rpe = 0.0
        
    def calculate_rpe(self, velocity: float, toxicity_score: float) -> float:
        """
        Rescorla-Wagner equation:
        V(t+1) = V(t) + alpha * [R(t) - V(t)]
        
        Reward R(t) is proxied by a combination of normalized velocity and toxicity.
        """
        # Normalize velocity
        norm_v = min(velocity / self.config.max_velocity_px_s, 1.0)
        
        # Reward R(t)
        actual_reward = min(norm_v + (toxicity_score * self.config.toxicity_reward_weight), 1.0)
        
        # RPE
        self.rpe = actual_reward - self.expected_reward
        
        # Update V(t+1)
        self.expected_reward = self.expected_reward + self.config.alpha * self.rpe
        
        return self.rpe
        
    def get_addiction_score(self) -> float:
        """
        Map RPE to a 0-1 scale. Max RPE is theoretically 1.0.
        """
        return max(0.0, min(self.rpe * self.config.rpe_scaling_factor, 1.0))
        
    def reset(self):
        self.expected_reward = self.config.initial_expected_reward
        self.rpe = 0.0
