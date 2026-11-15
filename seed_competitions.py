from datetime import datetime, timezone

from db import get_db, init_db

COMPETITIONS = [
    {"name":"AI for Social Impact Challenge","organizer":"University Innovation Hub","deadline":"2026-11-20","description":"Build an AI-enabled idea that addresses a social or community problem.","category":"Data / AI"},
    {"name":"Campus Sustainability Challenge","organizer":"Student Entrepreneurship Center","deadline":"2026-12-05","description":"Develop a practical solution for a more sustainable university or city.","category":"Sustainability"},
    {"name":"Smart Mobility Case Competition","organizer":"Mobility Lab","deadline":"2027-01-18","description":"Design a data-driven solution for urban mobility and transportation.","category":"Engineering"},
    {"name":"Digital Health Innovation Sprint","organizer":"HealthTech Society","deadline":"2027-02-10","description":"Create a student-led digital health concept with measurable user value.","category":"Idea / Planning"},
]


def seed_competitions():
    init_db()
    conn = get_db()
    now = datetime.now(timezone.utc)
    for idx, item in enumerate(COMPETITIONS, start=1):
        external_id = f"demo-{idx}"
        exists = conn.execute(
            "SELECT id FROM competitions WHERE source_name=:source_name AND external_id=:external_id",
            {"source_name":"Demo","external_id":external_id},
        ).fetchone()
        params = {**item,"source_name":"Demo","source_url":None,"external_id":external_id,"fetched_at":now,"updated_at":now,"is_active":True}
        if not exists:
            conn.execute(
                """INSERT INTO competitions(name,organizer,deadline,description,category,source_name,source_url,external_id,fetched_at,updated_at,is_active)
                   VALUES (:name,:organizer,:deadline,:description,:category,:source_name,:source_url,:external_id,:fetched_at,:updated_at,:is_active)""",
                params,
            )
    conn.commit(); conn.close()


if __name__ == "__main__":
    seed_competitions()
    print("Seeded development/demo competition fixtures. source_name=Demo")
