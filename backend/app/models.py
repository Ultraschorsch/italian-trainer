import datetime
import uuid

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def _uuid():
    return str(uuid.uuid4())


class Profile(Base):
    """Ein Lern-Profil (eine Person). Wird entweder über den SSO-Header
    identifiziert (external_id = SSO-Benutzername) oder lokal per Picker
    (external_id = zufällige lokale ID, im Cookie gespeichert)."""
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=_uuid)
    external_id = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    target_level = Column(String, default="A1")  # A1, A2, B1, B2, C1, C2
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    srs_states = relationship("SrsState", back_populates="profile", cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="profile", cascade="all, delete-orphan")


class Lexeme(Base):
    """Ein Vokabeleintrag: Nomen, Verb, Adjektiv, ..."""
    __tablename__ = "lexemes"

    id = Column(String, primary_key=True, default=_uuid)
    italian = Column(String, nullable=False, index=True)
    german = Column(String, nullable=False)
    pos = Column(String, nullable=False)  # noun, verb, adjective, adverb, other
    level = Column(String, nullable=False, index=True)  # A1..C2
    gender = Column(String, nullable=True)  # m, f (nur für Nomen)
    plural = Column(String, nullable=True)  # explizite Pluralform, falls unregelmäßig
    conjugation_class = Column(String, nullable=True)  # are, ere, ire, irregular (nur Verben)
    irregular_forms = Column(JSON, nullable=True)  # {"presente": {"io": "vado", ...}, ...}
    example_it = Column(Text, nullable=True)
    example_de = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("italian", "pos", name="uq_lexeme_italian_pos"),)


class SrsState(Base):
    """SM-2 Zustand pro (Profil, Vokabel, Übungsart)."""
    __tablename__ = "srs_states"

    id = Column(String, primary_key=True, default=_uuid)
    profile_id = Column(String, ForeignKey("profiles.id"), nullable=False, index=True)
    lexeme_id = Column(String, ForeignKey("lexemes.id"), nullable=False, index=True)
    exercise_type = Column(String, nullable=False)  # translation, conjugation, article, plural

    easiness_factor = Column(Float, default=2.5)
    interval_days = Column(Float, default=0)
    repetitions = Column(Integer, default=0)
    due_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    last_reviewed_at = Column(DateTime, nullable=True)

    profile = relationship("Profile", back_populates="srs_states")
    lexeme = relationship("Lexeme")

    __table_args__ = (
        UniqueConstraint("profile_id", "lexeme_id", "exercise_type", name="uq_srs_profile_lexeme_type"),
    )


class Attempt(Base):
    """Historie aller Antworten – Grundlage für die Fortschritts-Timeline."""
    __tablename__ = "attempts"

    id = Column(String, primary_key=True, default=_uuid)
    profile_id = Column(String, ForeignKey("profiles.id"), nullable=False, index=True)
    lexeme_id = Column(String, ForeignKey("lexemes.id"), nullable=False)
    exercise_type = Column(String, nullable=False)
    level = Column(String, nullable=False)
    correct = Column(Boolean, nullable=False)
    given_answer = Column(String, nullable=True)
    expected_answer = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    profile = relationship("Profile", back_populates="attempts")
