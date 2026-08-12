import os


class Settings:
    # Datenbank
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://italian:italian@db:5432/italian_trainer",
    )

    # Name des HTTP-Headers, den Pangolin Platform SSO (bzw. euer Forward-Auth)
    # mit dem angemeldeten Benutzernamen setzt. In den Pangolin-Docs/eurer
    # bestehenden Config nachsehen, welcher Header tatsächlich verwendet wird
    # (gängige Kandidaten: "Remote-User", "X-Forwarded-User", "X-Authentik-Username").
    sso_header_name: str = os.getenv("SSO_HEADER_NAME", "Remote-User")

    # Wenn kein SSO-Header vorhanden ist (z.B. lokale Entwicklung im Heimnetz
    # ohne Pangolin davor), erlaubt diese Einstellung den Fallback auf den
    # einfachen Profil-Picker per Cookie. In Produktion hinter Pangolin sollte
    # das nicht nötig sein, schadet aber auch nicht, da Pangolin ohnehin vorgeschaltet ist.
    allow_local_profile_picker: bool = os.getenv("ALLOW_LOCAL_PROFILE_PICKER", "true").lower() == "true"

    session_cookie_name: str = "italian_trainer_profile"

    # KI-Rückfragen (optional). LLM_BASE_URL erwartet die VOLLSTÄNDIGE
    # Chat-Completions-URL (OpenAI-kompatibles Format), z.B.:
    #   OpenWebUI:  http://openwebui:8080/api/chat/completions
    #   OpenRouter: https://openrouter.ai/api/v1/chat/completions
    # Ist LLM_BASE_URL leer, ist das Feature deaktiviert (Buttons erscheinen
    # nicht bzw. liefern eine verständliche Fehlermeldung).
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "llama3.1")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_base_url)


settings = Settings()
