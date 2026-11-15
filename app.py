import hmac
import json
import os
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from functools import wraps

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db, init_db
from guardrails import SCOPE_MESSAGE, is_out_of_scope_search
from university import filter_applicants_same_university, filter_teams_same_university
from learning import (
    REASONS,
    add_demo_feedback,
    feedback_summary,
    generate_proposal,
    review_proposal,
    save_feedback,
)
from matching import compatibility, factor_breakdown, get_active_weights

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production" or bool(os.getenv("RAILWAY_ENVIRONMENT"))
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if IS_PRODUCTION and not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in production.")

app = Flask(__name__)
app.secret_key = SECRET_KEY or "dev-only-secret-change-before-production"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
)

SKILLS = ["Research", "Coding", "Data analysis", "Design", "Presentation", "Writing", "Project management"]
AVAILABILITY = ["Weekday daytime", "Weekday evenings", "Weekends", "Flexible / Negotiable"]
ROLES = ["Research", "Data / Coding", "Design", "Presentation", "Project management", "Flexible"]
WORKING_STYLES = ["Structured and planned", "Flexible and adaptive", "Fast-paced", "Discussion-oriented"]
PROJECT_GOALS = ["High quality / ambitious", "Balanced effort", "Minimum viable effort"]
KOREA_TZ = ZoneInfo("Asia/Seoul")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = :user_id",
        {"user_id": session["user_id"]},
    ).fetchone()
    conn.close()
    return user


def is_admin_user(user=None):
    user = user or current_user()
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    return bool(user and admin_email and user["email"].strip().lower() == admin_email)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        if not is_admin_user():
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def csrf_protect():
    if request.method == "POST":
        expected = session.get("_csrf_token", "")
        supplied = request.form.get("_csrf_token", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            abort(400, description="Invalid or missing CSRF token.")


@app.context_processor
def inject_user():
    user = current_user()
    return {
        "logged_in_user": user,
        "is_admin": is_admin_user(user),
        "show_demo_credentials": not IS_PRODUCTION,
    }


@app.route("/")
def index():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))


@app.route("/healthz")
def healthz():
    try:
        conn = get_db()
        ok = conn.execute("SELECT 1 AS ok").fetchone()
        conn.close()
        if not ok or ok["ok"] != 1:
            raise RuntimeError("database health check failed")
        return jsonify(status="ok"), 200
    except Exception:
        return jsonify(status="unhealthy"), 503


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        university = request.form.get("university", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        skills = request.form.getlist("skills")
        availability = request.form.get("availability", "")
        preferred_role = request.form.get("preferred_role", "")
        working_style = request.form.get("working_style", "")
        project_goal = request.form.get("project_goal", "")

        if not all([name, university, email, password, skills, availability, preferred_role, working_style, project_goal]):
            flash("Please complete all required fields.")
            return render_template(
                "signup.html", skills=SKILLS, availability=AVAILABILITY,
                roles=ROLES, styles=WORKING_STYLES, goals=PROJECT_GOALS,
            )
        if len(password) < 6:
            flash("Password must be at least 6 characters for this MVP.")
            return render_template(
                "signup.html", skills=SKILLS, availability=AVAILABILITY,
                roles=ROLES, styles=WORKING_STYLES, goals=PROJECT_GOALS,
            )

        conn = get_db()
        try:
            row = conn.execute(
                """INSERT INTO users(name, university, email, password_hash, skills, availability,
                                      preferred_role, working_style, project_goal)
                   VALUES (:name, :university, :email, :password_hash, :skills, :availability,
                           :preferred_role, :working_style, :project_goal)
                   RETURNING id""",
                {
                    "name": name,
                    "university": university,
                    "email": email,
                    "password_hash": generate_password_hash(password),
                    "skills": ",".join(skills),
                    "availability": availability,
                    "preferred_role": preferred_role,
                    "working_style": working_style,
                    "project_goal": project_goal,
                },
            ).fetchone()
            conn.commit()
            user_id = row["id"]
        except IntegrityError:
            conn.rollback()
            conn.close()
            flash("An account with this email already exists.")
            return redirect(url_for("signup"))
        conn.close()

        session["user_id"] = user_id
        flash("Account and matching profile created.")
        return redirect(url_for("dashboard"))

    return render_template(
        "signup.html", skills=SKILLS, availability=AVAILABILITY,
        roles=ROLES, styles=WORKING_STYLES, goals=PROJECT_GOALS,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = :email",
            {"email": email},
        ).fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        csrf_token()
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    my_teams = conn.execute(
        """SELECT teams.*, competitions.name AS competition_name
           FROM teams JOIN competitions ON competitions.id = teams.competition_id
           WHERE teams.owner_id = :owner_id ORDER BY teams.created_at DESC""",
        {"owner_id": session["user_id"]},
    ).fetchall()
    applications = conn.execute(
        """SELECT applications.*, teams.title AS team_title
           FROM applications JOIN teams ON teams.id = applications.team_id
           WHERE applications.user_id = :user_id ORDER BY applications.created_at DESC""",
        {"user_id": session["user_id"]},
    ).fetchall()
    conn.close()
    return render_template("dashboard.html", my_teams=my_teams, applications=applications)


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user())


