from __future__ import annotations

from typing import Any

from .scaffold_bot import Decision
from ..events import EventType, LearnerEvent


class EthicsBot:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        # ... (config unchanged) ...
        cfg = config or {}
        self.require_attempt_before_hint = bool(cfg.get("require_attempt_before_hint", True))
        self.forbid_bottom_out = bool(cfg.get("forbid_bottom_out", True))
        self.max_hints = int(cfg.get("max_hints", 3))
        self.proactive_support_threshold = int(cfg.get("proactive_support_threshold", 2))

    def decide(self, event: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | Decision:
        """Enforce ethical constraints and provide proactive support.
        
        Returns either a dict of constraints OR a Decision to suggest help.
        """
        hint_count = int(state.get("hint_count", 0))
        consecutive_errors = int(state.get("consecutive_errors", 0))
        
        # Proactive support: Offer help to struggling students
        learner_evt = LearnerEvent.from_dict(event)
        
        if (learner_evt.event_type == EventType.ANSWER_ATTEMPT and 
            hint_count == 0 and 
            consecutive_errors >= self.proactive_support_threshold):
            # Student struggling but hasn't asked for help
            return Decision(
                action="SUGGEST_HELP",
                message="Would you like a hint to help you get started?",
                metadata={
                    "consecutive_errors": consecutive_errors,
                    "hint_count": hint_count,
                    "proactive": True
                },
                reason="proactive_support"
            )
        
        # Standard constraint enforcement
        allow_bottom_out = not self.forbid_bottom_out and hint_count >= self.max_hints
        return {
            "require_attempt_before_hint": self.require_attempt_before_hint,
            "allow_bottom_out": allow_bottom_out,
            "max_hints": self.max_hints,
        }
