import os
from pathlib import Path

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
    inspect,
    text,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "teammatch.db"

DEFAULT_WEIGHTS = {
    "skills": 0.35,
    "availability": 0.20,
    "preferred_role": 0.20,
    "working_style": 0.10,
    "project_goal": 0.15,
}

metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False),
    Column("university", Text, nullable=False),
    Column("email", Text, nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
    Column("skills", Text, nullable=False),
    Column("availability", Text, nullable=False),
    Column("preferred_role", Text, nullable=False),
    Column("working_style", Text, nullable=False),
    Column("project_goal", Text, nullable=False),
    Column("feedback_opt_in", Boolean, nullable=False, server_default=text("TRUE")),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
)

competitions = Table(
    "competitions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False),
    Column("organizer", Text),
    Column("deadline", Text),
    Column("description", Text),
    Column("category", Text),
    Column("eligibility", Text),
    Column("participation_type", Text),
    Column("source_name", Text),
    Column("source_url", Text),
    Column("external_id", Text),
    Column("fetched_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
    Column("is_active", Boolean, nullable=False, server_default=text("TRUE")),
    Column("application_start_date", Date),
    Column("deadline_date", Date),
    Column("original_deadline_text", Text),
)

teams = Table(
    "teams", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("competition_id", Integer, ForeignKey("competitions.id"), nullable=False),
    Column("owner_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("title", Text, nullable=False),
    Column("description", Text),
    Column("needed_skills", Text, nullable=False),
    Column("needed_role", Text, nullable=False),
    Column("availability", Text, nullable=False),
    Column("working_style", Text, nullable=False),
    Column("project_goal", Text, nullable=False),
    Column("members_needed", Integer, nullable=False, server_default=text("1")),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
)

applications = Table(
    "applications", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("status", Text, nullable=False, server_default=text("'Pending'")),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
    UniqueConstraint("team_id", "user_id", name="uq_applications_team_user"),
)

shortlists = Table(
    "shortlists", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
    UniqueConstraint("user_id", "team_id", name="uq_shortlists_user_team"),
)

matching_settings = Table(
    "matching_settings", metadata,
    Column("id", Integer, primary_key=True),
    Column("skills", Float, nullable=False),
    Column("availability", Float, nullable=False),
    Column("preferred_role", Float, nullable=False),
    Column("working_style", Float, nullable=False),
    Column("project_goal", Float, nullable=False),
    Column("updated_at", DateTime, server_default=func.current_timestamp()),
    CheckConstraint("id = 1", name="ck_matching_settings_singleton"),
)

recommendation_feedback = Table(
    "recommendation_feedback", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("team_id", Integer, ForeignKey("teams.id"), nullable=False),
    Column("decision", Text, nullable=False),
    Column("reason", Text),
    Column("comment", Text),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
    Column("matching_score", Float, nullable=False),
    Column("factor_scores_json", Text, nullable=False),
    Column("weights_json", Text, nullable=False),
    Column("use_for_learning", Boolean, nullable=False, server_default=text("TRUE")),
    Column("demo", Boolean, nullable=False, server_default=text("FALSE")),
    CheckConstraint("decision IN ('Accept','Reject')", name="ck_feedback_decision"),
)

weight_proposals = Table(
    "weight_proposals", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("factor", Text, nullable=False),
    Column("old_weights_json", Text, nullable=False),
    Column("proposed_weights_json", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("feedback_count", Integer, nullable=False),
    Column("main_reason", Text, nullable=False),
    Column("status", Text, nullable=False, server_default=text("'Pending'")),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
    Column("reviewed_at", DateTime),
    Column("proposal_source", Text, nullable=False, server_default=text("'Rule-based'")),
    Column("ai_reason", Text),
    Column("evidence_summary", Text),
    Column("eligible_feedback_count", Integer),
    Column("feedback_max_id", Integer),
    Column("ai_run_id", Integer),
    CheckConstraint("status IN ('Pending','Approved','Rejected')", name="ck_proposal_status"),
)

ai_weight_judge_runs = Table(
    "ai_weight_judge_runs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("decision", Text, nullable=False),
    Column("current_weights_json", Text, nullable=False),
    Column("proposed_weights_json", Text),
    Column("reason", Text),
    Column("evidence_summary", Text),
    Column("aggregate_input_json", Text, nullable=False),
    Column("eligible_feedback_count", Integer, nullable=False),
    Column("excluded_feedback_count", Integer, nullable=False, server_default=text("0")),
    Column("feedback_min_id", Integer),
    Column("feedback_max_id", Integer),
    Column("status", Text, nullable=False),
    Column("error_message", Text),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
    CheckConstraint("status IN ('Completed','Failed')", name="ck_ai_weight_judge_run_status"),
)

weight_history = Table(
    "weight_history", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("old_weights_json", Text, nullable=False),
    Column("new_weights_json", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("feedback_count", Integer, nullable=False),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
)

_ENGINE = None
_ENGINE_URL = None


def _normalize_database_url(url):
    # Railway commonly exposes postgresql://. Explicitly select psycopg v3.
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def get_database_url():
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        return _normalize_database_url(configured)
    return f"sqlite:///{DB_PATH}"


def get_engine():
    global _ENGINE, _ENGINE_URL
    url = get_database_url()
    if _ENGINE is not None and _ENGINE_URL == url:
        return _ENGINE
    if _ENGINE is not None:
        _ENGINE.dispose()

    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite:"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def _sqlite_fk_on(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _ENGINE = engine
    _ENGINE_URL = url
    return engine


class DBResult:
    def __init__(self, result):
        self._result = result

    @property
    def rowcount(self):
        return self._result.rowcount

    def fetchone(self):
        return self._result.mappings().first()

    def fetchall(self):
        return self._result.mappings().all()

    def scalar(self):
        return self._result.scalar()


class DBConnection:
    """Small SQLAlchemy Core wrapper that preserves mapping-style row access."""

    def __init__(self):
        self._conn = get_engine().connect()

    def execute(self, statement, params=None):
        return DBResult(self._conn.execute(text(statement), params or {}))

    def executemany(self, statement, param_rows):
        return DBResult(self._conn.execute(text(statement), list(param_rows)))

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_db():
    return DBConnection()


def init_db():
    """Idempotently create missing schema without deleting existing data."""
    engine = get_engine()
    metadata.create_all(engine)

    # Small compatibility migration for pre-Session-7 databases.
    inspector = inspect(engine)
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    if "feedback_opt_in" not in user_columns:
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE users ADD COLUMN feedback_opt_in BOOLEAN NOT NULL DEFAULT TRUE"))
            else:
                conn.execute(text("ALTER TABLE users ADD COLUMN feedback_opt_in INTEGER NOT NULL DEFAULT 1"))

    # Phase 3 compatibility migration: add competition provenance/search fields without
    # deleting or recreating existing rows referenced by teams.
    competition_columns = {c["name"] for c in inspect(engine).get_columns("competitions")}
    competition_additions = {
        "category": "TEXT",
        "eligibility": "TEXT",
        "participation_type": "TEXT",
        "source_name": "TEXT",
        "source_url": "TEXT",
        "external_id": "TEXT",
        "fetched_at": "TIMESTAMPTZ" if engine.dialect.name == "postgresql" else "DATETIME",
        "updated_at": "TIMESTAMPTZ" if engine.dialect.name == "postgresql" else "DATETIME",
        "is_active": "BOOLEAN NOT NULL DEFAULT TRUE" if engine.dialect.name == "postgresql" else "INTEGER NOT NULL DEFAULT 1",
        "application_start_date": "DATE",
        "deadline_date": "DATE",
        "original_deadline_text": "TEXT",
    }
    with engine.begin() as migration_conn:
        for column_name, column_type in competition_additions.items():
            if column_name not in competition_columns:
                migration_conn.execute(text(f"ALTER TABLE competitions ADD COLUMN {column_name} {column_type}"))
        migration_conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_competitions_source_external "
            "ON competitions(source_name, external_id)"
        ))
        migration_conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_competitions_active_deadline "
            "ON competitions(is_active, deadline_date)"
        ))

    # AI Weight Judge compatibility migration. Preserve historical rule-based proposals.
    proposal_columns = {c["name"] for c in inspect(engine).get_columns("weight_proposals")}
    proposal_additions = {
        "proposal_source": "TEXT NOT NULL DEFAULT 'Rule-based'",
        "ai_reason": "TEXT",
        "evidence_summary": "TEXT",
        "eligible_feedback_count": "INTEGER",
        "feedback_max_id": "INTEGER",
        "ai_run_id": "INTEGER",
    }
    with engine.begin() as migration_conn:
        for column_name, column_type in proposal_additions.items():
            if column_name not in proposal_columns:
                migration_conn.execute(text(f"ALTER TABLE weight_proposals ADD COLUMN {column_name} {column_type}"))

    conn = get_db()
    existing = conn.execute("SELECT id FROM matching_settings WHERE id = :id", {"id": 1}).fetchone()
    if not existing:
        conn.execute(
            """INSERT INTO matching_settings
               (id, skills, availability, preferred_role, working_style, project_goal)
               VALUES (:id, :skills, :availability, :preferred_role, :working_style, :project_goal)""",
            {"id": 1, **DEFAULT_WEIGHTS},
        )
        conn.commit()
    conn.close()


def reset_engine_for_tests():
    global _ENGINE, _ENGINE_URL
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _ENGINE_URL = None
