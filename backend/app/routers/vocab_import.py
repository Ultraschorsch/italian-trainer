import csv
import io

from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Lexeme

router = APIRouter()

"""
Erwartetes CSV-Format (Kopfzeile erforderlich), z.B. exportiert aus Duolingo-
Vokabellisten oder dem Kursmaterial deiner Frau:

italian,german,pos,level,gender,plural,conjugation_class,example_it,example_de

Nur italian, german, pos, level sind Pflichtfelder. pos: noun|verb|adjective|adverb|other
gender nur bei noun relevant (m/f). conjugation_class nur bei verb: are|ere|ire|ire_isc|irregular
"""

REQUIRED = ["italian", "german", "pos", "level"]


@router.post("/vocab/import")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    added, skipped = 0, 0
    for row in reader:
        if not all(row.get(f) for f in REQUIRED):
            skipped += 1
            continue
        exists = (
            db.query(Lexeme)
            .filter(Lexeme.italian == row["italian"].strip(), Lexeme.pos == row["pos"].strip())
            .first()
        )
        if exists:
            skipped += 1
            continue
        lex = Lexeme(
            italian=row["italian"].strip(),
            german=row["german"].strip(),
            pos=row["pos"].strip(),
            level=row["level"].strip().upper(),
            gender=(row.get("gender") or "").strip() or None,
            plural=(row.get("plural") or "").strip() or None,
            conjugation_class=(row.get("conjugation_class") or "").strip() or None,
            example_it=(row.get("example_it") or "").strip() or None,
            example_de=(row.get("example_de") or "").strip() or None,
        )
        db.add(lex)
        added += 1
    db.commit()

    return RedirectResponse(url=f"/?import_added={added}&import_skipped={skipped}", status_code=303)
