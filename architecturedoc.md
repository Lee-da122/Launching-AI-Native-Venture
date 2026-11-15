# TeamMatch Architecture Document — Phase 3

## Production architecture

```text
K-Startup Open API ---------\
                              -> sync_competitions.py (manual / daily Railway job)
WEVITY university listings --/       -> normalize + filter
                                      -> source upsert + conservative cross-source dedup
                                      -> Railway PostgreSQL

Browser
  -> Flask / Gunicorn on Railway
  -> Competition search/filter (PostgreSQL only)
  -> Select competition
  -> Join / Recruit
  -> Existing matching + human decision
```

The normal web request path never contacts K-Startup or WEVITY. External-source outages therefore do not take down the Competition page; users see the last known PostgreSQL data.

## Competition sources / provenance

### K-Startup
Official Open API `getAnnouncementInformation01`, provided through data.go.kr. It is the preferred provenance when an identical competition is found in both sources. It requires `K_STARTUP_SERVICE_KEY` for live calls.

### WEVITY
The supplementary source is the publicly accessible WEVITY university competition listing/detail pages. The collector stores only minimal metadata required for TeamMatch discovery: title, organizer, category, eligibility, application dates, source URL and WEVITY `ix` identifier. It does not copy detailed article text or poster images.

The collector uses a descriptive User-Agent, timeout, one retry, sequential requests and a small page/detail cap. It does not use login, CAPTCHA solving, browser automation, anti-bot bypass or rate-limit circumvention. No explicit automated-access permission was established during review, so project documentation should not describe WEVITY as an officially licensed feed.

The MVP intentionally collects a useful current subset and does not claim complete coverage of Korean competitions.

## Competition schema

The existing `competitions.id` primary key remains unchanged. Phase 3 fields are:

- `category`
- `eligibility`
- `participation_type`
- `source_name`
- `source_url`
- `external_id`
- `fetched_at`
- `updated_at`
- `is_active`
- `application_start_date`
- `deadline_date`
- `original_deadline_text`

Legacy `name`, `organizer`, `deadline`, and `description` remain for compatibility. Existing team foreign keys are preserved.

`source_name + external_id` has a unique index. K-Startup uses `pbanc_sn`; WEVITY uses the stable `ix` query parameter.

## Normalization / safety

- Korean titles are preserved for display.
- K-Startup HTML fragments are converted to plain text.
- WEVITY long-form detail content is not stored; a short safe fallback description is used.
- Missing eligibility/participation data remains missing.
- Unknown/invalid dates remain NULL; no date is invented.
- D-day is calculated by TeamMatch at request time from `deadline_date`.
- Source URLs are retained and displayed with safe external-link attributes.
- Jinja auto-escaping remains enabled.

## Deduplication / update behavior

First identity:

```text
source_name + external_id
```

If there is no same-source identity match, TeamMatch performs a conservative cross-source fingerprint:

```text
normalized exact title
+ normalized organizer when both are present
+ exact deadline_date
```

No fuzzy similarity merge is used. This intentionally prefers occasional duplicates over incorrectly merging unrelated competitions.

When a cross-source duplicate is found, the existing TeamMatch row ID is reused. K-Startup provenance wins over WEVITY provenance because K-Startup is the official structured source.

The sync never implements `DELETE all competitions -> INSERT all`.

## Expiration

Known past deadlines are marked inactive, but rows are retained. Historical TeamMatch teams/applications continue to resolve the same competition ID. A listing merely disappearing from a source fetch is not automatically deleted or inactivated.

## Failure behavior

- One source fails -> log source failure, continue other sources.
- All sources fail -> non-zero exit, preserve all previous rows.
- One malformed record -> count/log and continue.
- No source failure causes table clearing or mass deletion.

## HTTP behavior

K-Startup:
- descriptive User-Agent
- 15-second timeout
- limited retries
- short page delay
- five-page MVP cap

WEVITY:
- descriptive User-Agent
- 15-second timeout
- one retry
- sequential requests only
- 0.7-second delay
- two listing pages / forty detail requests maximum per run

## Existing TeamMatch architecture preserved

Account, Join, Recruit, shortlist, applications, applicant ownership checks, Session 8 matching penalties/guard, Session 7 learning loop, admin authorization, CSRF, secure sessions, PostgreSQL, Gunicorn and `/healthz` remain separate from competition synchronization.

Competition data never modifies matching weights, feedback, reputation, or applicant status.
