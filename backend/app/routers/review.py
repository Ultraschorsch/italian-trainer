import datetime
import random
import re
import unicodedata

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..auth import require_profile
from ..models import Lexeme, SrsState, Attempt, Profile
from ..schemas import AnswerSubmit
from .. import srs, conjugation, grammar_rules

router = APIRouter()

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

POS_EXERCISES = {
    "noun": ["translation", "article", "plural"],
    "verb": ["translation", "conjugation"],
    "adjective": ["translation"],
    "adverb": ["translation"],
    "other": ["translation"],
}

CONJUGATION_TENSES_BY_LEVEL = {
    "A1": ["presente"],
    "A2": ["presente", "passato_prossimo", "imperfetto"],
    "B1": ["presente", "passato_prossimo", "imperfetto", "futuro_semplice", "condizionale_semplice"],
    "B2": ["presente", "passato_prossimo", "imperfetto", "futuro_semplice", "condizionale_semplice", "congiuntivo_presente"],
}

PERSON_LABELS_DE = {
    "io": "ich", "tu": "du", "lui": "er", "lei": "sie",
    "noi": "wir", "voi": "ihr", "loro": "sie/Sie",
}


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w'àèéìòù\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _pool(db: Session, profile: Profile):
    max_idx = LEVELS.index(profile.target_level) if profile.target_level in LEVELS else 0
    allowed_levels = LEVELS[: max_idx + 1]
    return db.query(Lexeme).filter(Lexeme.level.in_(allowed_levels))


def _tenses_for(level: str):
    idx = LEVELS.index(level) if level in LEVELS else 0
    if idx == 0:
        return CONJUGATION_TENSES_BY_LEVEL["A1"]
    if idx == 1:
        return CONJUGATION_TENSES_BY_LEVEL["A2"]
    if idx == 2:
        return CONJUGATION_TENSES_BY_LEVEL["B1"]
    return CONJUGATION_TENSES_BY_LEVEL["B2"]


@router.get("/review/next")
def next_exercise(db: Session = Depends(get_db), profile: Profile = Depends(require_profile)):
    now = datetime.datetime.utcnow()

    # 1. Gibt es fällige Wiederholungen?
    due_state = (
        db.query(SrsState)
        .filter(SrsState.profile_id == profile.id, SrsState.due_at <= now)
        .order_by(SrsState.due_at.asc())
        .first()
    )

    lexeme = None
    exercise_type = None

    if due_state:
        lexeme = db.query(Lexeme).get(due_state.lexeme_id)
        exercise_type = due_state.exercise_type
    else:
        # 2. Neue Vokabel aus dem Pool einführen
        pool = _pool(db, profile).all()
        random.shuffle(pool)
        seen_pairs = {
            (s.lexeme_id, s.exercise_type)
            for s in db.query(SrsState).filter(SrsState.profile_id == profile.id).all()
        }
        for lex in pool:
            possible_types = POS_EXERCISES.get(lex.pos, ["translation"])
            candidates = [t for t in possible_types if (lex.id, t) not in seen_pairs]
            if candidates:
                lexeme = lex
                exercise_type = random.choice(candidates)
                break
        if lexeme is None and pool:
            # Alles schon eingeführt -> zufällige Wiederholung vorziehen
            lexeme = random.choice(pool)
            exercise_type = random.choice(POS_EXERCISES.get(lexeme.pos, ["translation"]))

    if lexeme is None:
        return {"done": True, "message": "Kein Vokabular für dieses Level vorhanden."}

    payload = {
        "done": False,
        "lexeme_id": lexeme.id,
        "exercise_type": exercise_type,
        "level": lexeme.level,
        "pos": lexeme.pos,
    }

    if exercise_type == "translation":
        direction = random.choice(["it_to_de", "de_to_it"])
        payload["direction"] = direction
        payload["question"] = lexeme.italian if direction == "it_to_de" else lexeme.german
        payload["hint"] = "Italienisch \u2192 Deutsch" if direction == "it_to_de" else "Deutsch \u2192 Italienisch"

    elif exercise_type == "conjugation":
        tense = random.choice(_tenses_for(lexeme.level))
        person = random.choice(conjugation.PERSONS)
        payload["tense"] = tense
        payload["person"] = person
        payload["tense_label"] = conjugation.TENSE_LABELS_DE.get(tense, tense)
        payload["person_label"] = PERSON_LABELS_DE.get(person, person)
        payload["question"] = f"{lexeme.italian} ({lexeme.german}) \u2014 {person} ({PERSON_LABELS_DE.get(person, person)})"

    elif exercise_type == "article":
        is_plural = random.random() < 0.4
        payload["plural"] = is_plural
        payload["question"] = lexeme.italian
        payload["hint"] = "Bestimmter Artikel" + (" (Plural)" if is_plural else " (Singular)")

    elif exercise_type == "plural":
        payload["question"] = lexeme.italian
        payload["hint"] = f"Plural von '{lexeme.italian}' ({lexeme.german})"

    return payload


