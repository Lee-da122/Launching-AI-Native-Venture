# TeamMatch AI Weight Judge — Final Report

## A. Existing learning logic
Replaced only the deterministic proposal-generation step. Previously, the most repeated mapped rejection factor at count >= 5 was increased by a fixed 5 percentage points and the other factors were reduced proportionally. Feedback storage, human approval/rejection, matching_settings activation, weight_history, and the rule-based compatibility engine remain.

## B. Files changed
- app.py
- db.py
- learning.py
- templates/learning.html
- requirements.txt
- .env.example
- README.md
- scope.md
- architecturedoc.md
- phase2_tests.py

## C. Files added
- ai_weight_judge.py
- ai_weight_judge_tests.py
- AI_WEIGHT_JUDGE_TEST_RESULT.md
- AI_WEIGHT_JUDGE_REPORT.md

## D. AI Weight Judge input
Only sanitized aggregate fields are sent:
- current five active weights
- eligible feedback total
- Accept count
- Reject count
- acceptance rate
- rejection-reason counts: Availability, Skill fit, Preferred role, Working style, Project goals, Other
- count excluded from learning
- compact recent proposal history: status, source, feedback count, timestamp

## E. Privacy
Explicitly excluded from the AI payload:
- student names
- email addresses / university email
- passwords
- applicant identities
- individual recommendation histories
- permanent person-level reputation or quality scores

## F. AI output schema
Structured JSON:
- decision: `propose_change | no_change | insufficient_evidence`
- proposed_weights: exactly skills, availability, preferred_role, working_style, project_goal
- reason: short evidence-based rationale
- evidence_summary: short aggregate-evidence statement

For no_change / insufficient_evidence, proposed_weights must equal the current weights.

## G. Deterministic validation
For actionable AI proposals:
- exactly five required factor keys
- numeric, finite values only
- each factor 5%–50%
- total 100% within 0.2 percentage-point minor rounding tolerance
- only tiny rounding drift may be normalized
- no factor may move more than 5 percentage points from current active weights
- invalid output is rejected, not clamped
- validation runs again at approval time for AI proposals

## H. Proposal trigger
The AI is not called on every feedback event. Since the last completed AI Judge run, at least one mapped factor must accumulate >= 5 new learning-eligible rejection records. A currently Pending proposal also prevents another proposal call.

Only completed AI runs advance the feedback watermark. Failed provider/validation runs remain retryable.

## I. Human approval
A valid AI result creates a `Pending` proposal only. `matching_settings` is unchanged until an admin submits Approve. Reject changes only the proposal status. Approve updates matching_settings and writes weight_history.

## J. Database changes
Safe additive migration only.

Added weight_proposals columns:
- proposal_source
- ai_reason
- evidence_summary
- eligible_feedback_count
- feedback_max_id
- ai_run_id

Added table:
- ai_weight_judge_runs

No existing proposal, feedback, history, or active-weight rows are deleted or reset. Historical proposals default to `Rule-based`.

## K. Failure behavior
Missing configuration, API failure, timeout, invalid JSON/schema, invalid business-rule weights, rate limiting, and provider errors fail safely. No active weights change, recommendation feedback remains stored, and Join/Recruit/matching continue to work. No fake deterministic fallback is presented as AI.

## L. Availability-dominant test
PASS. Five learning-eligible Availability rejections produced a mocked AI proposal: Skills 33%, Availability 25%, Preferred Role 19%, Working Style 9%, Project Goal 14%. Status remained Pending and active weights stayed unchanged before approval.

## M. Weak-evidence test
PASS. Mixed 2 Availability + 2 Skill-fit rejections did not meet the trigger; AI was not called and no proposal was created. A separate `insufficient_evidence` AI result was accepted as a valid non-actionable outcome, audited, and produced no Pending proposal.

## N. Invalid-output test
PASS. A mocked proposal containing a >5 percentage-point change was rejected by deterministic validation. No Pending proposal was created and active weights remained unchanged.

## O. Human approve/reject test
PASS. Approval activated validated proposed weights and wrote history. Rejection left active weights unchanged and preserved the proposal with Rejected status.

## P. Session 8 regression
PASS — Normal 10/10, Attack 5/5. Critical mismatch logic and 0–100 clamping were not changed.

## Q. Production deployment
Code is ready for Railway deployment, but the real AI API call is **not yet production-verified** because the current Railway service does not have `OPENAI_API_KEY` and `AI_WEIGHT_JUDGE_MODEL` configured. This report does not claim a live API test.

## R. Remaining limitations
- AI proposal quality depends on aggregate recommendation-preference feedback; TeamMatch still has no ground-truth post-project outcome data.
- The model/provider must be configured separately in Railway.
- AI does not score individual teammates and cannot automatically approve changes.
- The trigger intentionally requires new evidence after a completed AI run, so weight changes are conservative rather than continuous.
