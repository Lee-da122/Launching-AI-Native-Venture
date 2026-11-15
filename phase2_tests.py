import json
import os
import tempfile
from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import db
import learning
import matching
from guardrails import is_out_of_scope_search

ROOT = Path(__file__).resolve().parent
results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def insert_fixture_data():
    conn = db.get_db()
    u1 = conn.execute(
        """INSERT INTO users(name, university, email, password_hash, skills, availability,
                              preferred_role, working_style, project_goal)
           VALUES (:name,:university,:email,:password_hash,:skills,:availability,
                   :preferred_role,:working_style,:project_goal) RETURNING id""",
        {
            "name":"Owner","university":"U","email":"owner@u.edu","password_hash":"hashed",
            "skills":"Research","availability":"Weekday evenings","preferred_role":"Research",
            "working_style":"Structured and planned","project_goal":"High quality / ambitious",
        },
    ).fetchone()["id"]
    u2 = conn.execute(
        """INSERT INTO users(name, university, email, password_hash, skills, availability,
                              preferred_role, working_style, project_goal)
           VALUES (:name,:university,:email,:password_hash,:skills,:availability,
                   :preferred_role,:working_style,:project_goal) RETURNING id""",
        {
            "name":"Joiner","university":"U","email":"joiner@u.edu","password_hash":"hashed",
            "skills":"Coding,Design","availability":"Weekday evenings","preferred_role":"Data / Coding",
            "working_style":"Structured and planned","project_goal":"High quality / ambitious",
        },
    ).fetchone()["id"]
    cid = conn.execute(
        "INSERT INTO competitions(name, organizer, deadline, description) VALUES (:n,:o,:d,:x) RETURNING id",
        {"n":"C","o":"O","d":"2027-01-01","x":"D"},
    ).fetchone()["id"]
    tid = conn.execute(
        """INSERT INTO teams(competition_id, owner_id, title, description, needed_skills, needed_role,
                              availability, working_style, project_goal, members_needed)
           VALUES (:competition_id,:owner_id,:title,:description,:needed_skills,:needed_role,
                   :availability,:working_style,:project_goal,:members_needed) RETURNING id""",
        {
            "competition_id":cid,"owner_id":u1,"title":"T","description":"D",
            "needed_skills":"Coding,Design","needed_role":"Data / Coding",
            "availability":"Weekday evenings","working_style":"Structured and planned",
            "project_goal":"High quality / ambitious","members_needed":1,
        },
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO applications(team_id,user_id) VALUES (:team_id,:user_id)",
        {"team_id":tid,"user_id":u2},
    )
    conn.commit(); conn.close()
    return u1,u2,cid,tid


