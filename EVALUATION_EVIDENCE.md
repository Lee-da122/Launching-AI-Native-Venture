# TeamMatch — Demo Day Evaluation Evidence

## Key processes

1. Competition discovery — automated data ingestion; no teammate decision is delegated to AI.
2. Teammate matching — deterministic, explainable five-factor compatibility with critical mismatch safeguards.
3. Learning layer — aggregated recommendation feedback can be reviewed by the AI Weight Judge, followed by deterministic validation and mandatory human approval.

## Current regression evidence

- Session 8 normal cases: **10/10 predefined cases passed**
- Session 8 attack cases: **5/5 predefined cases passed**
- Phase 4 focused regression: **22/22 checks passed**
- AI Weight Judge contract tests: **19/19 checks passed**
- Same-case safeguard comparison: **5/5 checks behaved as expected**

These are behavioral/regression tests defined for the MVP. They should not be presented as a 100% real-world teammate-matching accuracy rate.

The earlier Session 8 baseline of **7/10 normal** and **4/5 attack** was supplied in the Session 8 brief; it was not independently rerun from the old code in this final build.

## Same-case safeguard comparison

| Case | Before safeguards | Current | Change |
| --- | ---: | ---: | ---: |
| No required skill overlap | 65% | 40% | -25 pp |
| Non-flexible role mismatch | 80% | 60% | -20 pp |
| Opposite project-effort goal | 85% | 65% | -20 pp |
| All three critical mismatches | 30% | 0% | -30 pp after clamp |
| Strong match control | 100% | 100% | 0 pp |

These values are computed from the same fixed synthetic user/team fixtures. The comparison isolates the Session 8 critical-mismatch safeguards. It is evidence that the safeguards changed the intended edge cases without lowering the strong-match control; it is not evidence of real-world matching accuracy.

## AI Weight Judge evidence

The **19/19** figure refers to contract and safety tests around the AI-assisted learning layer, including moderate proposal limits, invalid-output rejection, pending status before approval, human approval/rejection behavior, retry behavior, and preservation of active weights on failure. It should not be described as "AI accuracy."

## Important limitation

The production OpenAI API call for AI Weight Judge was attempted but returned `RateLimitError` because API quota/billing was unavailable. The system failed safely: active weights remained unchanged and feedback remained retryable. The presentation should not claim a successful live production AI proposal.

No separate LLM-based eval-judge score is claimed in the final evidence because the previous 4/4 + 4/4 development numbers were not produced by a reproducible live judge call in this build.
