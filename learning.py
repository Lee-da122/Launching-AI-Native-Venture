import json
from collections import Counter
from datetime import datetime, timezone

from ai_weight_judge import (
    AIWeightJudgeError,
    AIWeightValidationError,
    FACTOR_KEYS,
    build_aggregate_input,
    is_ai_configured,
    judge_weights,
    validate_proposed_weights,
)
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


def save_feedback(user_id, team_id, decision, reason, comment, score, factor_scores, weights, use_for_learning, demo=False):
    conn = get_db()
    conn.execute(
        """INSERT INTO recommendation_feedback
           (user_id, team_id, decision, reason, comment, matching_score,
            factor_scores_json, weights_json, use_for_learning, demo)
           VALUES (:user_id, :team_id, :decision, :reason, :comment, :matching_score,
                   :factor_scores_json, :weights_json, :use_for_learning, :demo)""",
        {
            "user_id": user_id,
            "team_id": team_id,
            "decision": decision,
            "reason": reason or None,
            "comment": comment or None,
            "matching_score": float(score),
            "factor_scores_json": json.dumps(factor_scores, sort_keys=True),
            "weights_json": json.dumps(weights, sort_keys=True),
            "use_for_learning": bool(use_for_learning),
            "demo": bool(demo),
        },
    )
    conn.commit()
    conn.close()


