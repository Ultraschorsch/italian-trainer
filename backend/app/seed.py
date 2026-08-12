"""Befüllt die Datenbank mit dem kuratierten Startvokabular.
Wird beim Container-Start einmalig ausgeführt (idempotent: bereits
vorhandene italian+pos Kombinationen werden übersprungen)."""
import json
import pathlib

from .database import SessionLocal, Base, engine
from .models import Lexeme

SEED_DIR = pathlib.Path(__file__).parent / "seed_data"

LEVEL_FILES = {
    "A1": "vocab_a1.json",
    "A2": "vocab_a2.json",
    "B1": "vocab_b1.json",
    "B2": "vocab_b2.json",
    "C1": "vocab_c1.json",
    "C2": "vocab_c2.json",
}


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        added = 0
        for level, filename in LEVEL_FILES.items():
            path = SEED_DIR / filename
            if not path.exists():
                continue
            entries = json.loads(path.read_text(encoding="utf-8"))
            for entry in entries:
                exists = (
                    db.query(Lexeme)
                    .filter(Lexeme.italian == entry["italian"], Lexeme.pos == entry["pos"])
                    .first()
                )
                if exists:
                    continue
                lex = Lexeme(level=level, **entry)
                db.add(lex)
                added += 1
        db.commit()
        print(f"Seed abgeschlossen: {added} neue Vokabeln hinzugefügt.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
