# AI Weight Judge Test Result

- AI Weight Judge focused tests: **19/19 PASS**
- Phase 2 updated regression: **PASS**
- Phase 3 regression: **PASS**
- Phase 4 regression: **22/22 PASS**
- Session 8 normal cases: **10/10 PASS**
- Session 8 attack cases: **5/5 PASS**

Covered AI cases include:
- availability-dominant evidence → valid Pending AI proposal
- no automatic activation before admin approval
- human approval activates validated weights
- weak evidence → AI not called before threshold
- `insufficient_evidence` → no actionable proposal, audit retained
- invalid >5 percentage-point change → rejected
- invalid output → active weights unchanged
- human rejection → active weights unchanged and proposal preserved
- repeated same batch does not create unlimited proposals
- failed AI runs remain retryable because only completed AI runs advance the feedback watermark