def feedback_summary(since_id=0):
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM recommendation_feedback
           WHERE use_for_learning = :enabled AND id > :since_id
           ORDER BY id ASC""",
        {"enabled": True, "since_id": int(since_id or 0)},
    ).fetchall()
    excluded_count = conn.execute(
        "SELECT COUNT(*) AS n FROM recommendation_feedback WHERE use_for_learning = :enabled AND id > :since_id",
        {"enabled": False, "since_id": int(since_id or 0)},
    ).fetchone()["n"]
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
        "excluded_count": int(excluded_count or 0),
        "feedback_min_id": rows[0]["id"] if rows else None,
        "feedback_max_id": rows[-1]["id"] if rows else None,
    }


def _last_considered_feedback_id(conn):
    row = conn.execute(
        """SELECT feedback_max_id FROM ai_weight_judge_runs
           WHERE feedback_max_id IS NOT NULL AND status = 'Completed'
           ORDER BY id DESC LIMIT 1"""
    ).fetchone()
    return int(row["feedback_max_id"]) if row and row["feedback_max_id"] is not None else 0


def _proposal_history_summary(conn, limit=5):
    rows = conn.execute(
        """SELECT status, proposal_source, feedback_count, created_at
           FROM weight_proposals ORDER BY id DESC LIMIT :limit""",
        {"limit": limit},
    ).fetchall()
    return [
        {
            "status": row["status"],
            "source": row["proposal_source"] or "Rule-based",
            "feedback_count": row["feedback_count"],
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def _dominant_factor_change(old_weights, new_weights):
    return max(FACTOR_KEYS, key=lambda key: abs(float(new_weights[key]) - float(old_weights[key])))


def _insert_ai_run(conn, *, decision, current_weights, proposed_weights, reason, evidence_summary,
                   aggregate_input, summary, status, error_message=None):
    row = conn.execute(
        """INSERT INTO ai_weight_judge_runs
           (decision, current_weights_json, proposed_weights_json, reason, evidence_summary,
            aggregate_input_json, eligible_feedback_count, excluded_feedback_count,
            feedback_min_id, feedback_max_id, status, error_message)
           VALUES (:decision, :current_weights_json, :proposed_weights_json, :reason, :evidence_summary,
                   :aggregate_input_json, :eligible_feedback_count, :excluded_feedback_count,
                   :feedback_min_id, :feedback_max_id, :status, :error_message)
           RETURNING *""",
        {
            "decision": decision,
            "current_weights_json": json.dumps(current_weights, sort_keys=True),
            "proposed_weights_json": json.dumps(proposed_weights, sort_keys=True) if proposed_weights else None,
            "reason": reason,
            "evidence_summary": evidence_summary,
            "aggregate_input_json": json.dumps(aggregate_input, sort_keys=True),
            "eligible_feedback_count": summary["total"],
            "excluded_feedback_count": summary.get("excluded_count", 0),
            "feedback_min_id": summary.get("feedback_min_id"),
            "feedback_max_id": summary.get("feedback_max_id"),
            "status": status,
            "error_message": error_message,
        },
    ).fetchone()
    return row


def generate_proposal(judge_fn=None):
    """Generate an AI-assisted pending proposal. Never activates weights automatically."""
    conn = get_db()
    pending = conn.execute(
        "SELECT * FROM weight_proposals WHERE status = :status ORDER BY id DESC LIMIT 1",
        {"status": "Pending"},
    ).fetchone()
    if pending:
        conn.close()
        return {"status": "pending_exists", "proposal": pending, "message": "A Pending proposal already exists."}

    last_id = _last_considered_feedback_id(conn)
    summary = feedback_summary(since_id=last_id)
    factor_counts = Counter()
    for row in summary["rows"]:
        if row["decision"] == "Reject" and row["reason"] in REASON_TO_FACTOR:
            factor_counts[REASON_TO_FACTOR[row["reason"]]] += 1

    if not factor_counts or factor_counts.most_common(1)[0][1] < MIN_REJECTIONS_FOR_FACTOR:
        conn.close()
        return {
            "status": "insufficient_trigger",
            "proposal": None,
            "message": "Not enough new repeated rejection evidence yet. A mapped factor needs at least 5 new learning-eligible rejections.",
        }

    current_weights = get_active_weights(conn)
    history_summary = _proposal_history_summary(conn)
    aggregate_input = build_aggregate_input(current_weights, summary, history_summary)

    if judge_fn is None:
        if not is_ai_configured():
            conn.close()
            return {
                "status": "ai_unavailable",
                "proposal": None,
                "message": "AI Weight Judge is unavailable because its production configuration is missing.",
            }
        judge_fn = judge_weights

    try:
        result = judge_fn(aggregate_input)
        if isinstance(result, dict):
            from ai_weight_judge import parse_judge_result
            result = parse_judge_result(result)

        if result.decision in {"no_change", "insufficient_evidence"}:
            # Validate that non-actionable decisions did not smuggle in a weight change.
            unchanged = {key: float(current_weights[key]) for key in FACTOR_KEYS}
            validated_non_action = validate_proposed_weights(current_weights, result.proposed_weights)
            for key in FACTOR_KEYS:
                if abs(validated_non_action[key] - unchanged[key]) > 1e-9:
                    raise AIWeightValidationError("Non-actionable AI decisions must return the current weights unchanged.")
            _insert_ai_run(
                conn, decision=result.decision, current_weights=current_weights,
                proposed_weights=unchanged, reason=result.reason, evidence_summary=result.evidence_summary,
                aggregate_input=aggregate_input, summary=summary, status="Completed",
            )
            conn.commit()
            conn.close()
            label = "No weight change recommended." if result.decision == "no_change" else "AI judged the evidence insufficient for a weight change."
            return {"status": result.decision, "proposal": None, "message": label}

        proposed = validate_proposed_weights(current_weights, result.proposed_weights)
        ai_run = _insert_ai_run(
            conn, decision=result.decision, current_weights=current_weights,
            proposed_weights=proposed, reason=result.reason, evidence_summary=result.evidence_summary,
            aggregate_input=aggregate_input, summary=summary, status="Completed",
        )
        factor = _dominant_factor_change(current_weights, proposed)
        proposal = conn.execute(
            """INSERT INTO weight_proposals
               (factor, old_weights_json, proposed_weights_json, reason, feedback_count, main_reason,
                proposal_source, ai_reason, evidence_summary, eligible_feedback_count, feedback_max_id, ai_run_id)
               VALUES (:factor, :old_weights_json, :proposed_weights_json, :reason, :feedback_count, :main_reason,
                       :proposal_source, :ai_reason, :evidence_summary, :eligible_feedback_count, :feedback_max_id, :ai_run_id)
               RETURNING *""",
            {
                "factor": factor,
                "old_weights_json": json.dumps(current_weights, sort_keys=True),
                "proposed_weights_json": json.dumps(proposed, sort_keys=True),
                "reason": result.reason,
                "feedback_count": summary["total"],
                "main_reason": "AI Weight Judge",
                "proposal_source": "AI",
                "ai_reason": result.reason,
                "evidence_summary": result.evidence_summary,
                "eligible_feedback_count": summary["total"],
                "feedback_max_id": summary.get("feedback_max_id"),
                "ai_run_id": ai_run["id"],
            },
        ).fetchone()
        conn.commit()
        conn.close()
        return {"status": "proposal_created", "proposal": proposal, "message": "AI proposal ready for human review. It is not active yet."}

    except (AIWeightJudgeError, AIWeightValidationError) as exc:
        try:
            _insert_ai_run(
                conn, decision="error", current_weights=current_weights,
                proposed_weights=None, reason=None, evidence_summary=None,
                aggregate_input=aggregate_input, summary=summary, status="Failed",
                error_message=str(exc),
            )
            conn.commit()
        finally:
            conn.close()
        return {"status": "ai_error", "proposal": None, "message": f"AI proposal generation failed safely: {exc}"}
    except Exception as exc:
        try:
            _insert_ai_run(
                conn, decision="error", current_weights=current_weights,
                proposed_weights=None, reason=None, evidence_summary=None,
                aggregate_input=aggregate_input, summary=summary, status="Failed",
                error_message=f"Unexpected {exc.__class__.__name__}",
            )
            conn.commit()
        finally:
            conn.close()
        return {"status": "ai_error", "proposal": None, "message": "AI proposal generation failed safely. Active weights were not changed."}


def review_proposal(proposal_id, action):
    if action not in {"Approved", "Rejected"}:
        raise ValueError("Invalid review action")

    conn = get_db()
    proposal = conn.execute(
        "SELECT * FROM weight_proposals WHERE id = :proposal_id",
        {"proposal_id": proposal_id},
    ).fetchone()
    if not proposal or proposal["status"] != "Pending":
        conn.close()
        return False

    if action == "Approved":
        old_weights = json.loads(proposal["old_weights_json"])
        new_weights = json.loads(proposal["proposed_weights_json"])
        # Revalidate AI proposals at approval time as defense in depth.
        if (proposal["proposal_source"] or "Rule-based") == "AI":
            new_weights = validate_proposed_weights(old_weights, new_weights)
        conn.execute(
            """UPDATE matching_settings
               SET skills=:skills, availability=:availability, preferred_role=:preferred_role,
                   working_style=:working_style, project_goal=:project_goal,
                   updated_at=CURRENT_TIMESTAMP
               WHERE id=:id""",
            {"id": 1, **new_weights},
        )
        conn.execute(
            """INSERT INTO weight_history(old_weights_json, new_weights_json, reason, feedback_count)
               VALUES (:old_weights_json, :new_weights_json, :reason, :feedback_count)""",
            {
                "old_weights_json": json.dumps(old_weights, sort_keys=True),
                "new_weights_json": json.dumps(new_weights, sort_keys=True),
                "reason": proposal["reason"],
                "feedback_count": proposal["feedback_count"],
            },
        )

    conn.execute(
        "UPDATE weight_proposals SET status=:status, reviewed_at=:reviewed_at WHERE id=:proposal_id",
        {
            "status": action,
            "reviewed_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "proposal_id": proposal_id,
        },
    )
    conn.commit()
    conn.close()
    return True


def recent_ai_runs(limit=10):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM ai_weight_judge_runs ORDER BY id DESC LIMIT :limit",
        {"limit": limit},
    ).fetchall()
    conn.close()
    return rows


def add_demo_feedback(user_id, team_id, score, factors, weights):
    for _ in range(MIN_REJECTIONS_FOR_FACTOR):
        save_feedback(
            user_id, team_id, "Reject", "Availability",
            "Demo feedback for AI Weight Judge loop", score, factors, weights, True, demo=True,
        )
    save_feedback(
        user_id, team_id, "Accept", "Project goals",
        "Demo acceptance", score, factors, weights, True, demo=True,
    )
