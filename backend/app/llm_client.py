"""
Schlanker Client für OpenAI-kompatible Chat-Completions-Endpunkte.
Funktioniert sowohl gegen OpenWebUI (self-hosted) als auch OpenRouter (Cloud)
oder jeden anderen Anbieter mit /chat/completions-Schnittstelle – gesteuert
allein über LLM_BASE_URL/LLM_API_KEY/LLM_MODEL in der .env.
"""
import requests

from .config import settings


class LLMError(Exception):
    pass


def chat(messages: list[dict]) -> str:
    """messages: Liste von {"role": "system"|"user"|"assistant", "content": str}.
    Gibt den Antworttext zurück oder wirft LLMError mit einer für Endnutzer
    verständlichen Meldung (wird vom Router abgefangen, damit der Rest der
    App nie wegen eines nicht erreichbaren LLM-Backends abstürzt)."""
    if not settings.llm_enabled:
        raise LLMError("KI-Rückfragen sind nicht konfiguriert (LLM_BASE_URL fehlt in der .env).")

    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    body = {"model": settings.llm_model, "messages": messages, "stream": False}

    try:
        resp = requests.post(
            settings.llm_base_url, json=body, headers=headers, timeout=settings.llm_timeout_seconds
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        raise LLMError("Der KI-Helfer hat nicht rechtzeitig geantwortet (Timeout).")
    except requests.exceptions.ConnectionError:
        raise LLMError("Der KI-Helfer ist gerade nicht erreichbar (Verbindung fehlgeschlagen).")
    except requests.exceptions.HTTPError as ex:
        raise LLMError(f"Der KI-Helfer hat einen Fehler gemeldet ({ex.response.status_code}).")
    except (KeyError, IndexError, ValueError):
        raise LLMError("Die Antwort des KI-Helfers hatte ein unerwartetes Format.")