with tempfile.TemporaryDirectory() as td:
    old_path = db.DB_PATH
    old_db_url = os.environ.pop("DATABASE_URL", None)
    db.DB_PATH = Path(td) / "phase2.db"
    db.reset_engine_for_tests()
    try:
        db.init_db()
        db.init_db()  # idempotency
        inspector = __import__('sqlalchemy').inspect(db.get_engine())
        expected_tables = {
            'users','competitions','teams','applications','shortlists','matching_settings',
            'recommendation_feedback','weight_proposals','weight_history'
        }
        check('Schema bootstrap idempotent', expected_tables.issubset(set(inspector.get_table_names())), str(inspector.get_table_names()))

        owner, joiner, cid, tid = insert_fixture_data()
        weights0 = matching.get_active_weights()
        check('Initial weights total 100%', abs(sum(weights0.values()) - 1.0) < 1e-9, str(weights0))

        user = {
            'skills':'Coding,Design','availability':'Weekday evenings','preferred_role':'Data / Coding',
            'working_style':'Structured and planned','project_goal':'High quality / ambitious'
        }
        team = {
            'needed_skills':'Coding,Design','availability':'Weekday evenings','needed_role':'Data / Coding',
            'working_style':'Structured and planned','project_goal':'High quality / ambitious'
        }
        score, _, factors = matching.compatibility(user, team, weights0)
        check('Matching preserved', score == 100, f'score={score}')

        for _ in range(5):
            learning.save_feedback(joiner, tid, 'Reject', 'Availability', '', score, factors, weights0, True)
        learning.save_feedback(joiner, tid, 'Reject', 'Skill fit', '', score, factors, weights0, False)
        summary = learning.feedback_summary()
        check('Opt-out excluded from learning summary', summary['total'] == 5 and summary['reason_counts']['Skill fit'] == 0, str(summary['reason_counts']))

        proposal = learning.generate_proposal()
        before = matching.get_active_weights()
        check('Proposal created at threshold', proposal and proposal['factor'] == 'availability', str(proposal))
        check('Proposal does not auto-apply', before == weights0, f'before={before}')
        proposed = json.loads(proposal['proposed_weights_json'])
        check('Proposed weights normalized', abs(sum(proposed.values()) - 1.0) < 1e-9, str(proposed))

        ok = learning.review_proposal(proposal['id'], 'Approved')
        after = matching.get_active_weights()
        check('Admin approval activates weights', ok and after['availability'] == 0.25, str(after))
        check('Approved weights still total 100%', abs(sum(after.values()) - 1.0) < 1e-9, str(after))
        conn = db.get_db()
        history_count = conn.execute('SELECT COUNT(*) AS c FROM weight_history').fetchone()['c']
        conn.close()
        check('Weight history saved', history_count == 1, f'count={history_count}')

        # Generate another eligible proposal and reject it; active weights must remain unchanged.
        proposal2 = learning.generate_proposal()
        active_pre_reject = matching.get_active_weights()
        check('Second proposal can be reviewed', bool(proposal2), str(proposal2))
        learning.review_proposal(proposal2['id'], 'Rejected')
        check('Rejected proposal leaves weights unchanged', matching.get_active_weights() == active_pre_reject, str(active_pre_reject))

        # Simulate app restart/redeploy against the same persistent DB file.
        db.reset_engine_for_tests()
        db.init_db()
        conn = db.get_db()
        persisted = {
            'users': conn.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c'],
            'teams': conn.execute('SELECT COUNT(*) AS c FROM teams').fetchone()['c'],
            'applications': conn.execute('SELECT COUNT(*) AS c FROM applications').fetchone()['c'],
            'feedback': conn.execute('SELECT COUNT(*) AS c FROM recommendation_feedback').fetchone()['c'],
            'history': conn.execute('SELECT COUNT(*) AS c FROM weight_history').fetchone()['c'],
        }
        conn.close()
        check('Restart preserves SQLite fallback data', persisted == {'users':2,'teams':1,'applications':1,'feedback':6,'history':1}, str(persisted))
        check('Restart preserves active weights', matching.get_active_weights() == after, str(matching.get_active_weights()))
    finally:
        db.DB_PATH = old_path
        db.reset_engine_for_tests()
        if old_db_url is not None:
            os.environ['DATABASE_URL'] = old_db_url

# PostgreSQL portability: compile every Core table using the PostgreSQL dialect.
for table in db.metadata.sorted_tables:
    ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
    check(f'PostgreSQL DDL compiles: {table.name}', 'CREATE TABLE' in ddl, ddl[:120])

# No SQLite qmark placeholders should remain in business modules.
for filename in ['app.py','matching.py','learning.py']:
    source = (ROOT / filename).read_text()
    check(f'Portable named SQL parameters: {filename}', ' ?' not in source and '=?' not in source and '?,?' not in source, 'no qmark placeholders')

# Security/config source checks that do not require Flask to be installed in this build environment.
app_source = (ROOT / 'app.py').read_text()
check('Production SECRET_KEY required', 'SECRET_KEY must be set in production' in app_source, 'production startup fails closed')
check('Admin backend protection present', app_source.count('@admin_required') >= 4, f"count={app_source.count('@admin_required')}")
check('CSRF backend validation present', '@app.before_request' in app_source and 'hmac.compare_digest' in app_source, 'session token comparison')
check('Health route present', '@app.route("/healthz")' in app_source and 'SELECT 1 AS ok' in app_source, 'DB-aware health check')
check('Scope guard preserved', is_out_of_scope_search('Write my entire competition proposal and presentation script for me.'), 'attack blocked')
check('Normal scope search preserved', not is_out_of_scope_search('Find a case competition where I can practice presentation skills.'), 'normal query allowed')

post_forms = 0
csrf_forms = 0
for template in (ROOT / 'templates').glob('*.html'):
    source = template.read_text()
    post_forms += source.lower().count('method="post"')
    csrf_forms += source.count('name="_csrf_token"')
check('All POST forms carry CSRF token', post_forms == csrf_forms, f'post_forms={post_forms}, csrf_tokens={csrf_forms}')

# Red line search.
combined = '\n'.join((ROOT / f).read_text() for f in ['app.py','matching.py','learning.py','db.py'])
for forbidden in ['good_teammate_score','bad_teammate_score','reputation_score','blacklist_score','visibility_penalty']:
    check(f'Red line absent: {forbidden}', forbidden not in combined.lower(), 'not implemented')

print('PHASE2_TESTS_OK')
for name, ok, detail in results:
    print(('PASS' if ok else 'FAIL'), '|', name, '|', detail)
