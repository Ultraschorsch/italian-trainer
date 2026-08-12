from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import require_profile
from ..models import AskThread, AskMessage, Lexeme, Profile
from ..schemas import AskStart, AskMessageIn
from .. import llm_client
from ..config import settings

router = APIRouter()

POS_LABELS_DE = {
    "noun": "Nomen", "verb": "Verb", "adjective": "Adjektiv",
    "adverb": "Adverb", "other": "Sonstiges",
}


def _thread_to_dict(thread: AskThread):
    return {
        "thread_id": thread.id,
        "messages": [{"role": m.role, "content": m.content} for m in thread.messages],
    }


def _build_system_prompt(profile: Profile, lexeme: Lexeme, exercise_type, seed_context):
    lines = [
        "Du bist ein geduldiger Italienisch-Lernhelfer für einen deutschsprachigen Lerner "
        f"auf Niveau {profile.target_level} (CEFR).",
        f"Aktuelle Vokabel: '{lexeme.italian}' ({lexeme.german}), Wortart: {POS_LABELS_DE.get(lexeme.pos, lexeme.pos)}"
        + (f", Genus: {lexeme.gender}" if lexeme.gender else "")
        + (f", Konjugationsklasse: -{lexeme.conjugation_class}" if lexeme.conjugation_class else "")
        + ".",
    ]
    if seed_context:
        ctx_bits = []
        for key, label in [
            ("question", "Frage"), ("hint", "Hinweis"), ("given_answer", "gegebene Antwort"),
            ("expected_answer", "erwartete Antwort"), ("explanation", "automatische Erklärung"),
            ("tense", "Zeitform"), ("person", "Person"), ("direction", "Richtung"),
        ]:
            val = seed_context.get(key)
            if val not in (None, ""):
                ctx_bits.append(f"{label}: {val}")
        if ctx_bits:
            lines.append(
                f"Kontext der letzten Übung ({exercise_type or 'unbekannt'}): " + "; ".join(ctx_bits)
            )
    lines.append(
        "Beantworte Rückfragen kurz, konkret und auf Deutsch. Nutze bei Bedarf kurze "
        "italienische Beispielsätze mit deutscher Übersetzung. Keine langen Vorträge, "
        "sondern gezielt auf die Frage eingehen."
    )
    return "\n".join(lines)


@router.get("/vocab/search")
def search_vocab(q: str = "", db: Session = Depends(get_db), profile: Profile = Depends(require_profile)):
    q = q.strip()
    if len(q) < 2:
        return []
    like = f"%{q}%"
    results = (
        db.query(Lexeme)
        .filter((Lexeme.italian.ilike(like)) | (Lexeme.german.ilike(like)))
        .order_by(Lexeme.level, Lexeme.italian)
        .limit(20)
        .all()
    )
    return [
        {"id": lx.id, "italian": lx.italian, "german": lx.german, "level": lx.level, "pos": lx.pos}
        for lx in results
    ]


@router.post("/ask/start")
def start_thread(payload: AskStart, db: Session = Depends(get_db), profile: Profile = Depends(require_profile)):
    lexeme = db.query(Lexeme).get(payload.lexeme_id)
    if not lexeme:
        raise HTTPException(status_code=404, detail="Vokabel nicht gefunden.")

    thread = (
        db.query(AskThread)
        .filter(
            AskThread.profile_id == profile.id,
            AskThread.lexeme_id == lexeme.id,
            AskThread.exercise_type == payload.exercise_type,
        )
        .first()
    )
    if not thread:
        thread = AskThread(
            profile_id=profile.id,
            lexeme_id=lexeme.id,
            exercise_type=payload.exercise_type,
            seed_context=payload.context,
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)
    elif payload.context:
        # Neuere Übungssituation für denselben Thread -> Kontext aktualisieren,
        # damit Folgefragen sich auf den aktuellen Versuch beziehen können.
        thread.seed_context = payload.context
        db.commit()

    result = _thread_to_dict(thread)
    result["lexeme"] = {"italian": lexeme.italian, "german": lexeme.german}
    result["llm_enabled"] = settings.llm_enabled
    return result


@router.post("/ask/message")
def send_message(payload: AskMessageIn, db: Session = Depends(get_db), profile: Profile = Depends(require_profile)):
    thread = db.query(AskThread).get(payload.thread_id)
    if not thread or thread.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Chat-Thread nicht gefunden.")

    user_msg = AskMessage(thread_id=thread.id, role="user", content=payload.message)
    db.add(user_msg)
    db.commit()
    db.refresh(thread)

    system_prompt = _build_system_prompt(profile, thread.lexeme, thread.exercise_type, thread.seed_context)
    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m.role, "content": m.content} for m in thread.messages]

    try:
        reply = llm_client.chat(messages)
    except llm_client.LLMError as ex:
        reply = f"⚠️ {ex}"

    assistant_msg = AskMessage(thread_id=thread.id, role="assistant", content=reply)
    db.add(assistant_msg)
    db.commit()
    db.refresh(thread)

    return _thread_to_dict(thread)
