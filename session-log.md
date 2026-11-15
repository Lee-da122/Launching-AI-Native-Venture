# Session Log

## Session 8 — Fix One Step and Test Again

Targeted weakest step: **Compatibility Scoring**.

Baseline supplied by course testing:
- Normal cases: 7/10
- Attack cases: 4/5
- Step 3 scoring errors: 3

Implemented:
- preserved active/human-approved matching weights
- added zero-required-skill-overlap penalty (-25)
- added clear non-flexible role mismatch penalty (-20)
- added opposite effort-goal penalty (-20)
- clamped final score to 0..100
- added explainable mismatch messages
- added fixed-rule competition-search scope guard

Re-test result:
- Normal cases: 10/10
- Attack cases: 5/5 at logic/source-test level
- Three identified Step 3 baseline errors: 0 remaining in the repeated fixtures

Session 7 regression:
- weight proposal still requires evidence
- proposal still does not auto-apply
- human approval still updates active weights
- future matching still reads active weights

Environment note:
- full Flask browser test not run in build environment because Flask package installation was unavailable

## Phase 2 — PostgreSQL / Railway readiness

Implemented only deployment-readiness work: SQLAlchemy Core/Engine DB layer, PostgreSQL `DATABASE_URL`, local SQLite fallback, explicit idempotent schema initialization, separate competition/demo seed commands, production `SECRET_KEY`, `ADMIN_EMAIL` backend authorization, production-disabled demo feedback by default, session-backed CSRF, secure production cookies, Gunicorn, Railway config, and `/healthz`.

No Phase 3 crawler, same-university filter, UI redesign, AI recommendation feature, messaging, or OAuth was added.

## Phase 3 — Korean competition pipeline (2026-11-15)
- Selected the official K-Startup Open API as the single primary source.
- Added competition source module and manual `sync_competitions.py`.
- Extended competition schema via idempotent ALTER migrations; existing IDs/FKs are preserved.
- Added source provenance, category/eligibility/participation, fetch timestamps, parsed dates and active status.
- Added conservative university-relevance filtering and plain-text sanitization.
- Added idempotent source_name + external_id upsert and safe failure behavior.
- Expanded Competition search with category/status/closing-soon filters while preserving Join/Recruit modes.
- Seed fixtures remain Demo/local fallback and are hidden in production discovery.
- Phase 3 controlled tests passed; Session 8 remains 10/10 normal + 5/5 attack.
- Live K-Startup/Railway sync remains blocked until a data.go.kr service key is configured.

## Phase 3 source revision — multi-source collector (2026-11-15)
- Added WEVITY university competition pages as a limited supplementary metadata source.
- Kept K-Startup as the official structured source and higher-priority provenance.
- Added source-failure isolation: one source may fail while another still synchronizes.
- Added conservative cross-source duplicate detection using normalized title + organizer + exact deadline.
- WEVITY detailed body text/poster images are not stored; only minimal discovery metadata is retained.
- WEVITY requests are sequential, low-frequency and capped at two list pages / forty details per run.
- Controlled WEVITY parser fixture, cross-source dedup, source-isolation and all-source-failure tests pass.
- Session 8 remains 10/10 normal + 5/5 attack; Phase 2 regression remains PASS.
- Live Railway/WEVITY parsing is not claimed until this revision is pushed and run in production.
