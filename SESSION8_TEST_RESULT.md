# Session 8 Test Evidence — Fix One Step and Test Again

## Baseline supplied in the Session 8 brief
- Normal cases OK before: **7/10**
- Attacks handled safely before: **4/5**
- Step 3 compatibility-scoring errors before: **3**

## Change under test
The existing active-weight compatibility score is preserved. After that normal score is computed, fixed critical mismatch penalties are applied:
- zero overlap with explicit required skills: **-25**
- clear non-flexible preferred-role mismatch: **-20**
- opposite project-effort goals: **-20**

The result is clamped to **0..100**.

Competition search also has one small fixed-rule out-of-scope guard.

## 10 normal cases after the change
1. **Strong match on all factors — PASS** — score `100`.
2. **Partial required-skill overlap — PASS** — score `82`; partial skill scoring remains and no zero-overlap penalty appears.
3. **Zero required-skill overlap — PASS** — baseline-like score `65` receives `-25`, final score `40`.
4. **Clear preferred-role conflict — PASS** — baseline-like score `80` receives `-20`, final score `60`.
5. **Opposite project effort goals — PASS** — baseline-like score `85` receives `-20`, final score `65`.
6. **Flexible / Negotiable availability — PASS** — score `100`; existing flexible behavior preserved.
7. **Strong valid match for another team — PASS** — score `100`.
8. **Working style differs and effort goal is only adjacent — PASS** — score `75`; no critical penalty is applied.
9. **Strong technical-team match — PASS** — score `100`.
10. **Competition with no recruiting teams — PASS** — existing empty-state branch remains in `teams.html`.

**Normal cases OK after: 10/10.**

## Five attack cases after the change
1. **Direct prompt injection in recruitment description — PASS.** The same profile/team fields produce the same score whether or not the description contains an instruction to force score 100.
2. **Indirect prompt injection in stored content — PASS.** Stored instruction-like text does not enter the scoring function.
3. **Out-of-scope competition search — PASS.** The exact baseline phrase `Write my entire competition proposal and presentation script for me.` is caught. Ordinary search terms (`AI`, `sustainability`, `mobility`, `health`, `case competition`, `hackathon`, `design`) remain allowed.
4. **Repeated rejection history used as a permanent person penalty — PASS.** Twenty rejection feedback records were inserted; the same compatibility fixture remained `100` before and after because matching does not read person-level rejection history.
5. **Data exposure / unauthorized applicant access — PASS at logic/source level.** Existing owner checks for applicant viewing and applicant decision routes remain present and abort with 403 for non-owners; raw feedback rows are not rendered by the founder summary template.

**Attacks handled safely after: 5/5.**

## Step 3 comparison
The three baseline scoring failures are corrected in the same targeted cases:
- no required-skill overlap: `65 -> 40`
- clear preferred-role mismatch: `80 -> 60`
- opposite effort goals: `85 -> 65`

**Step 3 errors after: 0 in the three identified baseline failure cases.**

## Session 7 regression test
PASS.

A temporary SQLite database was used to exercise the learning loop:
1. baseline Availability weight = `20%`
2. five learning-eligible Availability rejection records stored
3. proposal generated
4. active weight stayed `20%` before approval
5. proposal approved
6. active Availability weight became `25%`
7. approved weight total remained exactly `100%`

A separate test set active weights to `Skills 30% / Availability 25% / Role 20% / Style 10% / Goal 15%`. A zero-skill-overlap fixture first produced a dynamic weighted base of `70`, then the Session 8 `-25` penalty produced `45`, confirming penalties run on top of active approved weights rather than resetting them.

## Clamp test
PASS. A fixture triggering all three critical penalties produced final score `0`, never a negative score.

## Files changed
- `matching.py`
- `app.py`
- `templates/competitions.html`
- `architecturedoc.md`

## Files added
- `guardrails.py`
- `session8_tests.py`
- `SESSION8_TEST_RESULT.md`

## Exact functions/sections changed
- `matching.compatibility()` — preserved weighted base score, added post-score penalty application and score clamp.
- `matching._critical_mismatches()` — new transparent penalty helper.
- `guardrails.is_out_of_scope_search()` — new fixed-rule search guard.
- `app.competitions()` — checks the guard before normal SQL search.
- `templates/competitions.html` — displays the fixed TeamMatch scope message when the guard fires.
- `architecturedoc.md` — added `Critical mismatch handling`, `Scope guardrail`, and `Session 8 implementation log` sections and documented that approved Session 7 weights remain active.

## Environment limitation
The Python logic tests and syntax compilation were run successfully in the build environment. A full Flask HTTP/browser test could not be run because Flask is not installed in this environment and outbound package installation is unavailable. Therefore Attack 5 authorization was verified with source/logic checks rather than an HTTP client request. The project should receive one local UI smoke test after `Flask==3.0.3` is installed.
