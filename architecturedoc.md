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

## AI Weight Judge architecture

The learning layer is now:

`Recommendation Feedback`
`→ Aggregated Evidence`
`→ AI Weight Judge (structured output)`
`→ Deterministic Validator`
`→ Pending Proposal`
`→ Human Approve / Reject`
`→ matching_settings / weight_history`

The matching engine remains independent of the AI provider and continues to use the active five-factor weights plus Session 8 mismatch safeguards.

### Privacy
The AI input contains current global weights, eligible feedback totals, accept/reject totals, rejection-reason counts, excluded-feedback count, and a compact proposal-history summary. No names, emails, university email, applicant identities, passwords, or person-level quality scores are sent.

### Safety validation
All five factor keys are required. Weights must be finite numeric values, sum to 1.0 within minor rounding tolerance, remain between 0.05 and 0.50, and move no more than 0.05 from the current active value. Fundamentally invalid output is rejected rather than clamped.

### Failure isolation
OpenAI/API timeout, unavailable configuration, invalid JSON/schema, invalid business-rule weights, rate limits, and provider errors do not affect normal TeamMatch matching or saved recommendation feedback. Failed AI runs cannot activate weights and remain retryable.
