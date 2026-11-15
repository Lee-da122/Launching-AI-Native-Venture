# TeamMatch MVP Scope — Phase 3

## Current scope

### Account / profile
- Sign up, login, logout
- University/name/email profile
- Hashed passwords
- Skills, availability, preferred role, working style, project goal
- Feedback-learning opt-out

### Competition discovery / team formation
- South Korean competition-data collector using K-Startup Open API + limited WEVITY public-page metadata
- PostgreSQL-backed competition search; no external source request during normal page rendering
- Source provenance and original listing URL
- Active/expired status and request-time D-day calculation
- Category, status and closing-soon filters
- Stable competition IDs through upsert rather than delete/reinsert
- Conservative cross-source deduplication
- Seed fixtures retained only for local/offline fallback
- Join a Team / Recruit a Team modes preserved
- Shortlist, apply, application status and recruiter applicant review preserved

### Matching / learning / safety
- Explainable weighted compatibility
- Human-approved active weights
- Session 8 critical mismatch penalties and score clamp
- Session 8 scope guard
- Session 7 feedback learning loop and opt-out
- Admin-only learning controls
- No permanent teammate reputation or rejection penalty

### Deployment / persistence
- Flask + Jinja + SQLAlchemy
- Railway PostgreSQL via `DATABASE_URL`
- Gunicorn + `/healthz`
- Environment-based secret/admin settings
- CSRF + secure production sessions
- Phase 3 manual sync command: `python sync_competitions.py`

## Production activation still requires

- Push this Phase 3 revision to GitHub
- Redeploy the Railway web service so the schema/code update is live
- Run one successful manual sync against Railway PostgreSQL
- Verify the WEVITY parser against the live pages from Railway
- Configure a separate once-daily Railway cron service after manual sync succeeds
- Optional: add `K_STARTUP_SERVICE_KEY` to broaden coverage with the official K-Startup source

Until those are completed, the multi-source implementation is tested with controlled fixtures but live production competition ingestion is not yet verified.

## Out of scope

- Global competition collection
- Same-university matching/filter
- AI/LLM competition recommendations
- New dashboard/match-card redesign
- Chat / notifications / payments
- OAuth
- Permanent good/bad teammate scoring
- Phase 4 work