@app.post("/feedback-preference")
@login_required
def feedback_preference():
    enabled = request.form.get("feedback_opt_in") == "on"
    conn = get_db()
    conn.execute(
        "UPDATE users SET feedback_opt_in = :enabled WHERE id = :user_id",
        {"enabled": enabled, "user_id": session["user_id"]},
    )
    conn.commit()
    conn.close()
    flash("Feedback learning preference updated.")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/competitions")
@login_required
def competitions():
    mode = request.args.get("mode", "join")
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "active").strip().lower()
    deadline_filter = request.args.get("deadline", "").strip().lower()

    if q and is_out_of_scope_search(q):
        return render_template(
            "competitions.html", competitions=[], mode=mode, q=q, category=category,
            status=status, deadline_filter=deadline_filter, categories=[],
            scope_message=SCOPE_MESSAGE, last_updated=None,
        )

    clauses = []
    params = {}
    if q:
        clauses.append(
            "(LOWER(name) LIKE :pattern OR LOWER(COALESCE(organizer, '')) LIKE :pattern "
            "OR LOWER(COALESCE(description, '')) LIKE :pattern OR LOWER(COALESCE(category, '')) LIKE :pattern)"
        )
        params["pattern"] = f"%{q.lower()}%"
    if category:
        clauses.append("category = :category")
        params["category"] = category
    # Seed/demo rows remain useful locally but are not presented as current production data.
    if IS_PRODUCTION:
        clauses.append("source_name IS NOT NULL AND source_name <> 'Demo'")
    if status == "active":
        clauses.append("is_active = :active")
        params["active"] = True
    elif status == "expired":
        clauses.append("is_active = :inactive")
        params["inactive"] = False
    if deadline_filter == "soon":
        clauses.append("deadline_date IS NOT NULL AND deadline_date >= :today AND deadline_date <= :soon")
        korea_today = datetime.now(KOREA_TZ).date()
        params["today"] = korea_today
        params["soon"] = korea_today + timedelta(days=14)

    where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM competitions" + where_sql +
        " ORDER BY CASE WHEN deadline_date IS NULL THEN 1 ELSE 0 END, deadline_date ASC, name ASC",
        params,
    ).fetchall()
    category_sql = """SELECT DISTINCT category FROM competitions
                      WHERE category IS NOT NULL AND category <> '' AND is_active = :active"""
    if IS_PRODUCTION:
        category_sql += " AND source_name IS NOT NULL AND source_name <> 'Demo'"
    category_sql += " ORDER BY category"
    categories = conn.execute(category_sql, {"active": True}).fetchall()
    freshness = conn.execute(
        "SELECT MAX(fetched_at) AS last_updated FROM competitions WHERE source_name IS NOT NULL AND source_name <> 'Demo'"
    ).fetchone()
    conn.close()

    enriched = []
    today = datetime.now(KOREA_TZ).date()
    for row in rows:
        deadline_date = row.get("deadline_date")
        if deadline_date:
            days = (deadline_date - today).days
            if days < 0:
                dday = "Closed"
            elif days == 0:
                dday = "D-Day"
            else:
                dday = f"D-{days}"
        else:
            dday = None
        enriched.append({"competition": row, "dday": dday})

    return render_template(
        "competitions.html", competitions=enriched, mode=mode, q=q, category=category,
        status=status, deadline_filter=deadline_filter,
        categories=[item["category"] for item in categories],
        scope_message=None, last_updated=freshness["last_updated"] if freshness else None,
    )


