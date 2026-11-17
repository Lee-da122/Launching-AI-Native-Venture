import json
import math
import os
from dataclasses import dataclass

FACTOR_KEYS = ("skills", "availability", "preferred_role", "working_style", "project_goal")
ALLOWED_DECISIONS = {"propose_change", "no_change", "insufficient_evidence"}
MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.50
MAX_CHANGE = 0.05
TOTAL_TOLERANCE = 0.002


class AIWeightJudgeError(RuntimeError):
    pass


class AIWeightValidationError(ValueError):
    pass


@dataclass
class JudgeResult:
    decision: str
    proposed_weights: dict
    reason: str
    evidence_summary: str

    def as_dict(self):
        return {
            "decision": self.decision,
            "proposed_weights": self.proposed_weights,
            "reason": self.reason,
            "evidence_summary": self.evidence_summary,
        }


def is_ai_configured():
    return bool(os.getenv("OPENAI_API_KEY", "").strip() and os.getenv("AI_WEIGHT_JUDGE_MODEL", "").strip())


def build_aggregate_input(current_weights, summary, proposal_history=None):
    """Build a privacy-preserving aggregate payload. No person-level fields are included."""
    return {
        "current_active_weights": {key: float(current_weights[key]) for key in FACTOR_KEYS},
        "eligible_recommendation_feedback": {
            "total": int(summary.get("total", 0)),
            "accept": int(summary.get("accepts", 0)),
            "reject": int(summary.get("rejects", 0)),
            "acceptance_rate_percent": float(summary.get("acceptance_rate", 0)),
            "rejection_reasons": {
                "Availability": int(summary.get("reason_counts", {}).get("Availability", 0)),
                "Skill fit": int(summary.get("reason_counts", {}).get("Skill fit", 0)),
                "Preferred role": int(summary.get("reason_counts", {}).get("Preferred role", 0)),
                "Working style": int(summary.get("reason_counts", {}).get("Working style", 0)),
                "Project goals": int(summary.get("reason_counts", {}).get("Project goals", 0)),
                "Other": int(summary.get("reason_counts", {}).get("Other", 0)),
            },
            "excluded_from_learning": int(summary.get("excluded_count", 0)),
        },
        "proposal_history_summary": proposal_history or [],
    }


def _schema():
    weight_properties = {key: {"type": "number"} for key in FACTOR_KEYS}
    return {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["propose_change", "no_change", "insufficient_evidence"],
            },
            "proposed_weights": {
                "type": "object",
                "properties": weight_properties,
                "required": list(FACTOR_KEYS),
                "additionalProperties": False,
            },
            "reason": {"type": "string"},
            "evidence_summary": {"type": "string"},
        },
        "required": ["decision", "proposed_weights", "reason", "evidence_summary"],
        "additionalProperties": False,
    }


def _instructions():
    return """You are TeamMatch's AI Weight Judge. You adjust GLOBAL MATCHING FACTOR WEIGHTS, not people.
Use only the aggregated recommendation-feedback evidence provided. Never evaluate or rank individual students, infer demographic or personal characteristics, create reputation scores, or recommend removing human review.

Rules:
- The five factors are skills, availability, preferred_role, working_style, project_goal.
- Prefer no_change or insufficient_evidence when evidence is weak or mixed.
- If proposing a change, keep it moderate and evidence-based.
- All five factors must remain represented.
- Proposed weights must sum to 1.0.
- Keep every factor between 0.05 and 0.50.
- Move no factor by more than 0.05 from the current active value.
- Explain the proposal using the supplied aggregate counts only.
- A proposal is advisory and will require deterministic validation and human approval before activation.
- For no_change or insufficient_evidence, return the current weights unchanged in proposed_weights.
"""


