# TeamMatch Architecture — Demo Day Candidate

## Production flow

```text
Competition sources
  -> competition-sync-v2 (scheduled worker)
  -> normalize / stable upsert
  -> Railway PostgreSQL

Browser
  -> Railway HTTPS
  -> Gunicorn / Flask / Jinja
  -> SQLAlchemy Core
  -> PostgreSQL
  -> Competition
  -> Join or Recruit
  -> optional same-university FILTER
  -> existing compatibility score
  -> human decision
```

## Matching boundary

The compatibility engine remains independent of university filtering.

```text
Skills
Availability
Preferred role
Working style
Project goal
   -> active human-approved weights
   -> Session 8 fixed mismatch safeguards
   -> clamp 0–100
```

The university filter runs before rendering the eligible team/applicant set. It does not pass university into `matching.compatibility()` and therefore cannot change a candidate's score.

Join identity:

```text
current user university
vs
team owner's user.university
```

Recruit identity:

```text
team owner university
vs
applicant user.university
```

Normalization trims whitespace, collapses repeated spaces and casefolds. There is no fuzzy matching or abbreviation inference.

## UI evidence hierarchy

Match cards display:

1. actual compatibility percentage;
2. five scan-friendly labels derived from the real `factors` dictionary;
3. existing evidence-based reasons from `matching.py`;
4. actual team action (Apply / Shortlist);
5. visually separate recommendation-learning feedback.

Critical mismatch reasons are shown in user-friendly text while the numerical penalty implementation remains internal.

## Learning loop

```text
Recommendation
 -> Accept/Reject recommendation feedback
 -> optional mapped reason/comment
 -> feedback record
 -> summary
 -> proposal after threshold
 -> admin review
 -> approved active weights
 -> future matching
```

Recommendation acceptance is preference feedback only and is not treated as successful teamwork.

## Security and production configuration

Preserved:

- production `SECRET_KEY` requirement
- secure/HttpOnly/SameSite session cookie settings
- CSRF validation on POST
- backend admin authorization for `/learning` and review actions
- `ENABLE_DEMO_FEEDBACK` production restriction
- PostgreSQL through `DATABASE_URL`
- Gunicorn
- DB-aware `/healthz`

## Competition sync

The web request path reads only stored competition data. Collection remains in `sync_competitions.py` and source adapters. Upsert preserves existing `competitions.id` values and therefore team/application relationships. Source failures do not clear stored competition data.
