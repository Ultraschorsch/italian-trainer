import datetime
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..auth import require_profile
from ..models import Attempt, SrsState, Profile

router = APIRouter()

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


@router.get("/stats/timeline")
def timeline(days: int = 60, db: Session = Depends(get_db), profile: Profile = Depends(require_profile)):
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    attempts = (
        db.query(Attempt)
        .filter(Attempt.profile_id == profile.id, Attempt.created_at >= since)
        .order_by(Attempt.created_at.asc())
        .all()
    )

    by_day = defaultdict(lambda: {"total": 0, "correct": 0})
    by_level_day = defaultdict(lambda: defaultdict(lambda: {"total": 0, "correct": 0}))

    for a in attempts:
        day = a.created_at.date().isoformat()
        by_day[day]["total"] += 1
        by_day[day]["correct"] += int(a.correct)
        by_level_day[a.level][day]["total"] += 1
        by_level_day[a.level][day]["correct"] += int(a.correct)

    daily_series = [
        {"date": day, "total": v["total"], "correct": v["correct"], "accuracy": round(v["correct"] / v["total"] * 100, 1)}
        for day, v in sorted(by_day.items())
    ]

    # Anzahl "gemeisterter" Vokabeln pro Level (repetitions >= 3 gilt hier als gefestigt)
    mastered_by_level = defaultdict(int)
    states = (
        db.query(SrsState)
        .filter(SrsState.profile_id == profile.id, SrsState.repetitions >= 3)
        .all()
    )
    for s in states:
        mastered_by_level[s.lexeme.level] += 1

    total_reviews = len(attempts)
    total_correct = sum(1 for a in attempts if a.correct)
    overall_accuracy = round(total_correct / total_reviews * 100, 1) if total_reviews else 0

    due_count = (
        db.query(func.count(SrsState.id))
        .filter(SrsState.profile_id == profile.id, SrsState.due_at <= datetime.datetime.utcnow())
        .scalar()
    )

    return {
        "daily_series": daily_series,
        "mastered_by_level": {lvl: mastered_by_level.get(lvl, 0) for lvl in LEVELS},
        "overall_accuracy": overall_accuracy,
        "total_reviews": total_reviews,
        "due_now": due_count,
    }