@app.route("/competition/<int:competition_id>/teams")
@login_required
def competition_teams(competition_id):
    user = current_user()
    conn = get_db()
    competition = conn.execute(
        "SELECT * FROM competitions WHERE id = :competition_id",
        {"competition_id": competition_id},
    ).fetchone()
    if not competition:
        conn.close()
        abort(404)

    same_university_only = request.args.get("same_university") == "1"
    teams = conn.execute(
        """SELECT teams.*, users.name AS owner_name, users.university AS owner_university
           FROM teams JOIN users ON users.id = teams.owner_id
           WHERE teams.competition_id = :competition_id AND teams.owner_id != :user_id
           ORDER BY teams.created_at DESC""",
        {"competition_id": competition_id, "user_id": user["id"]},
    ).fetchall()
    if same_university_only:
        teams = filter_teams_same_university(user["university"], teams)

    weights = get_active_weights(conn)
    enriched = []
    for team in teams:
        score, reasons, factors = compatibility(user, team, weights)
        applied = conn.execute(
            "SELECT status FROM applications WHERE team_id = :team_id AND user_id = :user_id",
            {"team_id": team["id"], "user_id": user["id"]},
        ).fetchone()
        shortlisted = conn.execute(
            "SELECT 1 AS present FROM shortlists WHERE team_id = :team_id AND user_id = :user_id",
            {"team_id": team["id"], "user_id": user["id"]},
        ).fetchone()
        enriched.append({
            "team": team,
            "score": score,
            "reasons": reasons,
            "factors": factors,
            "factor_breakdown": factor_breakdown(factors),
            "application_status": applied["status"] if applied else None,
            "shortlisted": bool(shortlisted),
        })
    enriched.sort(key=lambda x: x["score"], reverse=True)
    conn.close()
    return render_template(
        "teams.html", competition=competition, matches=enriched,
        feedback_reasons=REASONS, active_weights=weights,
        same_university_only=same_university_only,
    )


@app.post("/recommendation/<int:team_id>/feedback")
@login_required
def recommendation_feedback(team_id):
    decision = request.form.get("decision", "")
    reason = request.form.get("reason", "")
    comment = request.form.get("comment", "").strip()
    if decision not in {"Accept", "Reject"} or reason not in REASONS + [""]:
        abort(400)

    user = current_user()
    conn = get_db()
    team = conn.execute(
        "SELECT * FROM teams WHERE id = :team_id",
        {"team_id": team_id},
    ).fetchone()
    if not team:
        conn.close()
        abort(404)
    if team["owner_id"] == user["id"]:
        conn.close()
        abort(403)

    weights = get_active_weights(conn)
    score, _, factors = compatibility(user, team, weights)
    conn.close()
    save_feedback(
        user["id"], team_id, decision, reason, comment, score, factors, weights,
        bool(user["feedback_opt_in"]),
    )
    flash("Recommendation feedback saved.")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/competition/<int:competition_id>/recruit", methods=["GET", "POST"])
