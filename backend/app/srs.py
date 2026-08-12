"""
Klassischer SM-2 Spaced-Repetition-Algorithmus (wie ihn u.a. Anki in einer
Variante verwendet). Qualität der Antwort wird auf einer Skala 0-5 erwartet;
wir leiten sie hier vereinfacht aus "richtig/falsch" plus grober
Selbsteinschätzung ab (siehe map_quality).
"""
import datetime
from dataclasses import dataclass

from .models import SrsState


@dataclass
class ReviewResult:
    easiness_factor: float
    interval_days: float
    repetitions: int
    due_at: datetime.datetime


def map_quality(correct: bool, was_hard: bool = False) -> int:
    """Vereinfachte Übersetzung des Nutzer-Feedbacks in die SM-2 Qualitätsskala (0-5)."""
    if not correct:
        return 1
    return 3 if was_hard else 5


def review(state: SrsState, correct: bool, was_hard: bool = False) -> ReviewResult:
    quality = map_quality(correct, was_hard)

    ef = state.easiness_factor or 2.5
    reps = state.repetitions or 0
    interval = state.interval_days or 0

    if quality < 3:
        # Falsch beantwortet: zurück auf Anfang, aber Easiness bleibt (leicht) bestehen
        reps = 0
        interval = 0  # heute nochmal, bzw. sofort wieder fällig
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ef, 1)
        reps += 1

    ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(1.3, ef)

    due_at = datetime.datetime.utcnow() + datetime.timedelta(days=interval if interval > 0 else 0, minutes=0 if interval > 0 else 10)

    return ReviewResult(easiness_factor=ef, interval_days=interval, repetitions=reps, due_at=due_at)
