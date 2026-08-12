import uuid

from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Profile


def resolve_external_id(request: Request) -> str | None:
    """Liest die Identität aus dem SSO-Header (von Pangolin Platform SSO
    gesetzt) oder – falls nicht vorhanden und erlaubt – aus dem lokalen
    Profil-Cookie."""
    header_value = request.headers.get(settings.sso_header_name)
    if header_value:
        return f"sso:{header_value}"

    if settings.allow_local_profile_picker:
        cookie_value = request.cookies.get(settings.session_cookie_name)
        if cookie_value:
            return f"local:{cookie_value}"

    return None


def get_current_profile(request: Request, db: Session = Depends(get_db)) -> Profile | None:
    external_id = resolve_external_id(request)
    if not external_id:
        return None
    return db.query(Profile).filter(Profile.external_id == external_id).first()


def require_profile(request: Request, db: Session = Depends(get_db)) -> Profile:
    profile = get_current_profile(request, db)
    if not profile:
        raise HTTPException(status_code=401, detail="Kein Profil gefunden. Bitte zuerst anlegen.")
    return profile


def new_local_id() -> str:
    return uuid.uuid4().hex[:12]
