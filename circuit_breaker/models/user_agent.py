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
        self.current_dopamine = 0.0
        self.dopamine_decay = 0.95  # Default, can be overridden by Domain Randomization
        
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
        Map RPE to a 0-1 scale using a leaky integrator. Max RPE is theoretically 1.0.
        When RPE > 0, dopamine spikes. When RPE <= 0, dopamine decays exponentially.
        """
        if self.rpe > 0:
            self.current_dopamine += (self.rpe * self.config.rpe_scaling_factor)
            self.current_dopamine = min(self.current_dopamine, 1.0)
        else:
            self.current_dopamine *= self.dopamine_decay  # Configurable decay per step
            
        return max(0.0, self.current_dopamine)
        
    def reset(self):
        self.expected_reward = self.config.initial_expected_reward
        self.rpe = 0.0
        self.current_dopamine = 0.0
