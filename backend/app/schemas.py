from typing import Optional

from pydantic import BaseModel


class AnswerSubmit(BaseModel):
    lexeme_id: str
    exercise_type: str  # translation | conjugation | article | plural
    given_answer: str
    direction: Optional[str] = None  # it_to_de | de_to_it (nur translation)
    tense: Optional[str] = None      # nur conjugation
    person: Optional[str] = None     # nur conjugation
    plural: Optional[bool] = None    # nur article


class ProfileCreate(BaseModel):
    display_name: str
    target_level: str = "A1"
