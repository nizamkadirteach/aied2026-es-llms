from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List

@dataclass
class ClusterConfig:
    """
    Contains the probabilistic parameters governing synthetic student capability.
    Derived empirically from ASSISTments dataset centroids.
    """
    name: str
    init_mastery: float
    learn_rate: float
    slip: float
    guess: float
    hint_sensitivity: float  # How much a pedagogical hint boosts underlying mastery
    frustration_tolerance: int
    avg_hints: float  
    avg_correct: float 

# The 4 Student Archetypes discovered in our methodology
CLUSTERS = {
    "cluster_0": ClusterConfig(
        name="Struggling_Persisting",
        init_mastery=0.15,
        learn_rate=0.05,
        slip=0.25,
        guess=0.15,
        hint_sensitivity=0.2, 
        frustration_tolerance=4, 
        avg_hints=1.85,
        avg_correct=0.28
    ),
    "cluster_1": ClusterConfig(
        name="Low_Performer",
        init_mastery=0.20,
        learn_rate=0.08,
        slip=0.20,
        guess=0.20,
        hint_sensitivity=0.15,
        frustration_tolerance=2,
        avg_hints=1.53,
        avg_correct=0.30
    ),
    "cluster_2": ClusterConfig(
        name="Average",
        init_mastery=0.40,
        learn_rate=0.15,
        slip=0.10,
        guess=0.15,
        hint_sensitivity=0.10,
        frustration_tolerance=3,
        avg_hints=0.80,
        avg_correct=0.40
    ),
    "cluster_3": ClusterConfig(
        name="High_Performer",
        init_mastery=0.65,
        learn_rate=0.30, 
        slip=0.05,
        guess=0.10,
        hint_sensitivity=0.05, 
        frustration_tolerance=5,
        avg_hints=0.33,
        avg_correct=0.57
    ),
}

class ReactiveStudent:
    """
    Stochastic cognitive model of a learner parameterized by BKT initial state.
    Used for massive Monte Carlo parallel evaluations to test "Mastery Gain per Hint".
    """
    def __init__(self, config: ClusterConfig):
        self.cfg = config
        self.mastery = self.cfg.init_mastery
        self.history = []
        
    def react(self, tutor_actions: List[str]):
        """Update internal state based on tutor actions."""
        help_keywords = ["HINT", "SCAFFOLD", "GUIDE", "BASELINE_RESPONSE"]
        has_hint = any(k in a for a in tutor_actions for k in help_keywords)
        if has_hint:
            self.mastery = min(0.99, self.mastery + (1 - self.mastery) * self.cfg.hint_sensitivity)
            
    def attempt(self) -> dict:
        """Generate an attempt based on current internal mastery."""
        p_correct = self.mastery * (1 - self.cfg.slip) + (1 - self.mastery) * self.cfg.guess
        correct = random.random() < p_correct
        
        # Simplified affective state
        if self.mastery > 0.7:
            confidence = 0.9
        elif self.mastery > 0.4:
            confidence = 0.6
        else:
            confidence = 0.3
            
        return {
            "correct": correct,
            "confidence": confidence,
            "choice": "CORRECT" if correct else "WRONG"
        }
