# TeamMatch MVP — PostgreSQL / Railway-ready Phase 2

TeamMatch is a Flask + Jinja MVP for university teammate matching. Phase 2 keeps the existing product flow and matching/learning behavior while replacing direct SQLite assumptions with a small SQLAlchemy Core/Engine database layer.

## Architecture

```text
Browser
  -> Flask + Jinja
  -> SQLAlchemy Core/Engine database layer
  -> SQLite locally (default) OR PostgreSQL when DATABASE_URL is set
```

Existing product behavior remains: sign up/login, profile, Join/Recruit, competition search, team matching/explanations, shortlist/apply, applicant decisions, Session 7 feedback learning, Session 8 mismatch penalties and search guardrail.

## Local development (Windows / VS Code)

Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

Initialize the local SQLite schema:

```powershell
py init_db.py
```

Seed only the four local competition fixtures:

```powershell
py seed_competitions.py
```

Optional: add labelled demo users/teams with known demo passwords:

```powershell
py seed_demo.py
```

If you want local founder/admin access, set the admin email before starting:

```powershell
$env:ADMIN_EMAIL="demo.recruiter@university.edu"
```

Run locally:

```powershell
py app.py
```

Open `http://127.0.0.1:5000`.

If `DATABASE_URL` is absent, TeamMatch uses `teammatch.db` through SQLAlchemy's SQLite driver. The local development server initializes missing schema safely, but it no longer auto-creates demo accounts.

## PostgreSQL

Set `DATABASE_URL` to a PostgreSQL connection string. Railway's ordinary `postgresql://...` URL is normalized internally to SQLAlchemy's psycopg driver.

Example shell setup (do not commit real credentials):

```powershell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DB"
$env:SECRET_KEY="replace-with-a-long-random-value"
$env:ADMIN_EMAIL="founder@example.edu"
$env:APP_ENV="production"
py init_db.py
```

`init_db.py` is idempotent: it creates missing tables and the matching-settings singleton, and does not drop or reset existing data.

## Demo data separation

Schema setup and demo data are separate:

- `python init_db.py` — schema only
- `python seed_competitions.py` — competition fixtures only
- `python seed_demo.py` — optional known-password demo accounts and teams

Production does **not** auto-create demo users. The login page hides demo credentials in production.

## Admin / founder controls

Learning-loop administration is protected on the backend by `ADMIN_EMAIL`.

Only the logged-in user whose email exactly matches `ADMIN_EMAIL` may access:

- `GET /learning`
- `POST /learning/generate-proposal`
- `POST /learning/proposal/<id>/approve`
- `POST /learning/proposal/<id>/reject`
- `POST /learning/demo-feedback`

Other logged-in users receive HTTP 403.

`ENABLE_DEMO_FEEDBACK=true` must also be set to enable bulk demo-feedback creation in production. It is disabled by default in production.

## CSRF and sessions

All current POST forms include a session-backed CSRF token and `app.py` validates it before processing POST requests.

Production sessions use:

- Secure cookie: enabled
- HttpOnly: enabled
- SameSite=Lax

`SECRET_KEY` is required in production. Local development has a clearly marked development fallback only.

## Health check

`GET /healthz` verifies application/database connectivity and returns:

```json
{"status":"ok"}
```

with HTTP 200 only when the database query succeeds.

## Railway deployment

The repository includes `railway.toml`:

```toml
[deploy]
preDeployCommand = ["python init_db.py"]
startCommand = "gunicorn app:app --bind 0.0.0.0:$PORT"
healthcheckPath = "/healthz"
```

Required Railway app variables:

```text
APP_ENV=production
SECRET_KEY=<long random secret>
DATABASE_URL=${{Postgres.DATABASE_URL}}
ADMIN_EMAIL=<founder/admin login email>
ENABLE_DEMO_FEEDBACK=false
```

Recommended first deployment flow:

1. Create Railway project and app service from the GitHub repo.
2. Add a PostgreSQL service.
3. In the app service, set `DATABASE_URL=${{Postgres.DATABASE_URL}}`.
4. Set `APP_ENV=production`, `SECRET_KEY`, `ADMIN_EMAIL`, and keep `ENABLE_DEMO_FEEDBACK=false`.
5. Deploy. `python init_db.py` runs as the pre-deploy schema step.
6. If you want the four placeholder competitions for Demo Day, run `python seed_competitions.py` once against the production database.
7. Confirm `/healthz` is HTTP 200, then run the regression checklist.

Do not use local `teammatch.db` as Railway production persistence.

## Tests

Session 8 benchmark:

```powershell
py session8_tests.py
```

Phase 2 DB/learning/config checks:

```powershell
py phase2_tests.py
```

The repository's latest test evidence is documented in `PHASE2_TEST_RESULT.md`.

## Matching behavior preserved

Baseline weights remain:

- Skills 35%
- Availability 20%
- Preferred role 20%
- Working style 10%
- Project goal 15%

Approved active weights in `matching_settings` override these defaults.

Session 8 post-score penalties remain:

- no required-skill overlap: -25
- non-flexible preferred-role mismatch: -20
- opposite project-effort goals: -20
- final score clamped to 0–100

No permanent person-level reputation or good/bad teammate score is implemented.

## Phase 3 — Korean competition data

TeamMatch Phase 3 uses two complementary South Korean sources:

- **K-Startup Open API** (official public-data API) for structured startup/idea/competition announcements.
- **WEVITY university competition pages** as a lightweight supplementary index for broader university-relevant contests such as AI/data, engineering, design, marketing and case-style competitions.

K-Startup is accessed through its documented API. WEVITY is treated more conservatively: TeamMatch only reads a small number of publicly accessible university-contest pages, stores minimal metadata, uses low-frequency sequential requests, and links users back to the original WEVITY listing. No CAPTCHA, login, anti-bot mechanism, rate limit or access control is bypassed. During source review, no explicit automated-access permission was found for WEVITY, so this integration should be described as a limited public-page metadata collector rather than as an officially licensed feed.

TeamMatch stores source provenance and does not claim to cover every Korean competition.

### What is collected

The collector keeps competition-style opportunities realistically relevant to university users. It excludes obvious recruiting-only items such as ordinary supporter, mentoring, academy, volunteer, hiring and event listings unless the title clearly represents a contest/competition.

Stored fields include title, organizer, deadline, category, eligibility, participation type when explicitly inferable, original source listing URL, source-specific external ID, fetch timestamp and active/expired status. WEVITY detail text and poster images are not copied into TeamMatch; the fallback description is `See original competition page for details.` Missing factual fields remain missing and no LLM is used to invent them.

Collection volume is deliberately capped for Demo Day reliability: K-Startup uses a small current-page limit and WEVITY uses at most two list pages / forty sequential detail requests per run.

### Manual sync

The manual command is always:

```powershell
py sync_competitions.py
```

If a data.go.kr K-Startup service key is available, set it before running:

```powershell
$env:K_STARTUP_SERVICE_KEY="<your service key>"
py sync_competitions.py
```

Without a K-Startup key, that source fails safely and the WEVITY source can still synchronize. If one source fails, the other source continues. Only when every configured source fails does the command exit non-zero, and existing database rows are preserved.

The primary source identity is `source_name + external_id`. A conservative cross-source duplicate check additionally compares normalized title + organizer + exact deadline. It does not use aggressive fuzzy matching. Existing TeamMatch competition IDs are updated in place rather than deleted/reinserted, so team/application history remains valid.

When the same item appears in both sources, K-Startup provenance has priority because it is the official structured source; the TeamMatch row ID remains unchanged.

### Scheduled sync on Railway

After a successful manual production sync, create a separate Railway service from the same repository with:

```text
Start command: python sync_competitions.py
Cron: once daily
DATABASE_URL=${{Postgres.DATABASE_URL}}
K_STARTUP_SERVICE_KEY=<optional Railway secret>
```

Daily refresh is enough for the MVP. The normal Flask web service never contacts either external source during user page requests; it only reads PostgreSQL.

`seed_competitions.py` remains a local/offline development fallback. Seed rows are marked `source_name=Demo` and are hidden from production competition discovery.
