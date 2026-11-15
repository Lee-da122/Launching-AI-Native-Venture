# TeamMatch Architecture Document — Phase 2

## Production target

```text
Browser
  -> Flask / Gunicorn on Railway
  -> Jinja templates + static CSS
  -> SQLAlchemy Core/Engine database layer
  -> Railway PostgreSQL
```

Local development uses the same application/business logic but falls back to SQLite when `DATABASE_URL` is absent.

## Database layer

`db.py` owns engine creation, Core metadata/schema, mapping-style result access, and idempotent schema bootstrap.

Environment behavior:

- `DATABASE_URL` set -> PostgreSQL (or the explicitly supplied SQLAlchemy URL)
- absent -> `sqlite:///.../teammatch.db`

Business code uses named SQL parameters and mapping-style rows (`row["column"]`). Direct `sqlite3` use, qmark placeholders, `lastrowid`, and SQLite schema inspection were removed from application/matching/learning logic.

### Tables

1. `users`
2. `competitions`
3. `teams`
4. `applications`
5. `shortlists`
6. `matching_settings`
7. `recommendation_feedback`
8. `weight_proposals`
9. `weight_history`

Important constraints are preserved: unique user email, unique application per team/user, unique shortlist per user/team, FKs, proposal status checks, feedback decision checks, and `matching_settings` singleton id=1.

## Schema bootstrap / data seeding

`init_db.py` calls idempotent `metadata.create_all()` plus the small historical `feedback_opt_in` compatibility migration and singleton initialization. It never drops tables.

Data seeding is separate:

- `seed_competitions.py` — four placeholder competition fixtures
- `seed_demo.py` — known-password demo users/teams, explicitly invoked only

Railway runs `python init_db.py` as a pre-deploy command. Demo users are not created automatically in production.

## Authentication / sessions

Werkzeug password hashing is preserved. Flask session still stores the authenticated `user_id`.

Production requires `SECRET_KEY`; no weak production fallback is allowed. HTTPS production cookies are Secure + HttpOnly + SameSite=Lax.

## CSRF

All current POST forms include `_csrf_token`. A Flask `before_request` handler checks the submitted token against the session token with `hmac.compare_digest`. Invalid/missing tokens fail before route logic executes.

## Admin authorization

The founder/admin identity is configured with `ADMIN_EMAIL`.

Backend `@admin_required` protects:

- `/learning`
- proposal generation
- proposal approval/rejection
- labelled demo-feedback generation

Frontend hiding is only convenience; the backend returns 403 for non-admin authenticated users.

Production demo-feedback generation is disabled unless `ENABLE_DEMO_FEEDBACK=true` is explicitly configured.

## User flow

```text
Sign Up + Profile
-> Login
-> Join OR Recruit
-> Search / Select Competition
-> Compatibility Matching
-> Human Final Decision
```

The Join and Recruit flows are unchanged by the database migration.

## Matching system

Default weights:

- Skills 0.35
- Availability 0.20
- Preferred role 0.20
- Working style 0.10
- Project goal 0.15

`matching.py` reads the current active row from `matching_settings`. Human-approved weights therefore continue to override defaults.

Session 8 penalties remain post-processing rules on top of the active-weight score:

- required-skill overlap = zero: -25
- non-flexible role mismatch: -20
- opposite effort goals: -20
- final clamp: 0–100

Explanations remain based on actual matching factors and penalties.

## Learning loop

```text
Recommendation
-> Accept / Reject feedback
-> Optional reason/comment
-> Snapshot stored
-> Aggregate summary
-> Proposed weight change after threshold
-> Admin human review
-> Approve / Reject
-> Active weights changed only on approval
-> Future recommendations read active weights
```

Threshold remains 5 learning-eligible rejection records mapped to the same factor. The selected factor gains 5 percentage points while other weights are proportionally reduced and normalized to 1.0.

Users who opt out still use TeamMatch normally, but their feedback is excluded from learning statistics/proposals.

## Safety / Red Line

Feedback changes compatibility rules only. There is no permanent student reputation, quality score, rejection penalty, visibility penalty, blacklist, or demographic inference.

Recommendation feedback and recruiter applicant decisions remain separate routes/tables.

## Railway

`railway.toml` uses:

- pre-deploy: `python init_db.py`
- start: `gunicorn app:app --bind 0.0.0.0:$PORT`
- health: `/healthz`

`/healthz` performs a database connectivity query but does not expose credentials or schema details.