@login_required
def recruit(competition_id):
    conn = get_db()
    competition = conn.execute(
        "SELECT * FROM competitions WHERE id = :competition_id",
        {"competition_id": competition_id},
    ).fetchone()
    if not competition:
        conn.close()
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        needed_skills = request.form.getlist("needed_skills")
        needed_role = request.form.get("needed_role", "")
        availability = request.form.get("availability", "")
        working_style = request.form.get("working_style", "")
        project_goal = request.form.get("project_goal", "")
        members_needed = request.form.get("members_needed", type=int)
        if not all([title, needed_skills, needed_role, availability, working_style, project_goal, members_needed]):
            conn.close()
            flash("Please complete all required fields.")
            return redirect(url_for("recruit", competition_id=competition_id))

        row = conn.execute(
            """INSERT INTO teams(competition_id, owner_id, title, description, needed_skills,
                                  needed_role, availability, working_style, project_goal, members_needed)
               VALUES (:competition_id, :owner_id, :title, :description, :needed_skills,
                       :needed_role, :availability, :working_style, :project_goal, :members_needed)
               RETURNING id""",
            {
                "competition_id": competition_id,
                "owner_id": session["user_id"],
                "title": title,
                "description": description,
                "needed_skills": ",".join(needed_skills),
                "needed_role": needed_role,
                "availability": availability,
                "working_style": working_style,
                "project_goal": project_goal,
                "members_needed": members_needed,
            },
        ).fetchone()
        conn.commit()
        team_id = row["id"]
        conn.close()
        flash("Recruiting post created.")
        return redirect(url_for("team_applicants", team_id=team_id))

    conn.close()
    return render_template(
        "recruit.html", competition=competition, skills=SKILLS,
        availability=AVAILABILITY, roles=ROLES,
        styles=WORKING_STYLES, goals=PROJECT_GOALS,
    )


@app.post("/team/<int:team_id>/apply")
@login_required
def apply_team(team_id):
    conn = get_db()
    team = conn.execute(
        "SELECT * FROM teams WHERE id = :team_id",
        {"team_id": team_id},
    ).fetchone()
    if not team:
        conn.close()
        abort(404)
    if team["owner_id"] == session["user_id"]:
        conn.close()
        flash("You cannot apply to your own team.")
        return redirect(url_for("competition_teams", competition_id=team["competition_id"]))

    try:
        conn.execute(
            "INSERT INTO applications(team_id, user_id) VALUES (:team_id, :user_id)",
            {"team_id": team_id, "user_id": session["user_id"]},
        )
        conn.commit()
        flash("Application submitted.")
    except IntegrityError:
        conn.rollback()
        flash("You already applied to this team.")
    conn.close()
    return redirect(url_for("competition_teams", competition_id=team["competition_id"]))


