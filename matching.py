from db import get_db, DEFAULT_WEIGHTS

FACTOR_LABELS = {
    "skills": "Skills",
    "availability": "Availability",
    "preferred_role": "Preferred role",
    "working_style": "Working style",
    "project_goal": "Project goals",
}


def split_values(text):
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def get_active_weights(conn=None):
    owns = conn is None
    conn = conn or get_db()
    row = conn.execute("SELECT * FROM matching_settings WHERE id = 1").fetchone()
    if owns:
        conn.close()
    if not row:
        return DEFAULT_WEIGHTS.copy()
    return {k: float(row[k]) for k in DEFAULT_WEIGHTS}


def compatibility(user, team, weights=None):
    weights = weights or get_active_weights()
    reasons = []

    user_skills = set(split_values(user["skills"]))
    needed_skills = set(split_values(team["needed_skills"]))
    matched_skills = sorted(user_skills & needed_skills)
    skill_factor = len(matched_skills) / len(needed_skills) if needed_skills else 0.0

    availability_factor = 1.0 if (
        user["availability"] == team["availability"]
        or user["availability"] == "Flexible / Negotiable"
        or team["availability"] == "Flexible / Negotiable"
    ) else 0.0

    role_factor = 1.0 if (
        user["preferred_role"] == team["needed_role"]
        or user["preferred_role"] == "Flexible"
        or team["needed_role"] == "Flexible"
    ) else 0.0

    style_factor = 1.0 if user["working_style"] == team["working_style"] else 0.0
    goal_factor = 1.0 if user["project_goal"] == team["project_goal"] else 0.0

    factors = {
        "skills": round(skill_factor, 4),
        "availability": availability_factor,
        "preferred_role": role_factor,
        "working_style": style_factor,
        "project_goal": goal_factor,
    }

    if matched_skills:
        reasons.append("Skill fit: " + ", ".join(matched_skills))
    if availability_factor:
        reasons.append("Availability is compatible")
    if role_factor:
        reasons.append("Preferred role fits the team's need")
    if style_factor:
        reasons.append("Working styles match")
    if goal_factor:
        reasons.append("Project effort goals are aligned")
    if not reasons:
        reasons.append("Some profile criteria differ; review the team details before deciding")

    raw = sum(factors[k] * weights[k] for k in weights)
    score = round(raw * 100)
    return min(score, 100), reasons, factors
