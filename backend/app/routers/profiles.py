from fastapi import APIRouter, Request, Depends, Response, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..auth import resolve_external_id, get_current_profile, new_local_id
from ..models import Profile

router = APIRouter()

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


@router.post("/profiles/create")
def create_profile(
    response: Response,
    request: Request,
    display_name: str = Form(...),
    target_level: str = Form("A1"),
    db: Session = Depends(get_db),
):
    external_id = resolve_external_id(request)
    set_cookie = False

    if not external_id:
        # Kein SSO-Header vorhanden -> lokales Profil per Cookie anlegen
        local_id = new_local_id()
        external_id = f"local:{local_id}"
        set_cookie = True

    existing = db.query(Profile).filter(Profile.external_id == external_id).first()
    if existing:
        profile = existing
    else:
        profile = Profile(external_id=external_id, display_name=display_name, target_level=target_level)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    redirect = RedirectResponse(url="/", status_code=303)
    if set_cookie:
        redirect.set_cookie(
            key=settings.session_cookie_name,
            value=external_id.split("local:")[1],
            max_age=60 * 60 * 24 * 365 * 5,
            httponly=True,
            samesite="lax",
        )
    return redirect


@router.post("/profiles/switch-local")
def switch_local_profile(response: Response, local_id: str = Form(...), db: Session = Depends(get_db)):
    """Zum schnellen Wechseln zwischen lokalen Profilen (nur wenn kein SSO-Header aktiv ist)."""
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.set_cookie(
        key=settings.session_cookie_name,
        value=local_id,
        max_age=60 * 60 * 24 * 365 * 5,
        httponly=True,
        samesite="lax",
    )
    return redirect


@router.post("/profiles/update-level")
def update_level(request: Request, target_level: str = Form(...), db: Session = Depends(get_db)):
    profile = get_current_profile(request, db)
    if profile and target_level in LEVELS:
        profile.target_level = target_level
        db.commit()
    return RedirectResponse(url="/", status_code=303)
