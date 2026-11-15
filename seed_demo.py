from werkzeug.security import generate_password_hash

from db import get_db, init_db
from seed_competitions import seed_competitions

DEMO_PASSWORD = "demo1234"


def seed_demo():
    init_db()
    seed_competitions()
    conn = get_db()

    recruiter = conn.execute(
        "SELECT id FROM users WHERE email = :email",
        {"email": "demo.recruiter@university.edu"},
    ).fetchone()
    if not recruiter:
        recruiter = conn.execute(
            """INSERT INTO users(name, university, email, password_hash, skills, availability,
                                  preferred_role, working_style, project_goal)
               VALUES (:name, :university, :email, :password_hash, :skills, :availability,
                       :preferred_role, :working_style, :project_goal)
               RETURNING id""",
            {
                "name": "Demo Recruiter",
                "university": "Demo University",
                "email": "demo.recruiter@university.edu",
                "password_hash": generate_password_hash(DEMO_PASSWORD),
                "skills": "Project management,Presentation,Research",
                "availability": "Weekday evenings",
                "preferred_role": "Project management",
                "working_style": "Structured and planned",
                "project_goal": "High quality / ambitious",
            },
        ).fetchone()
    owner_id = recruiter["id"]

    team_count = conn.execute(
        "SELECT COUNT(*) AS count FROM teams WHERE owner_id = :owner_id",
        {"owner_id": owner_id},
    ).fetchone()["count"]
    if team_count == 0:
        competition_ids = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM competitions").fetchall()
        }
        demo_teams = [
            {
                "competition_id": competition_ids["AI for Social Impact Challenge"],
                "owner_id": owner_id,
                "title": "EqualWork AI",
                "description": "Looking for teammates to prototype an AI tool for fairer student collaboration.",
                "needed_skills": "Coding,Design",
                "needed_role": "Data / Coding",
                "availability": "Weekday evenings",
                "working_style": "Structured and planned",
                "project_goal": "High quality / ambitious",
                "members_needed": 2,
            },
            {
                "competition_id": competition_ids["Campus Sustainability Challenge"],
                "owner_id": owner_id,
                "title": "Green Campus Crew",
                "description": "A team exploring waste reduction and student behavior change on campus.",
                "needed_skills": "Research,Presentation",
                "needed_role": "Research",
                "availability": "Flexible / Negotiable",
                "working_style": "Discussion-oriented",
                "project_goal": "Balanced effort",
                "members_needed": 2,
            },
            {
                "competition_id": competition_ids["Smart Mobility Case Competition"],
                "owner_id": owner_id,
                "title": "MoveSmart",
                "description": "We need one more member for mobility data analysis and final presentation.",
                "needed_skills": "Data analysis,Presentation",
                "needed_role": "Data / Coding",
                "availability": "Weekends",
                "working_style": "Fast-paced",
                "project_goal": "High quality / ambitious",
                "members_needed": 1,
            },
        ]
        conn.executemany(
            """INSERT INTO teams(competition_id, owner_id, title, description, needed_skills,
                                  needed_role, availability, working_style, project_goal, members_needed)
               VALUES (:competition_id, :owner_id, :title, :description, :needed_skills,
                       :needed_role, :availability, :working_style, :project_goal, :members_needed)""",
            demo_teams,
        )

    joiner = conn.execute(
        "SELECT id FROM users WHERE email = :email",
        {"email": "demo.student@university.edu"},
    ).fetchone()
    if not joiner:
        conn.execute(
            """INSERT INTO users(name, university, email, password_hash, skills, availability,
                                  preferred_role, working_style, project_goal)
               VALUES (:name, :university, :email, :password_hash, :skills, :availability,
                       :preferred_role, :working_style, :project_goal)""",
            {
                "name": "Demo Student",
                "university": "Demo University",
                "email": "demo.student@university.edu",
                "password_hash": generate_password_hash(DEMO_PASSWORD),
                "skills": "Coding,Data analysis,Design",
                "availability": "Weekday evenings",
                "preferred_role": "Data / Coding",
                "working_style": "Structured and planned",
                "project_goal": "High quality / ambitious",
            },
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed_demo()
    print("Seeded labelled local/demo accounts and teams.")
