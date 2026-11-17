# TeamMatch — Demo Day Candidate

TeamMatch helps university students discover competitions and find compatible teammates based on skills, availability, preferred roles, working style, and project goals. Human users always make the final team decision.

## Current product

- Flask + Jinja web application
- SQLAlchemy Core database layer
- PostgreSQL on Railway in production; SQLite fallback for local development
- Sign up / login with hashed passwords
- Profile fields: university, skills, availability, preferred role, working style, project goal
- Korean competition discovery from TeamMatch's own database
- Join a Team / Recruit a Team flows
- Explainable five-factor compatibility matching
- Same-university **filter** on Join and Recruit; university is not a scoring factor
- Shortlist, applications, recruiter accept/reject decisions
- Recommendation feedback and Session 7 human-approved learning loop
- Session 8 critical mismatch safeguards and scope guard
- CSRF, admin authorization, secure production sessions, `/healthz`
- Separate competition-sync worker with source provenance and stable competition IDs

## Matching

Compatibility continues to use the active human-approved weights for exactly five factors:

- Skills
- Availability
- Preferred role
- Working style
- Project goal

University is only an optional result filter. It never adds points, removes points, or becomes a sixth factor. Session 8 mismatch penalties remain fixed post-processing safeguards and final scores remain clamped to 0–100.

## Same-university filter

Comparison normalization is deliberately conservative:

- trim leading/trailing whitespace;
- collapse repeated whitespace;
- case-insensitive comparison through `casefold()`.

No fuzzy matching or abbreviation guessing is performed. For example, `Korea University` and `korea university` match, but `KU` is not automatically treated as `Korea University`.

## Competition sync

Normal page requests read only PostgreSQL. They never crawl an external site.

`sync_competitions.py` performs source collection, normalization and stable upsert. Existing competition IDs are updated in place so team/application relationships are not broken. WEVITY collection is intentionally limited to minimal public metadata; K-Startup can be enabled with its service key.

Manual sync:

```powershell
py sync_competitions.py
```

Production currently has a separate Railway sync service configured with a daily cron. The Competition page shows the real last fetched timestamp rather than claiming freshness that was not observed.

## Local development

```powershell
py -m pip install -r requirements.txt
py init_db.py
py seed_competitions.py
py app.py
```

`seed_demo.py` is for explicitly invoked local/demo setup only. It is not called automatically in production.

## Railway production

Public URL:

`https://teammatch-production.up.railway.app/`

Expected web service configuration:

- start: `gunicorn app:app --bind 0.0.0.0:$PORT`
- pre-deploy: `python init_db.py`
- health check: `/healthz`
- PostgreSQL through `DATABASE_URL`
- production `SECRET_KEY`
- `ADMIN_EMAIL` for the founder/admin learning page
- production demo-feedback disabled unless explicitly enabled

## Tests

Run:

```powershell
py phase4_tests.py
py session8_tests.py
py phase2_tests.py
py phase3_tests.py
```

See `PHASE4_TEST_RESULT.md` for the latest controlled regression result.

## Known limitations

- University information is self-reported; real university email verification is not implemented.
- Matching depends on self-reported profile information.
- Recommendation acceptance means the recommendation looked useful; it is not proof of successful teamwork.
- Competition coverage is limited to the current Korean collection sources and is not complete.
- Global competitions are not supported.
- No chat, real-time messaging or notifications.
- No post-project teamwork evaluation or permanent teammate reputation.

## AI Weight Judge

TeamMatch keeps teammate compatibility scoring deterministic and rule-based. AI is used only in the learning layer that reviews aggregated recommendation feedback and may propose a new set of global matching weights.

Learning flow:

`Recommendation Feedback → Aggregated Evidence → AI Weight Judge → Deterministic Validation → Human Approval → Active Matching Weights → Rule-based Compatibility Matching`

The AI receives only aggregate counts and current global weights. It does not receive student names, email addresses, applicant identities, passwords, or person-level reputation history. A valid AI proposal remains `Pending` until an admin explicitly approves it. The validator requires all five factors, a total of 100%, 5%–50% per factor, and no single-factor change greater than 5 percentage points.

Configuration:

- `OPENAI_API_KEY` — secret, set only in the deployment environment.
- `AI_WEIGHT_JUDGE_MODEL` — model configured for the AI Weight Judge.

If either is missing or the provider is unavailable, normal competition discovery, Join/Recruit, matching, and recommendation feedback continue to work. AI proposal generation fails safely and never falls back to a fake deterministic AI proposal.
