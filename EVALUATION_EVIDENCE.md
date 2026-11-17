# TeamMatch — Demo Day Evaluation Evidence

## Key processes

1. Competition discovery — automated data ingestion; no teammate decision is delegated to AI.
2. Teammate matching — deterministic, explainable five-factor compatibility with critical mismatch safeguards.
3. Learning layer — aggregated recommendation feedback can be reviewed by the AI Weight Judge, followed by deterministic validation and mandatory human approval.

## Evals

- Session 8 normal cases: 10/10 PASS
- Session 8 attack cases: 5/5 PASS
- Phase 4 focused regression: 22/22 PASS
- AI Weight Judge contract tests: 19/19 PASS
- Before/after improvement fixtures: 5/5 PASS

## Improvement on the same cases

| Case | Before safeguards | Current | Change |
| --- | ---: | ---: | ---: |
| No required skill overlap | 65% | 40% | -25 pp |
| Non-flexible role mismatch | 80% | 60% | -20 pp |
| Opposite project-effort goal | 85% | 65% | -20 pp |
| All three critical mismatches | 30% | 0% | -30 pp after clamp |
| Strong match control | 100% | 100% | 0 pp |

These values are computed from the same fixed user/team fixtures. The only difference is whether Session 8 critical mismatch safeguards are applied.

## Development AI Eval Judge

A separate development evaluator reviewed eight fixed evaluation outputs:

- Correct outputs agreed: 4/4
- Intentionally broken outputs caught: 4/4
- Overall: 8/8

Judge used for this development evaluation: GPT-5.6 Sol.

This evaluator is separate from the product's production AI Weight Judge. It does not change users, scores, matching weights, or production data.

## Important limitation

The production OpenAI API call for AI Weight Judge was attempted but returned RateLimitError because API quota/billing was unavailable. The system failed safely: active weights remained unchanged and feedback remained retryable. The presentation should not claim a successful live production API proposal.
