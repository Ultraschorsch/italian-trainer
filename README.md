# Passaporto Italiano – selbstgehosteter Italienisch-Trainer

Vokabel- und Grammatiktrainer (Konjugation, Artikel/Genus, Plural) mit CEFR-Niveaus
(A1–C2), eigenen Profilen für dich und deine Frau, Spaced-Repetition (SM-2, wie
bei Anki) und einer Fortschritts-Timeline.

## Architektur (kurz)

- **Backend**: FastAPI (Python), Server-rendert die Seiten (Jinja2), Übungs-
  Interaktion läuft über eine kleine JSON-API (`/review/next`, `/review/answer`).
- **DB**: PostgreSQL. Tabellen: `profiles`, `lexemes` (Vokabular), `srs_states`
  (SM-2-Zustand pro Profil/Vokabel/Übungsart), `attempts` (Verlauf → Timeline).
- **Grammatik-Engine**: komplett regelbasiert, keine externe KI/API nötig:
  - `conjugation.py`: Präsens/Imperfekt/Futur/Perfekt für regelmäßige Verben
    (-are/-ere/-ire, inkl. isc-Verben), plus hinterlegte Ausnahmen für die
    gängigsten unregelmäßigen Verben (andare, potere, volere, dovere, …).
  - `grammar_rules.py`: bestimmter Artikel (il/lo/l'/i/gli/la/le) nach
    Anfangslaut-Regeln, Pluralbildung (-o→-i, -a→-e, -e→-i) mit Ausnahmen
    über das Feld `plural` im Vokabeleintrag.
  - Bei jeder falschen Antwort wird eine kurze Erklärung generiert (z.B.
    warum "lo" statt "il", oder welche Endung bei welcher Person gilt).
- **Vokabular**: Ein kuratierter Startbestand für A1/A2 (ca. 150 Wörter,
  selbst zusammengestellt) liegt in `backend/app/seed_data/*.json` und wird
  beim ersten Start automatisch geladen. **Wichtig**: Es gibt keine sauber
  lizenzierte, fertige Italienisch-CEFR-Wortliste zum Download – der
  Startbestand ist bewusst überschaubar. Über die CSV-Import-Funktion im
  Dashboard könnt ihr jederzeit weitere Vokabeln (z.B. aus dem Kursmaterial
  deiner Frau) nachladen.

## Anmeldung / Zugriff von außen

Die App hat **kein eigenes Login**. Stattdessen:

1. Lokal/im LAN (bevor Pangolin davor hängt): Fällt automatisch auf einen
   einfachen Cookie-Profil-Picker zurück (`ALLOW_LOCAL_PROFILE_PICKER=true`).
2. Produktiv: Legt in Pangolin eine Resource für diese App an, aktiviert
   **Platform SSO** (Rolle "Member" nicht vergessen zuzuweisen – sonst hat
   niemand Zugriff, siehe eure eigene Notiz dazu), fertig. Die App liest die
   Identität aus dem Header, den euer Forward-Auth setzt (`SSO_HEADER_NAME`
   in der `.env`, Default `Remote-User`).

   **Bitte einmal verifizieren**, welchen Header-Namen Pangolin bei euch
   tatsächlich setzt (in der Pangolin-Doku oder per Testaufruf mit
   `curl -v` gegen die geschützte Resource nachsehen) – ich bin von einem
   gängigen Forward-Auth-Standard ausgegangen, das kann je nach Pangolin-
   Version variieren.

Sobald sich jemand zum ersten Mal über SSO anmeldet, legt die App
automatisch ein neues Profil an (Namensabfrage beim ersten Besuch).

## Setup

```bash
cp .env.example .env
# .env anpassen (Postgres-Passwort, ggf. SSO_HEADER_NAME)

docker compose up -d --build
```

App läuft dann auf Port 8000 im Container – über Traefik/Pangolin wie eure
anderen Services einbinden (Label in `docker-compose.yml` ist als Vorlage
schon drin, Domain anpassen). Für Dockhand: Compose-Datei wie gewohnt per
`PUT /api/stacks/{name}/compose` einspielen.

## Vokabular erweitern

Dashboard → "Eigene Vokabeln importieren" → CSV mit Kopfzeile:

```
italian,german,pos,level,gender,plural,conjugation_class,example_it,example_de
```

Pflichtfelder: `italian, german, pos, level`. `pos` ∈ {noun, verb, adjective,
adverb, other}. `gender` (m/f) nur bei Nomen relevant. `conjugation_class`
(are/ere/ire/ire_isc/irregular) nur bei Verben – bei unregelmäßigen Verben
lohnt sich ein Blick in `seed_data/vocab_a2.json`, wie `irregular_forms` als
JSON-Override aussieht (das Feld ist aktuell nur per direktem DB-Zugriff /
Erweiterung des Import-Scripts setzbar, nicht über die CSV – bei Bedarf baue
ich das gerne nach).

## Bekannte Vereinfachungen (bewusste Entscheidungen für die erste Version)

- **Übersetzungs-Check**: exakter Textvergleich (klein geschrieben, ohne
  Satzzeichen). Synonyme/alternative Übersetzungen werden aktuell nicht
  erkannt – bei Bedarf leicht erweiterbar (z.B. Liste akzeptierter Antworten
  pro Vokabel).
- **noi/voi/loro bei Perfekt mit essere**: mangels bekanntem Geschlecht der
  Gruppe wird vereinfachend die maskuline Pluralform angenommen.
- **SM-2**: Standardalgorithmus, "schwer aber richtig" wird aktuell nicht
  separat abgefragt (nur richtig/falsch fließt ein) – ließe sich ergänzen.

## Nächste sinnvolle Ausbaustufen

- Audio/Aussprache
- Akzeptierte Synonyme pro Vokabel
- B2–C2 Wortschatz (aktuell nur ein kleiner B1-Grundstock als Beispiel)
