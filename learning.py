import json
from collections import Counter
from datetime import datetime
from db import get_db
from matching import get_active_weights

REASON_TO_FACTOR = {
    "Availability": "availability",
    "Skill fit": "skills",
    "Preferred role": "preferred_role",
    "Working style": "working_style",
    "Project goals": "project_goal",
}
REASONS = list(REASON_TO_FACTOR) + ["Other"]
MIN_REJECTIONS_FOR_FACTOR = 5
WEIGHT_STEP = 0.05


def save_feedback(user_id, team_id, decision, reason, comment, score, factor_scores, weights, use_for_learning, demo=False):
    conn = get_db()
    conn.execute(
        """INSERT INTO recommendation_feedback
           (user_id, team_id, decision, reason, comment, matching_score,
            factor_scores_json, weights_json, use_for_learning, demo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, team_id, decision, reason or None, comment or None, float(score),
            json.dumps(factor_scores, sort_keys=True), json.dumps(weights, sort_keys=True),
            1 if use_for_learning else 0, 1 if demo else 0,
        ),
    )
    conn.commit()
    conn.close()


def feedback_summary():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM recommendation_feedback WHERE use_for_learning = 1 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    total = len(rows)
    accepts = sum(r["decision"] == "Accept" for r in rows)
    rejects = sum(r["decision"] == "Reject" for r in rows)
    mapped_rejects = [r for r in rows if r["decision"] == "Reject" and r["reason"] in REASON_TO_FACTOR]
    counts = Counter(r["reason"] for r in rows if r["decision"] == "Reject" and r["reason"])
    return {
        "rows": rows,
        "total": total,
        "accepts": accepts,
        "rejects": rejects,
        "acceptance_rate": round(accepts / total * 100, 1) if total else 0,
        "rejection_rate": round(rejects / total * 100, 1) if total else 0,
        "mismatch_rejection_rate": round(len(mapped_rejects) / total * 100, 1) if total else 0,
        "reason_counts": {reason: counts.get(reason, 0) for reason in REASONS},
    }


def _normalize_with_increase(weights, target, step=WEIGHT_STEP):
    proposed = dict(weights)
    increase = min(step, 0.95 - proposed[target])
    if increase <= 0:
        return proposed
    others = [k for k in proposed if k != target]
    other_total = sum(proposed[k] for k in others)
    proposed[target] += increase
    if other_total > 0:
        for k in others:
            proposed[k] -= increase * (proposed[k] / other_total)
    # Keep a clean total of exactly 1.0 after rounding.
    proposed = {k: round(v, 4) for k, v in proposed.items()}
    drift = round(1.0 - sum(proposed.values()), 4)
    proposed[others[-1]] = round(proposed[others[-1]] + drift, 4)
    return proposed


def generate_proposal():
    summary = feedback_summary()
    factor_counts = Counter()
    for row in summary["rows"]:
        if row["decision"] == "Reject" and row["reason"] in REASON_TO_FACTOR:
            factor_counts[REASON_TO_FACTOR[row["reason"]]] += 1
    if not factor_counts:
        return None
    factor, count = factor_counts.most_common(1)[0]
    if count < MIN_REJECTIONS_FOR_FACTOR:
        return None

    conn = get_db()
    pending = conn.execute("SELECT * FROM weight_proposals WHERE status = 'Pending' ORDER BY id DESC LIMIT 1").fetchone()
    if pending:
        conn.close()
        return pending

    weights = get_active_weights(conn)
    proposed = _normalize_with_increase(weights, factor)
    main_reason = next(reason for reason, mapped in REASON_TO_FACTOR.items() if mapped == factor)
    reason_text = (
        f"{main_reason} was selected in {count} learning-eligible rejection records. "
        f"The proposal increases its matching weight by 5 percentage points and redistributes the remaining weights proportionally."
    )
    cur = conn.execute(
        """INSERT INTO weight_proposals
           (factor, old_weights_json, proposed_weights_json, reason, feedback_count, main_reason)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (factor, json.dumps(weights, sort_keys=True), json.dumps(proposed, sort_keys=True), reason_text, count, main_reason),
    )
    conn.commit()
    proposal = conn.execute("SELECT * FROM weight_proposals WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return proposal


def review_proposal(proposal_id, action):
    if action not in {"Approved", "Rejected"}:
        raise ValueError("Invalid review action")
    conn = get_db()
    proposal = conn.execute("SELECT * FROM weight_proposals WHERE id = ?", (proposal_id,)).fetchone()
    if not proposal or proposal["status"] != "Pending":
        conn.close()
        return False

    if action == "Approved":
        old_weights = json.loads(proposal["old_weights_json"])
        new_weights = json.loads(proposal["proposed_weights_json"])
        conn.execute(
            """UPDATE matching_settings
               SET skills=?, availability=?, preferred_role=?, working_style=?, project_goal=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=1""",
            (new_weights["skills"], new_weights["availability"], new_weights["preferred_role"], new_weights["working_style"], new_weights["project_goal"]),
        )
        conn.execute(
            """INSERT INTO weight_history(old_weights_json, new_weights_json, reason, feedback_count)
               VALUES (?, ?, ?, ?)""",
            (json.dumps(old_weights, sort_keys=True), json.dumps(new_weights, sort_keys=True), proposal["reason"], proposal["feedback_count"]),
        )

    conn.execute(
        "UPDATE weight_proposals SET status=?, reviewed_at=? WHERE id=?",
        (action, datetime.utcnow().isoformat(timespec="seconds"), proposal_id),
    )
    conn.commit()
    conn.close()
    return True


def add_demo_feedback(user_id, team_id, score, factors, weights):
    # Clearly labelled demo records; enough Availability rejections to exercise the threshold.
    for _ in range(MIN_REJECTIONS_FOR_FACTOR):
        save_feedback(user_id, team_id, "Reject", "Availability", "Demo feedback for Session 7 loop", score, factors, weights, True, demo=True)
    save_feedback(user_id, team_id, "Accept", "Project goals", "Demo acceptance", score, factors, weights, True, demo=True)