@app.post("/team/<int:team_id>/shortlist")
@login_required
def shortlist_team(team_id):
    conn = get_db()
    team = conn.execute(
        "SELECT * FROM teams WHERE id = :team_id",
        {"team_id": team_id},
    ).fetchone()
    if not team:
        conn.close()
        abort(404)
    existing = conn.execute(
        "SELECT id FROM shortlists WHERE user_id = :user_id AND team_id = :team_id",
        {"user_id": session["user_id"], "team_id": team_id},
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM shortlists WHERE id = :id", {"id": existing["id"]})
        flash("Removed from shortlist.")
    else:
        conn.execute(
            "INSERT INTO shortlists(user_id, team_id) VALUES (:user_id, :team_id)",
            {"user_id": session["user_id"], "team_id": team_id},
        )
        flash("Added to shortlist.")
    conn.commit()
    conn.close()
    return redirect(url_for("competition_teams", competition_id=team["competition_id"]))


@app.route("/team/<int:team_id>/applicants")
@login_required
def team_applicants(team_id):
    owner = current_user()
    conn = get_db()
    team = conn.execute(
        """SELECT teams.*, competitions.name AS competition_name
           FROM teams JOIN competitions ON competitions.id = teams.competition_id
           WHERE teams.id = :team_id""",
        {"team_id": team_id},
    ).fetchone()
    if not team:
        conn.close()
        abort(404)
    if team["owner_id"] != owner["id"]:
        conn.close()
        abort(403)

    same_university_only = request.args.get("same_university") == "1"
    applicants = conn.execute(
        """SELECT applications.id AS application_id, applications.status, users.*
           FROM applications JOIN users ON users.id = applications.user_id
           WHERE applications.team_id = :team_id ORDER BY applications.created_at DESC""",
        {"team_id": team_id},
    ).fetchall()
    if same_university_only:
        applicants = filter_applicants_same_university(owner["university"], applicants)

    weights = get_active_weights(conn)
    enriched = []
    for applicant in applicants:
        score, reasons, factors = compatibility(applicant, team, weights)
        enriched.append({
            "applicant": applicant,
            "score": score,
            "reasons": reasons,
            "factors": factors,
            "factor_breakdown": factor_breakdown(factors),
        })
    enriched.sort(key=lambda x: x["score"], reverse=True)
    conn.close()
    return render_template("applicants.html", team=team, applicants=enriched, same_university_only=same_university_only)


@app.post("/application/<int:application_id>/<status>")
@login_required
def update_application(application_id, status):
    if status not in {"Accepted", "Rejected"}:
        abort(400)
    conn = get_db()
    app_row = conn.execute(
        """SELECT applications.*, teams.owner_id, teams.id AS team_id
           FROM applications JOIN teams ON teams.id = applications.team_id
           WHERE applications.id = :application_id""",
        {"application_id": application_id},
    ).fetchone()
    if not app_row:
        conn.close()
        abort(404)
    if app_row["owner_id"] != session["user_id"]:
        conn.close()
        abort(403)
    conn.execute(
        "UPDATE applications SET status = :status WHERE id = :application_id",
        {"status": status, "application_id": application_id},
    )
    conn.commit()
    team_id = app_row["team_id"]
    conn.close()
    flash(f"Application {status.lower()}.")
    return redirect(url_for("team_applicants", team_id=team_id))


@app.route("/learning")
@admin_required
def learning_dashboard():
    summary = feedback_summary()
    conn = get_db()
    proposals = conn.execute("SELECT * FROM weight_proposals ORDER BY id DESC LIMIT 10").fetchall()
    history = conn.execute("SELECT * FROM weight_history ORDER BY id DESC LIMIT 10").fetchall()
    demo_team = conn.execute("SELECT * FROM teams ORDER BY id LIMIT 1").fetchone()
    conn.close()
    active = get_active_weights()

    parsed = [
        {"row": p, "old": json.loads(p["old_weights_json"]), "new": json.loads(p["proposed_weights_json"])}
        for p in proposals
    ]
    parsed_history = [
        {"row": h, "old": json.loads(h["old_weights_json"]), "new": json.loads(h["new_weights_json"])}
        for h in history
    ]
    return render_template(
        "learning.html", summary=summary, active_weights=active,
        proposals=parsed, history=parsed_history, demo_team=demo_team,
        demo_feedback_enabled=(not IS_PRODUCTION or os.getenv("ENABLE_DEMO_FEEDBACK", "").lower() == "true"),
    )


@app.post("/learning/generate-proposal")
@admin_required
def learning_generate_proposal():
    proposal = generate_proposal()
    flash(
        "Proposal ready for human review."
        if proposal
        else "Not enough repeated rejection evidence yet. A factor needs at least 5 learning-eligible rejections."
    )
    return redirect(url_for("learning_dashboard"))


@app.post("/learning/proposal/<int:proposal_id>/<action>")
@admin_required
def learning_review(proposal_id, action):
    mapping = {"approve": "Approved", "reject": "Rejected"}
    if action not in mapping:
        abort(400)
    ok = review_proposal(proposal_id, mapping[action])
    flash("Proposal reviewed." if ok else "Proposal could not be reviewed.")
    return redirect(url_for("learning_dashboard"))


@app.post("/learning/demo-feedback")
@admin_required
def learning_demo_feedback():
    enabled = not IS_PRODUCTION or os.getenv("ENABLE_DEMO_FEEDBACK", "").lower() == "true"
    if not enabled:
        abort(403)

    conn = get_db()
    team = conn.execute("SELECT * FROM teams ORDER BY id LIMIT 1").fetchone()
    user = current_user()
    if not team:
        conn.close()
        flash("Create a team first to attach demo feedback.")
        return redirect(url_for("learning_dashboard"))
    weights = get_active_weights(conn)
    score, _, factors = compatibility(user, team, weights)
    conn.close()
    add_demo_feedback(user["id"], team["id"], score, factors, weights)
    flash("Added clearly labelled demo feedback.")
    return redirect(url_for("learning_dashboard"))


if __name__ == "__main__":
    # Local convenience only. Railway runs init_db.py as a pre-deploy command.
    init_db()
    app.run(debug=not IS_PRODUCTION, host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