@router.post("/review/answer")
def submit_answer(
    submission: AnswerSubmit,
    db: Session = Depends(get_db),
    profile: Profile = Depends(require_profile),
):
    lexeme = db.query(Lexeme).get(submission.lexeme_id)
    if not lexeme:
        return {"error": "Vokabel nicht gefunden."}

    given_norm = _normalize(submission.given_answer)
    expected = ""
    explanation = None
    correct = False

    if submission.exercise_type == "translation":
        expected = lexeme.german if submission.direction == "it_to_de" else lexeme.italian
        correct = given_norm == _normalize(expected)
        if not correct:
            explanation = f"Richtig wäre '{expected}'."

    elif submission.exercise_type == "conjugation":
        expected = conjugation.conjugate(
            lexeme.italian, submission.tense, submission.person,
            conj_class=lexeme.conjugation_class, irregular_forms=lexeme.irregular_forms,
        )
        correct = given_norm == _normalize(expected)
        if not correct:
            explanation = conjugation.explain_conjugation_error(
                lexeme.italian, submission.tense, submission.person, expected, submission.given_answer,
                conj_class=lexeme.conjugation_class,
            )

    elif submission.exercise_type == "article":
        expected = grammar_rules.determinate_article(lexeme.italian, lexeme.gender or "m", bool(submission.plural))
        correct = given_norm == _normalize(expected)
        if not correct:
            explanation = grammar_rules.explain_article_error(
                lexeme.italian, lexeme.gender or "m", bool(submission.plural), expected
            )

    elif submission.exercise_type == "plural":
        expected = lexeme.plural or grammar_rules.regular_plural(lexeme.italian, lexeme.gender or "m")
        correct = given_norm == _normalize(expected)
        if not correct:
            explanation = grammar_rules.explain_plural_error(lexeme.italian, lexeme.gender or "m", expected)

    # SRS-Zustand aktualisieren (anlegen falls neu)
    state = (
        db.query(SrsState)
        .filter(
            SrsState.profile_id == profile.id,
            SrsState.lexeme_id == lexeme.id,
            SrsState.exercise_type == submission.exercise_type,
        )
        .first()
    )
    if not state:
        state = SrsState(profile_id=profile.id, lexeme_id=lexeme.id, exercise_type=submission.exercise_type)
        db.add(state)

    result = srs.review(state, correct)
    state.easiness_factor = result.easiness_factor
    state.interval_days = result.interval_days
    state.repetitions = result.repetitions
    state.due_at = result.due_at
    state.last_reviewed_at = datetime.datetime.utcnow()

    attempt = Attempt(
        profile_id=profile.id,
        lexeme_id=lexeme.id,
        exercise_type=submission.exercise_type,
        level=lexeme.level,
        correct=correct,
        given_answer=submission.given_answer,
        expected_answer=expected,
        explanation=explanation,
    )
    db.add(attempt)
    db.commit()

    return {
        "correct": correct,
        "expected_answer": expected,
        "explanation": explanation,
        "next_due_in_days": state.interval_days,
    }
