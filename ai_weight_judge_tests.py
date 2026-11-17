import json
import os
import tempfile
from pathlib import Path

import db
import learning
import matching
from ai_weight_judge import AIWeightValidationError, JudgeResult, validate_proposed_weights

PASS = 0
TOTAL = 0


def check(name, condition, detail=""):
    global PASS, TOTAL
    TOTAL += 1
    if condition:
        PASS += 1
        print(f"PASS | {name} | {detail}")
    else:
        print(f"FAIL | {name} | {detail}")
        raise AssertionError(name)


def setup_fixture():
    conn = db.get_db()
    owner = conn.execute(
        """INSERT INTO users(name, university, email, password_hash, skills, availability,
                              preferred_role, working_style, project_goal)
           VALUES ('Owner','Korea University','owner@test','x','Coding,Data analysis','Weekday evenings',
                   'Data / Coding','Structured and planned','High quality / ambitious') RETURNING id"""
    ).fetchone()["id"]
    user = conn.execute(
        """INSERT INTO users(name, university, email, password_hash, skills, availability,
                              preferred_role, working_style, project_goal)
           VALUES ('Joiner','Korea University','joiner@test','x','Coding,Data analysis','Weekday evenings',
                   'Data / Coding','Structured and planned','High quality / ambitious') RETURNING id"""
    ).fetchone()["id"]
    comp = conn.execute("INSERT INTO competitions(name) VALUES ('Demo') RETURNING id").fetchone()["id"]
    team = conn.execute(
        """INSERT INTO teams(competition_id, owner_id, title, needed_skills, needed_role, availability,
                              working_style, project_goal, members_needed)
           VALUES (:competition_id,:owner_id,'T','Coding,Data analysis','Data / Coding','Weekday evenings',
                   'Structured and planned','High quality / ambitious',2) RETURNING id""",
        {"competition_id": comp, "owner_id": owner},
    ).fetchone()["id"]
    conn.commit(); conn.close()
    return user, team


def add_rejects(user, team, reason, count=5, learn=True):
    weights = matching.get_active_weights()
    factors = {"skills":1.0,"availability":1.0,"preferred_role":1.0,"working_style":1.0,"project_goal":1.0}
    for _ in range(count):
        learning.save_feedback(user, team, "Reject", reason, "", 100, factors, weights, learn)


def with_db(test_fn):
    with tempfile.TemporaryDirectory() as td:
        old_path = db.DB_PATH
        old_url = os.environ.pop("DATABASE_URL", None)
        db.DB_PATH = Path(td) / "aiwj.db"
        db.reset_engine_for_tests()
        try:
            db.init_db()
            test_fn()
        finally:
            db.DB_PATH = old_path
            db.reset_engine_for_tests()
            if old_url is not None:
                os.environ["DATABASE_URL"] = old_url


def availability_test():
    user, team = setup_fixture()
    add_rejects(user, team, "Availability", 5)
    add_rejects(user, team, "Skill fit", 1, learn=False)
    before = matching.get_active_weights()
    fake = lambda payload: JudgeResult(
        "propose_change",
        {"skills":0.33,"availability":0.25,"preferred_role":0.19,"working_style":0.09,"project_goal":0.14},
        "Availability is the dominant repeated rejection reason, so a moderate increase is justified.",
        "5 of 5 eligible rejections were related to availability.",
    )
    result = learning.generate_proposal(judge_fn=fake)
    check("Availability-dominant creates Pending AI proposal", result["status"] == "proposal_created", str(result["status"]))
    proposal = result["proposal"]
    check("Proposal source is AI", proposal["proposal_source"] == "AI", proposal["proposal_source"])
    check("No automatic activation", matching.get_active_weights() == before, str(matching.get_active_weights()))
    check("Evidence excludes opted-out feedback", proposal["eligible_feedback_count"] == 5, str(proposal["eligible_feedback_count"]))
    check("Proposal remains Pending", proposal["status"] == "Pending", proposal["status"])
    # Same batch cannot create another proposal while pending.
    again = learning.generate_proposal(judge_fn=fake)
    check("Same batch does not generate repeated proposal", again["status"] == "pending_exists", again["status"])
    learning.review_proposal(proposal["id"], "Approved")
    after = matching.get_active_weights()
    check("Human approval activates weights", abs(after["availability"] - 0.25) < 1e-9, str(after))


