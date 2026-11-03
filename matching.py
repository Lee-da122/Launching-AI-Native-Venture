from db import get_db, DEFAULT_WEIGHTS

FACTOR_LABELS = {
    "skills": "Skills",
    "availability": "Availability",
    "preferred_role": "Preferred role",
    "working_style": "Working style",
    "project_goal": "Project goals",
}

SKILL_MISMATCH_PENALTY = 25
ROLE_MISMATCH_PENALTY = 20
GOAL_MISMATCH_PENALTY = 20
OPPOSITE_GOALS = {
    ("High quality / ambitious", "Minimum viable effort"),
    ("Minimum viable effort", "High quality / ambitious"),
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


def _critical_mismatches(user, team, needed_skills, matched_skills):
    """Return fixed-point compatibility penalties and their explanations.

    These rules are deliberately applied only to a team's explicit requirements.
    They do not create or store any permanent person-level score.
    """
    penalties = []

    if needed_skills and not matched_skills:
        penalties.append((
            SKILL_MISMATCH_PENALTY,
            "Critical mismatch: none of the team's required skills overlap with your current skills.",
        ))

    role_is_flexible = user["preferred_role"] == "Flexible" or team["needed_role"] == "Flexible"
    if not role_is_flexible and user["preferred_role"] != team["needed_role"]:
        penalties.append((
            ROLE_MISMATCH_PENALTY,
            "Critical mismatch: your preferred role differs from the role the team needs.",
        ))

    if (user["project_goal"], team["project_goal"]) in OPPOSITE_GOALS:
        penalties.append((
            GOAL_MISMATCH_PENALTY,
            "Critical mismatch: your expected project effort is very different from the team's.",
        ))

    return penalties


def compatibility(user, team, weights=None):
    """Calculate explainable compatibility using active weights, then penalties.

    Session 7 active/human-approved weights remain the base scoring system.
    Session 8 critical mismatch penalties are fixed-point post-processing rules.
    """
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

    # Preserve the current active-weight calculation exactly as the base score.
    raw = sum(factors[k] * weights[k] for k in weights)
    base_score = round(raw * 100)

    # Session 8: apply transparent fixed-point penalties after the normal score.
    penalties = _critical_mismatches(user, team, needed_skills, matched_skills)
    penalty_total = sum(points for points, _ in penalties)
    for _, explanation in penalties:
        reasons.append(explanation)

    if not reasons:
        reasons.append("Some profile criteria differ; review the team details before deciding")

    final_score = max(0, min(100, base_score - penalty_total))
    return final_score, reasons, factors
