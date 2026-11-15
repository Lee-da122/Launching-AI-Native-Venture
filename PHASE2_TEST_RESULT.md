# TeamMatch Phase 2 Test Result

## Executed successfully in this environment

### 1. Python syntax

`python -m py_compile *.py` passed for the Phase 2 source files.

### 2. Session 8 regression

`python session8_tests.py`:

- Normal cases: **10/10 PASS**
- Attack cases: **5/5 PASS**
- Session 7 active-weight + Session 8 penalty interaction: PASS

The same functional scenarios were preserved; only the test database plumbing was adapted from direct sqlite3/qmark SQL to the new SQLAlchemy database layer.

### 3. Phase 2 database / learning regression

`python phase2_tests.py` passed all checks, including:

- schema bootstrap can run twice without wiping data
- all 9 application tables exist
- baseline weights total 100%
- matching behavior preserved
- feedback opt-out excluded from learning statistics
- 5 Availability rejections create a proposal
- proposal does not automatically change active weights
- proposed weights normalize to exactly 1.0
- approval activates the new weights
- weight history is stored
- rejected proposal leaves active weights unchanged
- SQLAlchemy engine restart preserves users, team, application, feedback, history and active weights in the local SQLite fallback
- every SQLAlchemy Core table compiles with the PostgreSQL dialect
- app/matching/learning business SQL uses named parameters rather than qmark placeholders
- production source fails closed when SECRET_KEY is missing
- learning controls have backend admin decorators
- CSRF backend validation exists
- every POST form contains a CSRF token
- DB-aware `/healthz` route exists
- Session 8 out-of-scope guard still blocks the historical attack request
- normal competition-style search remains allowed
- no permanent teammate reputation/quality/blacklist score was introduced

## PostgreSQL test status

A real PostgreSQL server was **not available in this execution environment**. The schema was compiled against SQLAlchemy's PostgreSQL dialect, but CRUD behavior against a live PostgreSQL instance has not yet been executed here.

That real test must be performed after Railway PostgreSQL is provisioned (or against another reachable PostgreSQL instance).

## Flask / HTTP route test status

The build environment does not currently contain Flask/Werkzeug/Gunicorn/psycopg, and outbound package installation was blocked by network/DNS restrictions. Therefore I could not run the Flask test client or Gunicorn here.

Consequently, these are implemented but still require runtime confirmation after dependencies are installed:

- non-admin receives HTTP 403 for `/learning` and all admin POST routes
- admin receives access
- CSRF rejection/acceptance through real HTTP requests
- `/healthz` through the running Flask/Gunicorn server
- production secure-cookie behavior over HTTPS

## Railway persistence status

Actual Railway redeploy persistence was **not tested** because no authenticated Railway project/database was available to this environment.

The local equivalent restart test passed: after disposing/recreating the SQLAlchemy engine and rerunning idempotent schema initialization, users, teams, applications, feedback, weight history, and active weights remained intact.

The production persistence test still required on Railway is:

1. create user
2. create team
3. create application
4. create recommendation feedback
5. note active weights
6. redeploy/restart
7. verify all records and active weights remain
