import csv
import io
import json

from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Lexeme

router = APIRouter()

"""
Erwartetes CSV-Format (Kopfzeile erforderlich), z.B. exportiert aus Duolingo-
Vokabellisten oder dem Kursmaterial deiner Frau:

italian,german,pos,level,gender,plural,conjugation_class,example_it,example_de,irregular_forms

Nur italian, german, pos, level sind Pflichtfelder. pos: noun|verb|adjective|adverb|other
gender nur bei noun relevant (m/f). conjugation_class nur bei verb: are|ere|ire|ire_isc
irregular_forms (optional, nur verb): JSON-String mit Ausnahmen, z.B.
{"presente": {"io": "vado", "tu": "vai", ...}}. Ungültiges JSON wird ignoriert
(Zeile wird trotzdem importiert, nur ohne die Ausnahmen).
"""

REQUIRED = ["italian", "german", "pos", "level"]


@router.post("/vocab/import")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    added, skipped = 0, 0
    seen_in_batch = set()
    for row in reader:
        if not all(row.get(f) for f in REQUIRED):
            skipped += 1
            continue
        key = (row["italian"].strip(), row["pos"].strip())
        if key in seen_in_batch:
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
        seen_in_batch.add(key)

        irregular_forms = None
        raw_irregular = (row.get("irregular_forms") or "").strip()
        if raw_irregular:
            try:
                irregular_forms = json.loads(raw_irregular)
            except (json.JSONDecodeError, TypeError):
                irregular_forms = None

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
            irregular_forms=irregular_forms,
        )
        db.add(lex)
        added += 1
    db.commit()

    return RedirectResponse(url=f"/?import_added={added}&import_skipped={skipped}", status_code=303)
