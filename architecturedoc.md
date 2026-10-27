# Architecture Document

## Product
TeamMatch helps university students form teams for competitions and projects using structured compatibility information.

## User flow
Sign Up + Profile -> Login -> Join / Recruit -> Search Competition -> Matching -> Human Final Decision

Session 7 learning loop:
Recommendation -> Accept/Reject feedback -> reason stored -> feedback summary -> proposed weight change -> human review -> approved weights become active -> future recommendations use the updated weights.

## Current architecture
Browser
-> Flask/Jinja routes (`app.py`)
-> matching service (`matching.py`)
-> feedback-learning service (`learning.py`)
-> SQLite access/schema (`db.py`)
-> SQLite database (`teammatch.db`)

Templates live in `templates/` and styles in `static/`.

## Main responsibilities

### app.py
- HTTP routes, sessions, validation and page flow
- Sign up/login/logout
- Competition search
- Join/recruit flows
- Feedback submission and founder review routes

### db.py
- SQLite connection
- Schema creation/migration
- Active matching-weight storage
- Feedback, proposal and weight-history tables

### matching.py
- Transparent compatibility factors
- Current active matching weights
- Compatibility score and explanations

### learning.py
- Accept/Reject feedback storage
- Feedback summary metrics
- Reason-to-factor mapping
- Rule-based weight proposal generation
- Human approval/rejection
- Demo feedback generation

## Matching baseline
Initial weights preserve the pre-Session-7 MVP scoring logic:
- Skills: 35%
- Availability: 20%
- Preferred role: 20%
- Working style: 10%
- Project goal / effort: 15%

All weights sum to 100%.

## Feedback input
Each recommended team card supports:
- Accept
- Reject
- Optional reason
- Optional short comment

Reasons:
- Availability
- Skill fit
- Preferred role
- Working style
- Project goals
- Other

Accept means only that the user prefers the recommendation. It does not measure actual post-project teamwork success.

## Feedback storage
`recommendation_feedback` stores:
- user_id
- team_id
- Accept/Reject decision
- selected reason
- optional comment
- timestamp
- matching score at feedback time
- factor scores at feedback time
- matching weights at feedback time
- whether the feedback is eligible for learning
- whether the record is demo data

## Feedback-learning opt-out
Each user has `feedback_opt_in`.
Opting out does not change profile use, recommendations, applications or recruiting.
Feedback can still be recorded for the user's own interaction, but records captured while opted out are excluded from learning statistics and weight proposals.

## Pattern analysis
Founder review shows:
- total learning-eligible recommendation feedback
- Accept count
- Reject count
- acceptance rate
- rejection rate
- compatibility-mismatch rejection rate
- rejection-reason counts

Acceptance rate = Accept / (Accept + Reject).
No statistical-significance claim is made.

## Proposed matching change
Visible reason-to-factor mapping:
- Availability -> availability
- Skill fit -> skills
- Preferred role -> preferred_role
- Working style -> working_style
- Project goals -> project_goal

MVP proposal rule:
1. A single mapped rejection reason must occur at least 5 times in learning-eligible feedback.
2. The matching factor corresponding to the most repeated qualifying reason is proposed at +5 percentage points.
3. Remaining factors are reduced proportionally.
4. Proposed weights are normalized to total 100%.
5. A proposal never changes active weights by itself.

## Human safety check
Each proposal has Pending / Approved / Rejected status.
Only clicking Approve updates `matching_settings`.
Reject leaves active weights unchanged.

## Learning output
`matching.py` reads the current row in `matching_settings` whenever recommendations are calculated.
Therefore approved weights are actually used for future recommendations.

## Weight history
Approved changes are stored in `weight_history` with old weights, new weights, date, reason and supporting feedback count.

## Safety rule
Feedback must never create a permanent good/bad teammate score.
There is no personal reputation score, rejection penalty, reduced visibility or blacklist.
Learning only changes compatibility-factor weights.
No sensitive demographic characteristics are inferred.

## Recommendation explanations
Explanations remain tied to actual factor checks:
- matching skills
- compatible availability
- needed/preferred role fit
- working-style match
- project-goal alignment

## Deliberate tradeoffs
- University email is required, but real email verification is not implemented.
- Competition data is locally seeded.
- SQLite is sufficient for the MVP and easiest to inspect during development.
- No LLM or model fine-tuning is used in the Session 7 loop.
- Post-project team success is not measured yet.

## Session 7 implementation status
Implemented:
- recommendation feedback input
- optional reason/comment
- feedback snapshots
- learning opt-out
- feedback summary
- transparent reason-to-factor mapping
- normalized weight proposal
- minimum threshold
- founder human approval/rejection
- approved weights used in future matching
- weight history
- labelled demo data path
- person-level scoring safety rule

Not implemented:
- actual team-success outcome measurement
- real university email verification
- ML/LLM fine-tuning
- skill-development recommendations
