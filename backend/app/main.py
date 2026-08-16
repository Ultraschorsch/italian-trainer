from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import get_db, Base, engine
from .auth import get_current_profile, resolve_external_id
from .routers import profiles, review, stats, vocab_import, ask, drill
from .config import settings
from . import seed

app = FastAPI(title="Italienisch-Trainer")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(profiles.router)
app.include_router(review.router)
app.include_router(stats.router)
app.include_router(vocab_import.router)
app.include_router(ask.router)
app.include_router(drill.router)

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed.run()


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    profile = get_current_profile(request, db)
    has_sso = bool(request.headers.get("Remote-User")) or resolve_external_id(request) and resolve_external_id(request).startswith("sso:")

    if not profile:
        return templates.TemplateResponse(
            "profile_select.html",
            {"request": request, "levels": LEVELS, "has_sso": has_sso},
        )

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "profile": profile, "levels": LEVELS, "llm_enabled": settings.llm_enabled},
    )


@app.get("/review", response_class=HTMLResponse)
def review_page(request: Request, db: Session = Depends(get_db)):
    profile = get_current_profile(request, db)
    if not profile:
        return templates.TemplateResponse("profile_select.html", {"request": request, "levels": LEVELS, "has_sso": False})
    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "profile": profile,
            "llm_enabled": settings.llm_enabled,
            "auto_explain": settings.auto_explain_on_wrong,
        },
    )


@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request, db: Session = Depends(get_db)):
    profile = get_current_profile(request, db)
    if not profile:
        return templates.TemplateResponse("profile_select.html", {"request": request, "levels": LEVELS, "has_sso": False})
    return templates.TemplateResponse(
        "ask.html", {"request": request, "profile": profile, "llm_enabled": settings.llm_enabled}
    )


@app.get("/drill", response_class=HTMLResponse)
def drill_page(request: Request, db: Session = Depends(get_db)):
    profile = get_current_profile(request, db)
    if not profile:
        return templates.TemplateResponse("profile_select.html", {"request": request, "levels": LEVELS, "has_sso": False})
    return templates.TemplateResponse("drill.html", {"request": request, "profile": profile})


@app.get("/timeline", response_class=HTMLResponse)
def timeline_page(request: Request, db: Session = Depends(get_db)):
    profile = get_current_profile(request, db)
    if not profile:
        return templates.TemplateResponse("profile_select.html", {"request": request, "levels": LEVELS, "has_sso": False})
    return templates.TemplateResponse("timeline.html", {"request": request, "profile": profile, "levels": LEVELS})
