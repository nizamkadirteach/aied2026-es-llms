from __future__ import annotations

from typing import Any

from typing import Any

from ..events import EventType, LearnerEvent
from ..llm.domain_expert_client import DomainExpertClient
from .hint_generator import generate_level_specific_hint



class Decision:
    def __init__(
        self,
        action: str = "",
        message: str = "",
        metadata: dict[str, Any] | None = None,
        reason: str = "",
    ):
        self.action = action
        self.message = message
        self.metadata = metadata or {}
        self.reason = reason


class ScaffoldBot:
    def __init__(
        self, config: dict[str, Any] | None = None, *, domain_expert: DomainExpertClient | None = None
    ) -> None:
        cfg = config or {}
        self.error_window = int(cfg.get("error_window", 2))
        self.hint_cap = int(cfg.get("hint_cap", 3))
        self.bottom_out_after = int(cfg.get("bottom_out_after", max(self.hint_cap, 3)))
        self.bottom_out_after = int(cfg.get("bottom_out_after", max(self.hint_cap, 3)))
        self.domain_expert = domain_expert
        self.hint_plan: list[str] | None = None

    def decide(self, event: dict[str, Any], state: dict[str, Any]) -> Decision:
        learner_evt = LearnerEvent.from_dict(event)
        et = learner_evt.event_type
        
        # Accept ANSWER_ATTEMPT (incorrect) OR explicit HINT_REQUEST
        if et not in {EventType.ANSWER_ATTEMPT, EventType.HINT_REQUEST}:
            return Decision()

        correct = learner_evt.correct
        hint_request = (et == EventType.HINT_REQUEST) or bool(event.get("event", {}).get("hint_request"))
        consecutive_errors = int(state.get("consecutive_errors", 0))
        consecutive_errors = int(state.get("consecutive_errors", 0))
        hint_count = int(state.get("hint_count", 0))

        next_hint_index = hint_count + 1
        if correct is True:
            return Decision()

        payload = event.get("event", {}) if isinstance(event, dict) else {}


        def _extract_hints() -> dict[str, str]:
            hint_items: list[Any] = []
            raw = payload.get("hints")
            if isinstance(raw, list):
                hint_items = raw
            meta = payload.get("metadata")
            if isinstance(meta, dict) and isinstance(meta.get("hints"), list):
                hint_items = meta.get("hints")  # type: ignore[assignment]

            out: dict[str, str] = {}
            ordered: list[str] = []
            for item in hint_items:
                if isinstance(item, dict):
                    text = item.get("hint_text") or item.get("text")
                    kind = (item.get("hint_type") or item.get("type") or "").strip().lower()
                    if text:
                        out.setdefault(kind, str(text).strip())
                elif item is not None:
                    ordered.append(str(item).strip())

            ordered = [t for t in ordered if t]
            if ordered and "minimal" not in out:
                out["minimal"] = ordered[0]
            if len(ordered) >= 2 and "scaffold" not in out:
                out["scaffold"] = ordered[1]
            if len(ordered) >= 3 and "bottom_out" not in out:
                out["bottom_out"] = ordered[2]

            bottom = payload.get("bottom_out_hint")
            if not bottom and isinstance(meta, dict):
                bottom = meta.get("bottom_out_hint")
            if bottom:
                out["bottom_out"] = str(bottom).strip()
            return {k: v for k, v in out.items() if v}

        problem_ctx = {
            "question_title": payload.get("question_title"),
            "question_prompt": payload.get("question_prompt"),
            "question_prompt_html": payload.get("question_prompt_html"),
            "domain": payload.get("domain"),
            "domain_label": payload.get("domain_label"),
        }

        hints = _extract_hints()
        expert_hint = ""
        
        # Pre-generate hint plan on first failure if enabled
        if self.domain_expert and not correct:
            # Detect misconception (still useful for plan generation)
            from ..nlg.misconceptions import detect_misconception
            misconception = detect_misconception(
                problem_ctx,
                payload.get("choice"),
                event.get("skill_id", "")
            )
            
            # Generate plan if missing
            if not self.hint_plan:
                self.hint_plan = self.domain_expert.generate_scaffold_plan(
                    event.get("skill_id"),
                    problem_ctx,
                    payload.get("choice"),
                    misconception=misconception
                )
            
            # Select hint based on current count
            # hint_count = 0 -> Plan[0] (Level 1)
            # hint_count = 1 -> Plan[1] (Level 2)
            plan_idx = min(hint_count, len(self.hint_plan) - 1)
            if self.hint_plan:  # Safety check
                expert_hint = self.hint_plan[plan_idx]

        # Fallback to minimal if expert empty
        micro_hint = (
            expert_hint
            or hints.get("minimal")
            or "Focus on the first operation that simplifies the expression."
        )

        scaffold_step = (
            expert_hint
            or hints.get("scaffold")
            or "Work through the next explicit step to isolate the unknown."
        )
        bottom_out_step = expert_hint or hints.get("bottom_out") or scaffold_step

        if hint_count >= self.hint_cap:
            # Only surface a denial when the learner explicitly asked for a hint.
            if not hint_request:
                return Decision()
            return Decision(
                action="HINT_DENIED",
                message="I want to see your thinking first so I know exactly how to help you. Try your best guess!",
                metadata={"hint_count": hint_count, "hint_cap": self.hint_cap},
                reason="hint_cap_reached",
            )

        # Helper function to clean hint messages
        def _clean_hint_message(msg: str) -> str:
            """Remove 'That's incorrect' and similar harsh phrases from hints."""
            msg = msg.strip()
            # Remove common harsh prefixes
            harsh_prefixes = [
                "That's incorrect.",
                "That is incorrect.",
                "That's wrong.",
                "That is wrong.",
                "Incorrect.",
            ]
            for prefix in harsh_prefixes:
                if msg.startswith(prefix):
                    msg = msg[len(prefix):].strip()
            return msg
        
        # Phase 3.1: Generate level-specific hints using Modular Scaffolding
        skill_id = event.get("skill_id", "")
        
        if consecutive_errors >= self.bottom_out_after or next_hint_index >= self.bottom_out_after:
            # FULL: Procedural micro-step
            generated_hint = generate_level_specific_hint(
                level="full",
                skill_id=skill_id,
                problem_context=problem_ctx,
                fallback_hint=bottom_out_step
            )
            
            return Decision(
                action="HINT_FULL",
                message=_clean_hint_message(generated_hint),
                metadata={
                    "hint_level": "full",
                    "consecutive_errors": consecutive_errors,
                    "hint_count": hint_count,
                    "scaffold_step": generated_hint,
                },
                reason="bottom_out_trigger",
            )

        if consecutive_errors >= self.error_window or next_hint_index >= 2:
            # MED: Structural bridge (formula + numbers)
            generated_hint = generate_level_specific_hint(
                level="medium",
                skill_id=skill_id,
                problem_context=problem_ctx,
                fallback_hint=scaffold_step
            )
            
            return Decision(
                action="HINT_MED",
                message=_clean_hint_message(generated_hint),
                metadata={
                    "hint_level": "medium",
                    "consecutive_errors": consecutive_errors,
                    "hint_count": hint_count,
                    "scaffold_step": generated_hint,
                },
                reason="error_window_reached",
            )

        # MIN: Conceptual nudge (no numbers)
        generated_hint = generate_level_specific_hint(
            level="minimal",
            skill_id=skill_id,
            problem_context=problem_ctx,
            fallback_hint=micro_hint
        )
        
        return Decision(
            action="HINT_MIN",
            message=_clean_hint_message(generated_hint),
            metadata={
                "hint_level": "minimal",
                "consecutive_errors": consecutive_errors,
                "hint_count": hint_count,
                "micro_hint": generated_hint,
            },
            reason="minimal_hint",
        )
