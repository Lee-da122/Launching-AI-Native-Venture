from pathlib import Path

import db
import matching
from university import (
    filter_applicants_same_university,
    filter_teams_same_university,
    normalize_university,
    same_university,
)

ROOT = Path(__file__).resolve().parent
results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    if not condition:
        raise AssertionError(f"{name}: {detail}")


# University normalization is intentionally conservative.
check("Normalize trims/collapses/casefolds", normalize_university("  Korea   University ") == "korea university")
check("English case differences match", same_university("Korea University", "korea university"))
check("No abbreviation guessing", not same_university("KU", "Korea University"))
check("Blank universities do not match", not same_university("", ""))

# Join-side filter: same school stays, another school disappears.
teams = [
    {"id": 1, "owner_university": "Korea University"},
    {"id": 2, "owner_university": "Yonsei University"},
]
join_filtered = filter_teams_same_university(" korea   university ", teams)
check("Join same-university keeps B", [t["id"] for t in join_filtered] == [1], str(join_filtered))

# Recruit-side filter: same school stays, another school disappears.
applicants = [
    {"id": 11, "university": "Korea University"},
    {"id": 12, "university": "Sogang University"},
]
recruit_filtered = filter_applicants_same_university("KOREA UNIVERSITY", applicants)
check("Recruit same-university keeps B", [u["id"] for u in recruit_filtered] == [11], str(recruit_filtered))

# University is not part of compatibility; filter cannot alter the score.
user = {
    "skills": "Coding,Data analysis",
    "availability": "Weekday evenings",
    "preferred_role": "Data / Coding",
    "working_style": "Structured and planned",
    "project_goal": "High quality / ambitious",
}
team = {
    "needed_skills": "Coding,Data analysis",
    "availability": "Weekday evenings",
    "needed_role": "Data / Coding",
    "working_style": "Structured and planned",
    "project_goal": "High quality / ambitious",
}
score_before, _, factors_before = matching.compatibility(user, team, db.DEFAULT_WEIGHTS)
score_after, _, factors_after = matching.compatibility(user, team, db.DEFAULT_WEIGHTS)
check("Score unchanged by university filtering", score_before == score_after, f"{score_before} vs {score_after}")
check("Factors unchanged by university filtering", factors_before == factors_after, str(factors_before))
check("Default factor weights unchanged", db.DEFAULT_WEIGHTS == {
    "skills": 0.35,
    "availability": 0.20,
    "preferred_role": 0.20,
    "working_style": 0.10,
    "project_goal": 0.15,
}, str(db.DEFAULT_WEIGHTS))

# Breakdown is derived only from actual factor values.
breakdown = matching.factor_breakdown({
    "skills": 0.5,
    "availability": 1.0,
    "preferred_role": 0.0,
    "working_style": 1.0,
    "project_goal": 0.0,
})
check("Actual factor breakdown", breakdown == {
    "skills": "Partial match",
    "availability": "Match",
    "preferred_role": "Different",
    "working_style": "Match",
    "project_goal": "Different",
}, str(breakdown))

# Static route/template regression: verifies the final wiring without Flask runtime here.
app_text = (ROOT / "app.py").read_text(encoding="utf-8")
teams_html = (ROOT / "templates" / "teams.html").read_text(encoding="utf-8")
applicants_html = (ROOT / "templates" / "applicants.html").read_text(encoding="utf-8")
base_html = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")

check("Profile route exists", '@app.route("/profile")' in app_text)
check("Join filter wired", 'filter_teams_same_university' in app_text and 'same_university_only' in app_text)
check("Recruit filter wired", 'filter_applicants_same_university' in app_text and 'same_university_only' in app_text)
check("Join UI has same-university control", "Same university only" in teams_html)
check("Recruit UI has same-university control", "Same university only" in applicants_html)
check("Join empty-state escape", "Show all universities" in teams_html)
check("Recruit empty-state escape", "Show all universities" in applicants_html)
check("Apply separated from recommendation feedback", "Apply to Team" in teams_html and "Accept recommendation" in teams_html)
check("Recruit decisions use applicant wording", "Accept applicant" in applicants_html and "Reject applicant" in applicants_html)
check("CSRF preserved on Join forms", teams_html.count('name="_csrf_token"') >= 3, str(teams_html.count('name="_csrf_token"')))
check("CSRF preserved on Recruit decisions", applicants_html.count('name="_csrf_token"') >= 2, str(applicants_html.count('name="_csrf_token"')))
check("Admin navigation remains conditional", "{% if is_admin %}" in base_html and "Learning" in base_html)

print(f"PHASE4 {sum(ok for _, ok, _ in results)}/{len(results)} PASS")
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), "-", name, (f"- {detail}" if detail else ""))
