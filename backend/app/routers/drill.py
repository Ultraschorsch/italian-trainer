import random

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import require_profile
from ..models import Lexeme, Profile
from ..schemas import DrillCheck
from .. import conjugation
from .review import _pool, _normalize  # gleiche Level-Logik/Normalisierung wie beim regulären Üben

router = APIRouter()

ALL_TENSES = [
    "presente", "passato_prossimo", "imperfetto",
    "futuro_semplice", "condizionale_semplice", "congiuntivo_presente",
]


@router.get("/drill/verb")
def next_drill_verb(
    tense: str = "presente",
    db: Session = Depends(get_db),
    profile: Profile = Depends(require_profile),
):
    if tense not in ALL_TENSES:
        tense = "presente"

    verbs = _pool(db, profile).filter(Lexeme.pos == "verb").all()
    if not verbs:
        return {"done": True, "message": "Keine Verben für dieses Level vorhanden."}

    lexeme = random.choice(verbs)
    return {
        "done": False,
        "lexeme_id": lexeme.id,
        "italian": lexeme.italian,
        "german": lexeme.german,
        "level": lexeme.level,
        "tense": tense,
        "tense_label": conjugation.TENSE_LABELS_DE.get(tense, tense),
        "persons": conjugation.PERSONS,
    }


@router.post("/drill/check")
def check_drill(
    submission: DrillCheck,
    db: Session = Depends(get_db),
    profile: Profile = Depends(require_profile),
):
    lexeme = db.query(Lexeme).get(submission.lexeme_id)
    if not lexeme:
        return {"error": "Vokabel nicht gefunden."}

    results = {}
    all_correct = True
    for person in conjugation.PERSONS:
        given = submission.answers.get(person, "")
        expected = conjugation.conjugate(
            lexeme.italian, submission.tense, person,
            conj_class=lexeme.conjugation_class, irregular_forms=lexeme.irregular_forms,
        )
        correct = _normalize(given) == _normalize(expected)
        if not correct:
            all_correct = False
        results[person] = {"given": given, "expected": expected, "correct": correct}

    return {"results": results, "all_correct": all_correct}
