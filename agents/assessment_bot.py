from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

from ..models.assessment_bkt import BKTModel


class AssessmentBot:
    """Wrapper around the BKT model for orchestrator consumption."""

    def __init__(
        self,
        model: BKTModel | None = None,
        *,
        idle_reset_hours: float | None = None,
        idle_reset_enabled: bool | None = None,
        decay_hours: float | None = None,
    ) -> None:
        self.model = model or BKTModel()
        horizon = float(idle_reset_hours) if idle_reset_hours else None
        self.idle_reset_threshold = timedelta(hours=horizon) if horizon and horizon > 0 else None
        self.idle_reset_enabled = (
            bool(idle_reset_enabled) if idle_reset_enabled is not None else True
        )
        self.decay_hours = float(decay_hours) if decay_hours else None
        self._last_event: dict[tuple[str, str], datetime] = {}

    def fit(self, df: Any | None = None, **kwargs: Any) -> None:
        self.model.fit(df, **kwargs)

    def get_mastery(self, student_id: str, skill_id: str) -> float:
        return self.model.get_mastery(student_id, skill_id)

    def update_mastery(
        self,
        student_id: str,
        skill_id: str,
        is_correct: bool,
        *,
        event_timestamp: datetime | None = None,
    ) -> tuple[float, bool, bool, float]:
        reset_applied = False
        decayed = False
        key = (student_id, skill_id)

        if self.idle_reset_enabled and self.idle_reset_threshold and event_timestamp is not None:
            last_ts = self._last_event.get(key)
            if last_ts and event_timestamp - last_ts >= self.idle_reset_threshold:
                self.model.reset()
                reset_applied = True

        last_ts = self._last_event.get(key)
        if self.decay_hours and last_ts and event_timestamp and event_timestamp > last_ts:
            hours = (event_timestamp - last_ts).total_seconds() / 3600
            if hours > 0:
                prior = self.model.prior_for_skill(skill_id).p_L0
                current = self.model.get_mastery(student_id, skill_id)
                decay_factor = math.exp(-hours / self.decay_hours)
                decayed_value = prior + (current - prior) * decay_factor
                self.model.set_mastery(student_id, skill_id, decayed_value)
                decayed = True

        if event_timestamp:
            self._last_event[key] = event_timestamp

        predicted = self.model.predict_correctness(student_id, skill_id)
        mastery = self.model.update_mastery(student_id, skill_id, is_correct)
        return mastery, reset_applied, decayed, predicted
