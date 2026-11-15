# TeamMatch MVP Scope — Phase 2

## Current production-ready scope

### Account / profile
- Sign up, login, logout
- University/name/email profile
- Hashed passwords
- Skills, availability, preferred role, working style, project goal
- Feedback-learning opt-out

### Competition / team formation
- Seedable local competition fixtures
- Search + Session 8 out-of-scope guard
- Join a Team
- Recruit a Team
- Recruiting posts and requirements
- Shortlist, apply, application status
- Recruiter applicant review and ownership checks

### Matching
- Explainable weighted compatibility
- Human-approved active weights
- Session 8 critical mismatch penalties
- Score clamp 0–100
- Human final decision

### Learning loop
- Recommendation Accept/Reject feedback
- Optional reason/comment
- Score/factor/weight snapshot
- Learning opt-out respected
- Aggregate feedback summary
- Threshold-based weight proposal
- Human approval/rejection
- Approved active weights used later
- Weight history
- No permanent teammate reputation

### Deployment / persistence
- SQLAlchemy Core/Engine database layer
- Local SQLite fallback
- PostgreSQL via `DATABASE_URL`
- Idempotent explicit schema initialization
- Separate demo seeding
- Gunicorn production start
- Railway config-as-code
- DB-aware `/healthz`
- Environment-based production secrets
- Backend founder/admin protection
- Session-backed CSRF protection

## Still out of scope

- Korean competition crawler
- Railway Cron
- Same-university matching/filter
- Competition-category filters
- External/global competition search
- New dashboard/match-card redesign
- AI/LLM matching or competition recommendations
- Chat / notifications / payments
- OAuth
- Skill-development recommendations
- Permanent good/bad teammate scoring

## Phase 2 definition of done

The code is ready to run with SQLite locally and PostgreSQL in production without changing product behavior. Public Railway deployment still requires account-specific Railway/GitHub connection and production environment variables, followed by real PostgreSQL and public-URL regression tests.
