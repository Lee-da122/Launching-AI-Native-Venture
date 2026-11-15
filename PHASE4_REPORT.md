# TeamMatch Phase 4 Report — Pre-deployment Candidate

## A. Files changed

Modified:
- `app.py`
- `matching.py`
- `templates/base.html`
- `templates/dashboard.html`
- `templates/competitions.html`
- `templates/teams.html`
- `templates/applicants.html`
- `static/style.css`
- `README.md`
- `scope.md`
- `architecturedoc.md`
- `session-log.md`

Added:
- `university.py`
- `templates/profile.html`
- `phase4_tests.py`
- `PHASE4_TEST_RESULT.md`
- `DEMO_DAY.md`
- `PHASE4_REPORT.md`

Intentionally unchanged:
- `db.py`
- `learning.py`
- `guardrails.py`
- `sync_competitions.py`
- `competition_sources/*`
- Session 7/8 core scoring and learning behavior

## B. Same-university implementation

Join: after selecting a competition, `Same university only` filters recruiting teams by the team owner's `users.university` versus the logged-in user's university. It filters the candidate set before rendering and never changes `compatibility()`.

Recruit: applicant review uses the team owner's university versus each applicant's `users.university`. Compatibility sorting inside the remaining filtered set is preserved.

Both empty states provide `Show all universities`.

## C. University normalization

Exact rule:
1. trim leading/trailing whitespace;
2. collapse repeated whitespace to one space;
3. `casefold()` for case-insensitive English comparison.

No fuzzy matching and no abbreviation expansion. `KU` is not assumed to mean `Korea University`.

## D. UI changes

- Dashboard hero: `Find the right competition. Build the right team.`
- Primary Dashboard choices remain Join / Recruit.
- Navigation: Dashboard / Join / Recruit / Profile / optional admin Learning / Logout.
- Lightweight read-only profile view.
- Competition page has clearer Competition -> Team wording and truthful last-fetched timestamp.
- Join/Recruit same-university controls and recovery empty states.
- Match cards prioritize compatibility percentage and real five-factor breakdown.
- Apply/Shortlist is visually separated from recommendation-learning feedback.
- Applicant decision buttons explicitly say `Accept applicant` / `Reject applicant`.
- Responsive adjustments for filters, navigation, match cards and mobile widths.

## E. Match explanation changes

No matching reason is invented by an LLM. The existing `reasons` from `matching.py` are still rendered. The `Critical mismatch:` implementation prefix is removed in display only, with the reason emphasized. Factor labels are derived directly from the actual factor dictionary returned by `compatibility()`.

## F. Demo data

No weak known-password account is automatically seeded in production. `seed_demo.py` remains an explicitly invoked local/demo utility only.

Recommended production Demo Day strategy is documented in `DEMO_DAY.md`: one normal manually created demo user plus the founder/admin account, with clearly labelled test team owners and same-/different-university examples.

## G. Public URL

Existing production URL:

`https://teammatch-production.up.railway.app/`

At packaging time this URL is still running the prior `c7f975a` revision. This Phase 4 package must be pushed to GitHub before public-runtime verification can honestly be reported.

## H. Join flow test

Controlled/local logic and static wiring: PASS.

Public Phase 4 runtime: **not yet tested** because the Phase 4 revision is not yet in GitHub/Railway.

## I. Recruit flow test

Controlled/local logic and static wiring: PASS.

Public Phase 4 runtime: **not yet tested** for the same deployment reason.

## J. Same-university regression

PASS:
- same university survives Join filter;
- different university is removed;
- same university survives Recruit filter;
- different university is removed;
- whitespace/case normalization works;
- abbreviations are not inferred;
- score/factors stay exactly unchanged.

## K. Session 8 regression

Actual local result:
- Normal cases: **10/10 PASS**
- Attack cases: **5/5 PASS**

Existing penalties and score clamp were not changed.

## L. Learning-loop regression

Phase 2 regression passed:
- threshold proposal generated;
- proposal does not auto-apply;
- approval activates new normalized weights;
- rejection leaves weights unchanged;
- history is saved;
- active weights persist in the controlled restart test.

## M. Competition-sync regression

Phase 3 controlled regression: PASS.

Confirmed test behaviors include parser handling, same-source idempotency, update-in-place, cross-source conservative dedup, relationship preservation, one-source failure isolation, all-source failure preservation and deadline behavior.

Production Railway sync service was re-inspected before packaging and is configured as `python -u sync_competitions.py` with cron `0 0 * * *`.

## N. Persistence test

Controlled Phase 2 SQLite fallback restart test: PASS for users, teams, applications, feedback, history and active weights.

Production PostgreSQL already has a persistent Railway Postgres volume, but **Phase 4-specific post-deploy persistence has not yet been rerun** because this package is not deployed yet.

## O. Admin/security regression

Controlled/static Phase 2 regression: PASS for:
- backend admin guards;
- CSRF validation/forms;
- production SECRET_KEY requirement;
- DB-aware `/healthz`;
- no reputation/blacklist red-line fields.

Current Railway web configuration was re-inspected and still uses Gunicorn, `python init_db.py` pre-deploy, `/healthz`, PostgreSQL env reference, `ADMIN_EMAIL`, `SECRET_KEY` and `ENABLE_DEMO_FEEDBACK`.

## P. Demo Day scenario

Recommended click flow:
1. public URL;
2. login normal demo user;
3. Dashboard hero;
4. Join a Team;
5. select current Korean competition;
6. inspect compatibility score/factors/reasons;
7. toggle Same university only;
8. show score unchanged;
9. Shortlist / Apply to Team;
10. separate Accept/Reject recommendation feedback;
11. briefly show Recruit or Dashboard;
12. optional admin Learning review if time remains.

See `DEMO_DAY.md` for profile/scenario setup.

## Q. Known limitations

- self-reported university/profile data;
- no real university verification;
- matching quality depends on self-reported fields;
- recommendation feedback does not measure eventual team success;
- Korean competition coverage is limited/incomplete;
- no global competitions;
- no chat/realtime messaging/notifications;
- no post-project teamwork evaluation or permanent teammate reputation.

## R. Anything still incomplete

The code candidate and controlled regressions are complete locally. Remaining items require the Phase 4 commit to exist in GitHub/Railway:

1. public normal-user click regression;
2. public recruiter click regression;
3. public admin `/learning` allow/deny regression;
4. public same-university filter regression with real demo accounts;
5. Phase 4 post-redeploy PostgreSQL persistence confirmation;
6. final screenshots / 1366px + mobile visual check on the live revision.

Do not claim these as passed until the Phase 4 package is pushed and deployed.
