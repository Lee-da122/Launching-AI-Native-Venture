
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pathlib import Path
import sqlite3

app = Flask(__name__)
app.secret_key = "change-this-before-production"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "teammatch.db"

SKILLS = [
    "Research", "Coding", "Data analysis", "Design",
    "Presentation", "Writing", "Project management"
]
AVAILABILITY = [
    "Weekday daytime", "Weekday evenings", "Weekends",
    "Flexible / Negotiable"
]
ROLES = [
    "Research", "Data / Coding", "Design",
    "Presentation", "Project management", "Flexible"
]
WORKING_STYLES = [
    "Structured and planned", "Flexible and adaptive",
    "Fast-paced", "Discussion-oriented"
]
PROJECT_GOALS = [
    "High quality / ambitious",
    "Balanced effort",
    "Minimum viable effort"
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            university TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            skills TEXT NOT NULL,
            availability TEXT NOT NULL,
            preferred_role TEXT NOT NULL,
            working_style TEXT NOT NULL,
            project_goal TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS competitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            organizer TEXT,
            deadline TEXT,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            needed_skills TEXT NOT NULL,
            needed_role TEXT NOT NULL,
            availability TEXT NOT NULL,
            working_style TEXT NOT NULL,
            project_goal TEXT NOT NULL,
            members_needed INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (competition_id) REFERENCES competitions(id),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(team_id, user_id),
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS shortlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, team_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );
        """
    )
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()

    competition_count = conn.execute("SELECT COUNT(*) FROM competitions").fetchone()[0]
    if competition_count == 0:
        competitions = [
            (
                "AI for Social Impact Challenge",
                "University Innovation Hub",
                "2026-11-20",
                "Build an AI-enabled idea that addresses a social or community problem."
            ),
            (
                "Campus Sustainability Challenge",
                "Student Entrepreneurship Center",
                "2026-12-05",
                "Develop a practical solution for a more sustainable university or city."
            ),
            (
                "Smart Mobility Case Competition",
                "Mobility Lab",
                "2027-01-18",
                "Design a data-driven solution for urban mobility and transportation."
            ),
            (
                "Digital Health Innovation Sprint",
                "HealthTech Society",
                "2027-02-10",
                "Create a student-led digital health concept with measurable user value."
            ),
        ]
        conn.executemany(
            """
            INSERT INTO competitions(name, organizer, deadline, description)
            VALUES (?, ?, ?, ?)
            """,
            competitions,
        )
        conn.commit()

    demo = conn.execute("SELECT id FROM users WHERE email = ?", ("demo.recruiter@university.edu",)).fetchone()
    if not demo:
        cursor = conn.execute(
            """
            INSERT INTO users(
                name, university, email, password_hash, skills,
                availability, preferred_role, working_style, project_goal
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Demo Recruiter",
                "Demo University",
                "demo.recruiter@university.edu",
                generate_password_hash("demo1234"),
                "Project management,Presentation,Research",
                "Weekday evenings",
                "Project management",
                "Structured and planned",
                "High quality / ambitious",
            ),
        )
        owner_id = cursor.lastrowid

        competition_ids = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM competitions").fetchall()
        }

        teams = [
            (
                competition_ids["AI for Social Impact Challenge"],
                owner_id,
                "EqualWork AI",
                "Looking for teammates to prototype an AI tool for fairer student collaboration.",
                "Coding,Design",
                "Data / Coding",
                "Weekday evenings",
                "Structured and planned",
                "High quality / ambitious",
                2,
            ),
            (
                competition_ids["Campus Sustainability Challenge"],
                owner_id,
                "Green Campus Crew",
                "A team exploring waste reduction and student behavior change on campus.",
                "Research,Presentation",
                "Research",
                "Flexible / Negotiable",
                "Discussion-oriented",
                "Balanced effort",
                2,
            ),
            (
                competition_ids["Smart Mobility Case Competition"],
                owner_id,
                "MoveSmart",
                "We need one more member for mobility data analysis and final presentation.",
                "Data analysis,Presentation",
                "Data / Coding",
                "Weekends",
                "Fast-paced",
                "High quality / ambitious",
                1,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO teams(
                competition_id, owner_id, title, description, needed_skills,
                needed_role, availability, working_style, project_goal, members_needed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            teams,
        )
        conn.commit()

    conn.close()


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
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return user


def split_values(text):
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def compatibility(user, team):
    score = 0
    reasons = []

    user_skills = set(split_values(user["skills"]))
    needed_skills = set(split_values(team["needed_skills"]))
    matched_skills = sorted(user_skills & needed_skills)

    if needed_skills:
        skill_points = int(35 * len(matched_skills) / len(needed_skills))
        score += skill_points
    if matched_skills:
        reasons.append("Skill fit: " + ", ".join(matched_skills))

    if (
        user["availability"] == team["availability"]
        or user["availability"] == "Flexible / Negotiable"
        or team["availability"] == "Flexible / Negotiable"
    ):
        score += 20
        reasons.append("Availability is compatible")

    if (
        user["preferred_role"] == team["needed_role"]
        or user["preferred_role"] == "Flexible"
        or team["needed_role"] == "Flexible"
    ):
        score += 20
        reasons.append("Preferred role fits the team's need")

    if user["working_style"] == team["working_style"]:
        score += 10
        reasons.append("Working styles match")

    if user["project_goal"] == team["project_goal"]:
        score += 15
        reasons.append("Project effort goals are aligned")

    if not reasons:
        reasons.append("Some profile criteria differ; review the team details before deciding")

    return min(score, 100), reasons


@app.context_processor
def inject_user():
    return {"logged_in_user": current_user()}


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


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
                "signup.html",
                skills=SKILLS,
                availability=AVAILABILITY,
                roles=ROLES,
                styles=WORKING_STYLES,
                goals=PROJECT_GOALS,
            )

        if len(password) < 6:
            flash("Password must be at least 6 characters for this MVP.")
            return render_template(
                "signup.html",
                skills=SKILLS,
                availability=AVAILABILITY,
                roles=ROLES,
                styles=WORKING_STYLES,
                goals=PROJECT_GOALS,
            )

        conn = get_db()
        try:
            cursor = conn.execute(
                """
                INSERT INTO users(
                    name, university, email, password_hash, skills,
                    availability, preferred_role, working_style, project_goal
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    university,
                    email,
                    generate_password_hash(password),
                    ",".join(skills),
                    availability,
                    preferred_role,
                    working_style,
                    project_goal,
                ),
            )
            conn.commit()
            user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            conn.close()
            flash("An account with this email already exists.")
            return redirect(url_for("signup"))

        conn.close()
        session["user_id"] = user_id
        flash("Account and matching profile created.")
        return redirect(url_for("dashboard"))

    return render_template(
        "signup.html",
        skills=SKILLS,
        availability=AVAILABILITY,
        roles=ROLES,
        styles=WORKING_STYLES,
        goals=PROJECT_GOALS,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
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
        """
        SELECT teams.*, competitions.name AS competition_name
        FROM teams
        JOIN competitions ON competitions.id = teams.competition_id
        WHERE teams.owner_id = ?
        ORDER BY teams.created_at DESC
        """,
        (session["user_id"],),
    ).fetchall()
    applications = conn.execute(
        """
        SELECT applications.*, teams.title AS team_title
        FROM applications
        JOIN teams ON teams.id = applications.team_id
        WHERE applications.user_id = ?
        ORDER BY applications.created_at DESC
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("dashboard.html", my_teams=my_teams, applications=applications)


@app.route("/competitions")
@login_required
def competitions():
    mode = request.args.get("mode", "join")
    q = request.args.get("q", "").strip()

    conn = get_db()
    if q:
        rows = conn.execute(
            """
            SELECT * FROM competitions
            WHERE name LIKE ? OR organizer LIKE ? OR description LIKE ?
            ORDER BY deadline
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM competitions ORDER BY deadline").fetchall()
    conn.close()

    return render_template("competitions.html", competitions=rows, mode=mode, q=q)


@app.route("/competition/<int:competition_id>/teams")
@login_required
def competition_teams(competition_id):
    user = current_user()
    conn = get_db()
    competition = conn.execute(
        "SELECT * FROM competitions WHERE id = ?", (competition_id,)
    ).fetchone()
    if not competition:
        conn.close()
        abort(404)

    teams = conn.execute(
        """
        SELECT teams.*, users.name AS owner_name
        FROM teams
        JOIN users ON users.id = teams.owner_id
        WHERE teams.competition_id = ? AND teams.owner_id != ?
        ORDER BY teams.created_at DESC
        """,
        (competition_id, user["id"]),
    ).fetchall()

    enriched = []
    for team in teams:
        score, reasons = compatibility(user, team)
        applied = conn.execute(
            "SELECT status FROM applications WHERE team_id = ? AND user_id = ?",
            (team["id"], user["id"]),
        ).fetchone()
        shortlisted = conn.execute(
            "SELECT 1 FROM shortlists WHERE team_id = ? AND user_id = ?",
            (team["id"], user["id"]),
        ).fetchone()
        enriched.append(
            {
                "team": team,
                "score": score,
                "reasons": reasons,
                "application_status": applied["status"] if applied else None,
                "shortlisted": bool(shortlisted),
            }
        )

    enriched.sort(key=lambda x: x["score"], reverse=True)
    conn.close()
    return render_template("teams.html", competition=competition, matches=enriched)


@app.route("/competition/<int:competition_id>/recruit", methods=["GET", "POST"])
@login_required
def recruit(competition_id):
    conn = get_db()
    competition = conn.execute(
        "SELECT * FROM competitions WHERE id = ?", (competition_id,)
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

        cursor = conn.execute(
            """
            INSERT INTO teams(
                competition_id, owner_id, title, description, needed_skills,
                needed_role, availability, working_style, project_goal, members_needed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                competition_id,
                session["user_id"],
                title,
                description,
                ",".join(needed_skills),
                needed_role,
                availability,
                working_style,
                project_goal,
                members_needed,
            ),
        )
        conn.commit()
        team_id = cursor.lastrowid
        conn.close()
        flash("Recruiting post created.")
        return redirect(url_for("team_applicants", team_id=team_id))

    conn.close()
    return render_template(
        "recruit.html",
        competition=competition,
        skills=SKILLS,
        availability=AVAILABILITY,
        roles=ROLES,
        styles=WORKING_STYLES,
        goals=PROJECT_GOALS,
    )


@app.post("/team/<int:team_id>/apply")
@login_required
def apply_team(team_id):
    conn = get_db()
    team = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
    if not team:
        conn.close()
        abort(404)
    if team["owner_id"] == session["user_id"]:
        conn.close()
        flash("You cannot apply to your own team.")
        return redirect(url_for("competition_teams", competition_id=team["competition_id"]))

    try:
        conn.execute(
            "INSERT INTO applications(team_id, user_id) VALUES (?, ?)",
            (team_id, session["user_id"]),
        )
        conn.commit()
        flash("Application submitted.")
    except sqlite3.IntegrityError:
        flash("You already applied to this team.")

    conn.close()
    return redirect(url_for("competition_teams", competition_id=team["competition_id"]))


@app.post("/team/<int:team_id>/shortlist")
@login_required
def shortlist_team(team_id):
    conn = get_db()
    team = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
    if not team:
        conn.close()
        abort(404)

    existing = conn.execute(
        "SELECT id FROM shortlists WHERE user_id = ? AND team_id = ?",
        (session["user_id"], team_id),
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM shortlists WHERE id = ?", (existing["id"],))
        flash("Removed from shortlist.")
    else:
        conn.execute(
            "INSERT INTO shortlists(user_id, team_id) VALUES (?, ?)",
            (session["user_id"], team_id),
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
        """
        SELECT teams.*, competitions.name AS competition_name
        FROM teams
        JOIN competitions ON competitions.id = teams.competition_id
        WHERE teams.id = ?
        """,
        (team_id,),
    ).fetchone()

    if not team:
        conn.close()
        abort(404)
    if team["owner_id"] != owner["id"]:
        conn.close()
        abort(403)

    applicants = conn.execute(
        """
        SELECT applications.id AS application_id, applications.status,
               users.*
        FROM applications
        JOIN users ON users.id = applications.user_id
        WHERE applications.team_id = ?
        ORDER BY applications.created_at DESC
        """,
        (team_id,),
    ).fetchall()

    enriched = []
    for applicant in applicants:
        score, reasons = compatibility(applicant, team)
        enriched.append({"applicant": applicant, "score": score, "reasons": reasons})
    enriched.sort(key=lambda x: x["score"], reverse=True)

    conn.close()
    return render_template("applicants.html", team=team, applicants=enriched)


@app.post("/application/<int:application_id>/<status>")
@login_required
def update_application(application_id, status):
    if status not in {"Accepted", "Rejected"}:
        abort(400)

    conn = get_db()
    app_row = conn.execute(
        """
        SELECT applications.*, teams.owner_id, teams.id AS team_id
        FROM applications
        JOIN teams ON teams.id = applications.team_id
        WHERE applications.id = ?
        """,
        (application_id,),
    ).fetchone()

    if not app_row:
        conn.close()
        abort(404)
    if app_row["owner_id"] != session["user_id"]:
        conn.close()
        abort(403)

    conn.execute(
        "UPDATE applications SET status = ? WHERE id = ?",
        (status, application_id),
    )
    conn.commit()
    team_id = app_row["team_id"]
    conn.close()
    flash(f"Application {status.lower()}.")
    return redirect(url_for("team_applicants", team_id=team_id))


if __name__ == "__main__":
    init_db()
    seed_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