def weak_evidence_test():
    user, team = setup_fixture()
    add_rejects(user, team, "Availability", 2)
    add_rejects(user, team, "Skill fit", 2)
    called = {"n":0}
    def fake(_):
        called["n"] += 1
        return JudgeResult("insufficient_evidence", matching.get_active_weights(), "Weak evidence.", "Mixed feedback.")
    result = learning.generate_proposal(judge_fn=fake)
    check("Weak evidence does not call AI before threshold", result["status"] == "insufficient_trigger", result["status"])
    check("Weak evidence creates no proposal", called["n"] == 0, str(called["n"]))


def insufficient_ai_test():
    user, team = setup_fixture()
    add_rejects(user, team, "Availability", 5)
    current = matching.get_active_weights()
    fake = lambda payload: JudgeResult("insufficient_evidence", current, "Evidence is not strong enough.", "5 rejects exist but the pattern is not reliable enough.")
    result = learning.generate_proposal(judge_fn=fake)
    check("AI insufficient-evidence is valid", result["status"] == "insufficient_evidence", result["status"])
    conn = db.get_db()
    pcount = conn.execute("SELECT COUNT(*) AS n FROM weight_proposals").fetchone()["n"]
    rcount = conn.execute("SELECT COUNT(*) AS n FROM ai_weight_judge_runs").fetchone()["n"]
    conn.close()
    check("Insufficient evidence creates no actionable proposal", pcount == 0, str(pcount))
    check("Insufficient evidence is audited", rcount == 1, str(rcount))


def invalid_output_test():
    user, team = setup_fixture()
    add_rejects(user, team, "Availability", 5)
    before = matching.get_active_weights()
    fake = lambda payload: JudgeResult(
        "propose_change",
        {"skills":0.20,"availability":0.35,"preferred_role":0.20,"working_style":0.10,"project_goal":0.15},
        "Too large.", "Availability rejects dominate.",
    )
    result = learning.generate_proposal(judge_fn=fake)
    check("Invalid >5pp AI change is rejected", result["status"] == "ai_error", result["message"])
    conn = db.get_db()
    pcount = conn.execute("SELECT COUNT(*) AS n FROM weight_proposals").fetchone()["n"]
    failed = conn.execute("SELECT COUNT(*) AS n FROM ai_weight_judge_runs WHERE status='Failed'").fetchone()["n"]
    conn.close()
    check("Invalid output creates no Pending proposal", pcount == 0, str(pcount))
    check("Invalid output failure is audited", failed == 1, str(failed))
    check("Invalid output leaves active weights unchanged", matching.get_active_weights() == before, str(before))


def reject_test():
    user, team = setup_fixture()
    add_rejects(user, team, "Availability", 5)
    before = matching.get_active_weights()
    fake = lambda payload: JudgeResult(
        "propose_change",
        {"skills":0.33,"availability":0.25,"preferred_role":0.19,"working_style":0.09,"project_goal":0.14},
        "Moderate change.", "5 of 5 rejections were availability-related.",
    )
    result = learning.generate_proposal(judge_fn=fake)
    learning.review_proposal(result["proposal"]["id"], "Rejected")
    check("Human rejection leaves weights unchanged", matching.get_active_weights() == before, str(before))
    conn=db.get_db(); row=conn.execute("SELECT status FROM weight_proposals WHERE id=:id", {"id":result["proposal"]["id"]}).fetchone(); conn.close()
    check("Rejected proposal stays in history", row["status"] == "Rejected", row["status"])


def validator_test():
    current={"skills":0.35,"availability":0.20,"preferred_role":0.20,"working_style":0.10,"project_goal":0.15}
    try:
        validate_proposed_weights(current, {"skills":0.8,"availability":0.3,"preferred_role":0.2,"working_style":0.1,"project_goal":0.1})
        ok=False
    except AIWeightValidationError:
        ok=True
    check("Validator rejects impossible totals/ranges", ok)


for fn in [availability_test, weak_evidence_test, insufficient_ai_test, invalid_output_test, reject_test, validator_test]:
    with_db(fn)

print(f"AI_WEIGHT_JUDGE {PASS}/{TOTAL} PASS")