def judge_weights(aggregate_input):
    """Call OpenAI with Structured Outputs and return a parsed JudgeResult."""
    if not is_ai_configured():
        raise AIWeightJudgeError("AI Weight Judge is not configured. Set OPENAI_API_KEY and AI_WEIGHT_JUDGE_MODEL.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIWeightJudgeError("The OpenAI SDK is not installed.") from exc

    try:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=20.0, max_retries=1)
        response = client.responses.create(
            model=os.environ["AI_WEIGHT_JUDGE_MODEL"],
            instructions=_instructions(),
            input=(
                "Review this sanitized aggregate TeamMatch evidence and return a JSON decision. "
                "Do not use any information beyond this payload:\n" + json.dumps(aggregate_input, ensure_ascii=False, sort_keys=True)
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "team_match_weight_judge",
                    "strict": True,
                    "schema": _schema(),
                }
            },
        )
        raw = response.output_text
        if not raw:
            raise AIWeightJudgeError("AI Weight Judge returned no output.")
        data = json.loads(raw)
    except AIWeightJudgeError:
        raise
    except Exception as exc:
        raise AIWeightJudgeError(f"AI Weight Judge request failed: {exc.__class__.__name__}") from exc

    return parse_judge_result(data)


def parse_judge_result(data):
    if not isinstance(data, dict):
        raise AIWeightValidationError("AI output must be a JSON object.")
    decision = data.get("decision")
    if decision not in ALLOWED_DECISIONS:
        raise AIWeightValidationError("AI output contains an invalid decision.")
    proposed = data.get("proposed_weights")
    if not isinstance(proposed, dict):
        raise AIWeightValidationError("AI output is missing proposed_weights.")
    if set(proposed.keys()) != set(FACTOR_KEYS):
        raise AIWeightValidationError("AI output must contain exactly the five matching factors.")
    reason = data.get("reason")
    evidence = data.get("evidence_summary")
    if not isinstance(reason, str) or not reason.strip():
        raise AIWeightValidationError("AI output is missing a reason.")
    if not isinstance(evidence, str) or not evidence.strip():
        raise AIWeightValidationError("AI output is missing an evidence summary.")
    return JudgeResult(decision, proposed, reason.strip(), evidence.strip())


def validate_proposed_weights(current_weights, proposed_weights):
    """Deterministically validate AI-proposed weights. Never silently clamp large changes."""
    if not isinstance(proposed_weights, dict) or set(proposed_weights.keys()) != set(FACTOR_KEYS):
        raise AIWeightValidationError("Proposed weights must contain exactly the five matching factors.")

    clean = {}
    for key in FACTOR_KEYS:
        value = proposed_weights[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AIWeightValidationError(f"{key} must be numeric.")
        value = float(value)
        if not math.isfinite(value):
            raise AIWeightValidationError(f"{key} must be finite.")
        if value < MIN_WEIGHT - 1e-9 or value > MAX_WEIGHT + 1e-9:
            raise AIWeightValidationError(f"{key} is outside the allowed 5%–50% range.")
        if abs(value - float(current_weights[key])) > MAX_CHANGE + 1e-9:
            raise AIWeightValidationError(f"{key} changes by more than 5 percentage points.")
        clean[key] = value

    total = sum(clean.values())
    drift = 1.0 - total
    if abs(drift) > TOTAL_TOLERANCE:
        raise AIWeightValidationError("Proposed weights do not sum to 1.0.")

    # Only normalize tiny rounding drift, and re-check all constraints afterward.
    if abs(drift) > 1e-12:
        anchor = max(FACTOR_KEYS, key=lambda key: clean[key])
        normalized = dict(clean)
        normalized[anchor] += drift
        if normalized[anchor] < MIN_WEIGHT - 1e-9 or normalized[anchor] > MAX_WEIGHT + 1e-9:
            raise AIWeightValidationError("Rounding normalization would violate factor bounds.")
        if abs(normalized[anchor] - float(current_weights[anchor])) > MAX_CHANGE + 1e-9:
            raise AIWeightValidationError("Rounding normalization would violate maximum-change limits.")
        clean = normalized

    return {key: round(clean[key], 6) for key in FACTOR_KEYS}
