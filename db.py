from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "teammatch.db"

DEFAULT_WEIGHTS = {
    "skills": 0.35,
    "availability": 0.20,
    "preferred_role": 0.20,
    "working_style": 0.10,
    "project_goal": 0.15,
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _columns(conn, table):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


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
            feedback_opt_in INTEGER NOT NULL DEFAULT 1,
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

        CREATE TABLE IF NOT EXISTS matching_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            skills REAL NOT NULL,
            availability REAL NOT NULL,
            preferred_role REAL NOT NULL,
            working_style REAL NOT NULL,
            project_goal REAL NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS recommendation_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('Accept','Reject')),
            reason TEXT,
            comment TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            matching_score REAL NOT NULL,
            factor_scores_json TEXT NOT NULL,
            weights_json TEXT NOT NULL,
            use_for_learning INTEGER NOT NULL DEFAULT 1,
            demo INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS weight_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factor TEXT NOT NULL,
            old_weights_json TEXT NOT NULL,
            proposed_weights_json TEXT NOT NULL,
            reason TEXT NOT NULL,
            feedback_count INTEGER NOT NULL,
            main_reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            reviewed_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS weight_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            old_weights_json TEXT NOT NULL,
            new_weights_json TEXT NOT NULL,
            reason TEXT NOT NULL,
            feedback_count INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Safe migration for databases created before Session 7.
    if "feedback_opt_in" not in _columns(conn, "users"):
        conn.execute("ALTER TABLE users ADD COLUMN feedback_opt_in INTEGER NOT NULL DEFAULT 1")

    exists = conn.execute("SELECT id FROM matching_settings WHERE id = 1").fetchone()
    if not exists:
        conn.execute(
            """INSERT INTO matching_settings
               (id, skills, availability, preferred_role, working_style, project_goal)
               VALUES (1, ?, ?, ?, ?, ?)""",
            tuple(DEFAULT_WEIGHTS.values()),
        )
    conn.commit()
    conn.close()
