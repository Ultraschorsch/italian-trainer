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


settings = Settings()
