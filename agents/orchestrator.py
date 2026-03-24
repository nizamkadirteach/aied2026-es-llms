from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ..services import problem_service
from ..nlg.renderer import get_renderer
from ..affect.affect_detector import AffectDetector
from ..llm.domain_expert_client import DomainExpertClient
from ..policy.pedagogical_policy import PedagogicalPolicy, PedagogicalState
from ..state import StudentState
from ..utils import config as cfg
from ..utils import db as db_utils
from .assessment_bot import AssessmentBot
from .ethics_bot import EthicsBot
from .feedback_bot import FeedbackBot
from .motivator_bot import MotivatorBot
from .scaffold_bot import Decision, ScaffoldBot
from .tutor_bot import TutorBot


MODE_ES_LLMS = "es_llms"
MODE_BASELINE_DIRECT = "baseline_direct_llm"
MODE_AIED2026 = "aied2026"
ALLOWED_MODES = {MODE_ES_LLMS, MODE_BASELINE_DIRECT, MODE_AIED2026}


class Orchestrator:
    def __init__(self, *, config: dict[str, Any] | None = None, **deps: Any) -> None:
        self.config = copy.deepcopy(config) if config else cfg.load()
        self.training_cfg = _load_training_config()
        self.domain_overrides = self.training_cfg.get("domain_overrides", {})
        self._domain_override_cache: dict[tuple[str | None, str], dict[str, Any]] = {}
        reset_conf = self._resolve_domain_overrides(
            None, "resets", self.training_cfg.get("resets", {})
        )
        idle_hours = reset_conf.get("idle_hours")
        domain_expert_cfg = self.config.get("domain_expert", {}) or {}
        domain_expert_enabled = bool(domain_expert_cfg.get("enabled", False))
        self.domain_expert = (
            DomainExpertClient(domain_expert_cfg) if domain_expert_enabled else None
        )
        affect_cfg = self.config.get("affect", {}) or {}
        self.affect_enabled = bool(affect_cfg.get("enabled", False))
        self.affect_detector = AffectDetector(affect_cfg) if self.affect_enabled else None
        policy_cfg = self.config.get("policy", {}) or {}
        self.policy = PedagogicalPolicy(policy_cfg)
        self.policy_model = None
        policy_file = policy_cfg.get("policy_file") if isinstance(policy_cfg, dict) else None
        if policy_file:
            try:
                import joblib  # type: ignore

                self.policy_model = joblib.load(policy_file)
            except Exception:
                self.policy_model = None
        self.assess = deps.get(
            "assess",
            AssessmentBot(
                idle_reset_hours=idle_hours,
                idle_reset_enabled=reset_conf.get("enabled", True),
                decay_hours=reset_conf.get("decay_hours"),
            ),
        )
        self.tutor = deps.get("tutor", TutorBot(self.config.get("tutor", {})))
        self.scaffold = deps.get(
            "scaffold",
            ScaffoldBot(self.config.get("scaffold", {}), domain_expert=self.domain_expert),
        )
        self.feedback = deps.get(
            "feedback",
            FeedbackBot(self.config.get("feedback", {}), domain_expert=self.domain_expert),
        )
        self.motivator = deps.get("motivator", MotivatorBot(self.config.get("motivator", {})))
        self.ethics = deps.get("ethics", EthicsBot(self.config.get("ethics", {})))
        self.renderer = get_renderer(self.config)
        tutor_conf = self.config.get("tutor", {})
        self.mastery_threshold = float(
            tutor_conf.get("mastery_threshold", self.config.get("mastery_threshold", 0.9))
        )
        self._default_tutor_candidates = tuple(tutor_conf.get("candidates", []))
        self._session_state: dict[tuple[str, str], dict[str, Any]] = {}
        self._trace: list[dict[str, Any]] = []
        # PRODUCTION: Always use ES-LLMs mode
        # Other modes (AIED2026, Baseline) are kept in code but inactive
        self.default_mode = MODE_ES_LLMS
        
        # Initialize BaselineTutor for comparative studies
        from .baseline_bot import BaselineTutor
        self.baseline_tutor = BaselineTutor(self.config.get("baseline", {}))

    @classmethod
    def from_configs(cls, *, config_override: dict[str, Any] | None = None) -> Orchestrator:
        return cls(config=config_override)

    def step(self, event: dict[str, Any]) -> dict[str, Any]:


        sid, kid = event["student_id"], event["skill_id"]
        event_payload = event.get("event", {}) if isinstance(event, dict) else {}
        et = event.get("event", {}).get("type")
        state = self._session_state.setdefault(
            (sid, kid),
            {"consecutive_errors": 0, "consecutive_correct": 0, "hint_count": 0, "attempts": 0},
        )
        state.pop("reset_applied", None)
        state.pop("decayed", None)

        mastery_before = self.assess.get_mastery(sid, kid)
        predicted_prob = None
        if et == "answer":
            state["attempts"] += 1
            correct_flag = bool(event.get("event", {}).get("correct", False))
            problem_id = event_payload.get("prompt_id") or event_payload.get("question_title")
            if problem_id:
                history = state.setdefault("problem_history", {})
                history[problem_id] = correct_flag
            event_ts_raw = event.get("event", {}).get("timestamp")
            event_ts = None
            if isinstance(event_ts_raw, str):
                iso_value = event_ts_raw.strip()
                if iso_value.endswith("Z"):
                    iso_value = iso_value[:-1] + "+00:00"
                try:
                    event_ts = datetime.fromisoformat(iso_value)
                except ValueError:
                    event_ts = None
            pL, reset_applied, decayed, predicted_prob = self.assess.update_mastery(
                sid, kid, correct_flag, event_timestamp=event_ts
            )
            if correct_flag:
                state["consecutive_correct"] = state.get("consecutive_correct", 0) + 1
                state["consecutive_errors"] = 0
            else:
                state["consecutive_errors"] = state.get("consecutive_errors", 0) + 1
                state["consecutive_correct"] = 0
            if reset_applied:
                state["reset_applied"] = True
            if decayed:
                state["decayed"] = True
        else:
            pL = mastery_before

        event_payload = event.get("event", {})

        # Handle Baseline Mode (Direct LLM) - Return here to bypass Policy/Agent Selection
        req_mode = event.get("mode")
        if req_mode == MODE_BASELINE_DIRECT:
             bl_resp = self.baseline_tutor.process_turn(event, self._session_state.get((sid, kid)))
             return {
                 "actions": [bl_resp["action"]],
                 "messages": [bl_resp["message"]],
                 "mastery": float(pL),
                 "affect": None, # Baseline ignores affect
                 "constraints": {},
                 "trace": [],
                 "telemetry": {
                     "mastery": {"before": float(mastery_before), "after": float(pL)},
                     "prediction": {"bkt_prob": predicted_prob} if predicted_prob is not None else {}
                 },
                 "next_problem": None
             }

        agent_state = {
            **state,
            "pL": pL,
            "hint_cap": int(self.config.get("hint_cap", 3)),
        }
        affect_state = "neutral"
        if self.affect_detector:
            affect_state = self.affect_detector.infer_affect(
                correct=event.get("event", {}).get("correct"),
                confidence=event.get("event", {}).get("confidence"),
                error_streak=int(state.get("consecutive_errors", 0)),
                hint_count=int(state.get("hint_count", 0)),
                last_message=event_payload.get("message") or event_payload.get("prompt"),
            )
            agent_state["affect_state"] = affect_state
        # Build StudentState for downstream agents (optional usage)
        student_state = StudentState.from_event(
            student_id=sid,
            event=event_payload,
            mastery={kid: pL} if kid else {},
            affect=affect_state,
            last_action=None,
        )
        agent_state["student_state"] = student_state.to_dict()
        # Knowledge graph prerequisites
        try:
            if kid:
                prereqs = db_utils.get_prerequisites(kid)
                if prereqs:
                    agent_state["prerequisites"] = prereqs
        except Exception:
            pass

        telemetry: dict[str, Any] = {}
        telemetry["mastery"] = {
            "before": float(mastery_before),
            "after": float(pL),
        }
        telemetry["affect_state"] = affect_state
        if predicted_prob is not None:
            telemetry["prediction"] = {
                "bkt_prob": predicted_prob,
                "pfa_prob": None,
                "logistic_prob": None,
                "hybrid_prob": None,
            }
        # Placeholder RL signal for persistence; can be replaced by real policy outputs.
        telemetry["rl"] = {
            "state": {
                "pL": float(pL),
                "affect_state": affect_state,
                "error_streak": int(state.get("consecutive_errors", 0)),
                "hint_count": int(state.get("hint_count", 0)),
            },
            "action": None,
            "reward": None,
        }

        # Ethics still evaluated independently for constraints.
        ethics_decision = self.ethics.decide(event, agent_state)
        # Handle case where ethics returns a Decision (e.g., proactive help) by extracting metadata
        # to satisfy the StepResponse schema which requires constraints to be a dict.
        if isinstance(ethics_decision, Decision):
             constraints = ethics_decision.metadata or {}
             # Optimization: We could also choose to act on ethics_decision.action here if desired
        else:
             constraints = ethics_decision
        decisions: list[str] = []
        messages: list[str] = []
        trace_step: list[dict[str, Any]] = []
        trace_step.append(
            {
                "agent": "assessment",
                "action": "MASTERY_UPDATE" if et == "answer" else "MASTERY_LOOKUP",
                "metadata": {
                    "mastery_before": float(mastery_before),
                    "mastery_after": float(pL),
                    "predicted_prob": predicted_prob,
                },
            }
        )
        if self.affect_detector:
            trace_step.append(
                {
                    "agent": "affect",
                    "action": "AFFECT_INFERRED",
                    "metadata": {"affect_state": affect_state},
                }
            )

        event_payload = event.get("event", {})
        base_render_ctx: dict[str, Any] = {
            "skill_id": kid,
            "skill_name": event_payload.get("question_title") or event_payload.get("skill_name"),
            "domain": event_payload.get("domain"),
            "domain_label": event_payload.get("domain_label"),
            "question_title": event_payload.get("question_title"),
            "question_prompt": event_payload.get("question_prompt"),
            "question_prompt_html": event_payload.get("question_prompt_html"),
            "selected_choice": event_payload.get("choice"),
            "choice_feedback": event_payload.get("choice_feedback"),
            "diagram_alt": event_payload.get("diagram_alt"),
            "history": event_payload.get("history"),
            "metadata": event_payload.get("metadata"),
            "confidence": event_payload.get("confidence"),
            "correct": event_payload.get("correct"),
            "pL": pL,
            "reset_applied": state.get("reset_applied", False),
            "decayed": state.get("decayed", False),
            "hint_count": int(state.get("hint_count", 0)),
        }
        policy_state = PedagogicalState(
            correct=event_payload.get("correct"),
            pL=pL,
            affect_state=affect_state,
            error_streak=int(state.get("consecutive_errors", 0)),
            hint_count=int(state.get("hint_count", 0)),
            domain=event_payload.get("domain"),
            skill_id=kid,
        )
        sequence = self.policy.choose_actions(policy_state)
        trace_step.append(
            {"agent": "policy", "action": "AGENT_SEQUENCE", "metadata": {"sequence": sequence}}
        )

        agent_map = {
            "feedback": self.feedback,
            "scaffold": self.scaffold,
            "motivator": self.motivator,
            "ethics": self.ethics,
            "tutor": self.tutor,
        }

        domain = event_payload.get("domain") or self.config.get("domain")
        overrides = self._resolve_domain_overrides(domain, "tutor", {})
        override_candidates = overrides.get("candidates")
        if override_candidates is not None:
            candidates = list(override_candidates)
        else:
            candidates = list(self._default_tutor_candidates)
        tutor_mastery = overrides.get("mastery_threshold", self.mastery_threshold)

        for name in sequence:
            agent = agent_map.get(name)
            if agent is None:
                continue
            if name == "ethics":
                # Ethics already evaluated; skip to avoid duplicate decide.
                continue
            
            # Gold Standard Behavior: Stop after first agent to prevent excessive output
            if messages:
                break
            
            if name == "tutor":
                nxt = self.tutor.next_item(
                    sid,
                    kid,
                    {
                        "pL": pL,
                        "mastery_threshold": tutor_mastery,
                        "candidates": candidates,
                    },
                )
                if nxt:
                    target_skill = nxt.get("skill_id") or kid
                    selected_problem = None
                    history = state.get("problem_history", {})
                    exclude_correct = {pid for pid, ok in history.items() if ok}
                    retry_incorrect = [pid for pid, ok in history.items() if not ok]
                    if nxt.get("problem_id"):
                        selected_problem = problem_service.fetch_problem_with_hints(
                            nxt.get("problem_id")
                        )
                    if selected_problem is None and target_skill:
                        selected_problem = problem_service.select_problem(
                            target_skill,
                            nxt.get("subskill_id"),
                            exclude_correct=exclude_correct,
                            retry_incorrect=retry_incorrect,
                        )
                        if selected_problem and "hints" not in selected_problem:
                            selected_problem["hints"] = db_utils.fetch_problem_hints(
                                selected_problem.get("problem_id")
                            )
                    problem_id_for_action = (
                        nxt.get("problem_id")
                        or (selected_problem.get("problem_id") if selected_problem else None)
                        or target_skill
                    )
                    decisions.append(f"NEXT:{problem_id_for_action}")
                    trace_step.append(
                        {
                            "agent": "tutor",
                            "action": decisions[-1],
                            "reason": nxt.get("policy", "rule"),
                            "metadata": {**nxt, "problem": selected_problem},
                        }
                    )
                    if selected_problem:
                        telemetry.setdefault("next_problem", {})["problem_id"] = selected_problem.get(
                            "problem_id"
                        )
                        telemetry["next_problem"]["skill_id"] = selected_problem.get("skill_id")
                        telemetry["next_problem"]["subskill_id"] = selected_problem.get("subskill_id")
                        telemetry["next_problem"]["difficulty"] = selected_problem.get("difficulty")
                        telemetry["next_problem"]["is_transfer_task"] = selected_problem.get(
                            "is_transfer_task"
                        )
                        telemetry["next_problem"]["is_latex"] = selected_problem.get("is_latex")
                        telemetry["next_problem"]["question_type"] = selected_problem.get(
                            "question_type"
                        )
                        telemetry["next_problem"]["title"] = selected_problem.get("title")
                        telemetry["next_problem"]["prompt"] = selected_problem.get("prompt")
                        telemetry["next_problem"]["options"] = selected_problem.get("options")
                        telemetry["next_problem"]["diagram_url"] = selected_problem.get("diagram_url")
                        telemetry["next_problem"]["image_description"] = selected_problem.get(
                            "image_description"
                        )
                        telemetry["next_problem"]["hints"] = selected_problem.get("hints")
                    agent_state["next_problem"] = selected_problem
                continue

            d: Decision = agent.decide(event, agent_state)
            if d.action:
                decisions.append(d.action)
                render_ctx: dict[str, Any] = dict(base_render_ctx)
                render_ctx.update({"agent": name, "decision_reason": getattr(d, "reason", "")})
                if isinstance(d.metadata, dict):
                    render_ctx.update(d.metadata)
                render_ctx["agent_message"] = d.message
                msg = self.renderer.render(d.action, render_ctx)
                
                # Gold Standard Behavior: Only use the first message
                if not messages:
                    messages.append(msg)
                
                trace_step.append(
                    {
                        "agent": name,
                        "action": d.action,
                        "reason": getattr(d, "reason", ""),
                        "metadata": d.metadata,
                    }
                )
                if self.domain_expert and name in {"feedback", "scaffold"} and (
                    d.action.startswith("HINT") or d.action in {"REMEDIATE"}
                ):
                    trace_step.append(
                        {
                            "agent": name,
                            "action": "USED_DOMAIN_EXPERT",
                            "reason": "domain_expert_enabled",
                            "metadata": {"skill_id": kid},
                        }
                    )
                if d.action.startswith("HINT"):
                    state["hint_count"] = state.get("hint_count", 0) + 1
            elif d.message:
                if not messages:
                    messages.append(d.message)

        self._trace.append({"student": sid, "skill": kid, "events": trace_step})

        return {
            "actions": decisions,
            "messages": messages,
            "mastery": float(pL),
            "affect": None,
            "constraints": constraints,
            "trace": trace_step,
            "telemetry": telemetry,
            "next_problem": agent_state.get("next_problem"),
        }

    def get_trace(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._trace)

    def _resolve_domain_overrides(
        self, domain: str | None, key: str, default: dict[str, Any]
    ) -> dict[str, Any]:
        if not domain:
            return default
        cache_key = (domain, key)
        if cache_key in self._domain_override_cache:
            return self._domain_override_cache[cache_key]
        domain_cfg = self.domain_overrides.get(domain, {})
        value = domain_cfg.get(key, default) or default
        self._domain_override_cache[cache_key] = value
        return value


def _load_training_config() -> dict[str, Any]:
    cfg_path = Path("configs/training.yaml")
    if not cfg_path.exists():
        return {}
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
