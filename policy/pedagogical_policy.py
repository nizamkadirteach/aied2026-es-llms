from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import os
from pathlib import Path

import numpy as np

try:  # optional dependency; loaded lazily if policy_file is set
    import joblib  # type: ignore
except Exception:  # pragma: no cover
    joblib = None


@dataclass
class PedagogicalState:
    correct: bool | None
    pL: float | None
    affect_state: str | None
    error_streak: int
    hint_count: int
    domain: str | None
    skill_id: str | None


class PedagogicalPolicy:
    """
    Rule-based policy that orders existing agents for a step.

    No new agents are introduced; this simply chooses sequencing based on mastery,
    affect, correctness, and recent history.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self.mode = cfg.get("mode", "default")
        self.model = None
        policy_file = cfg.get("policy_file")
        if policy_file and joblib:
            try:
                path = Path(policy_file)
                if path.exists():
                    self.model = joblib.load(path)
            except Exception:
                self.model = None

    def choose_actions(self, state: PedagogicalState) -> List[str]:
        """Return an ordered list of agent names to apply."""
        if self.model is not None:
            # Map state -> observation vector expected by StudentEnv
            pL = state.pL if state.pL is not None else 0.5
            affect_map = {"frustrated": -1.0, "confused": -0.5, "neutral": 0.0, "engaged": 0.5}
            affect_val = affect_map.get((state.affect_state or "neutral").lower(), 0.0)
            obs = np.array(
                [float(pL), float(affect_val), float(state.error_streak), float(state.hint_count)],
                dtype=float,
            )
            try:
                action, _ = self.model.predict(obs, deterministic=True)
            except Exception:
                action = None
            # Action mapping from StudentEnv: 0=hint,1=remediate,2=motivate,3=next
            if action == 0:
                return ["feedback", "scaffold", "ethics", "motivator", "tutor"]
            if action == 1:
                return ["feedback", "scaffold", "ethics", "motivator", "tutor"]
            if action == 2:
                return ["motivator", "feedback", "ethics", "tutor"]
            if action == 3:
                return ["tutor"]
        if self.mode != "default":
            return ["feedback", "scaffold", "motivator", "ethics", "tutor"]

        correct = state.correct
        pL = state.pL if state.pL is not None else 0.5
        affect = (state.affect_state or "neutral").lower()
        error_streak = state.error_streak

        sequence: List[str] = []

        if correct is True:
            if pL < 0.4:
                sequence = ["feedback", "scaffold", "motivator", "ethics", "tutor"]
            else:
                sequence = ["feedback", "motivator", "ethics", "tutor"]
        else:
            # incorrect or unknown
            if affect == "frustrated" or error_streak >= 2:
                sequence = ["feedback", "scaffold", "motivator", "ethics", "tutor"]
            elif affect == "confused":
                sequence = ["feedback", "scaffold", "motivator", "ethics", "tutor"]
            else:
                sequence = ["feedback", "scaffold", "ethics", "motivator", "tutor"]

        return sequence
