# Phase 4 Test Result

## Local regression run

- Phase 4 focused tests: **22/22 PASS**
- Session 8 normal cases: **10/10 PASS**
- Session 8 attack cases: **5/5 PASS**
- Phase 2 regression: **PASS**
- Phase 3 controlled parser/dedup/failure regression: **PASS**

### Same-university regression

- `Korea University` matches `korea university`.
- Leading/trailing whitespace and repeated spaces are normalized.
- `KU` does **not** automatically match `Korea University`.
- Join filter keeps the same-university team and removes the different-university team.
- Recruit filter keeps the same-university applicant and removes the different-university applicant.
- Compatibility score and factor values are identical before/after filtering.
- The five existing matching weights remain unchanged.

### UI/static wiring regression

- Join and Recruit same-university controls are wired.
- Empty states include `Show all universities`.
- Apply/Shortlist actions are visually separated from recommendation feedback.
- Recruit decisions use `Accept applicant` / `Reject applicant`.
- CSRF hidden fields remain present on POST forms.
- Admin Learning navigation remains conditional.
- Profile route exists.

## Runtime limitation of this build environment

This container has SQLAlchemy/BeautifulSoup but does not have Flask/Werkzeug installed, and outbound package installation is not assumed. Therefore the final public-URL form-click regression must be repeated after this Phase 4 revision is pushed and deployed to Railway. The existing production Railway deployment was re-inspected separately before packaging.
