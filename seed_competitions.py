from db import get_db, init_db

COMPETITIONS = [
    {
        "name": "AI for Social Impact Challenge",
        "organizer": "University Innovation Hub",
        "deadline": "2026-11-20",
        "description": "Build an AI-enabled idea that addresses a social or community problem.",
    },
    {
        "name": "Campus Sustainability Challenge",
        "organizer": "Student Entrepreneurship Center",
        "deadline": "2026-12-05",
        "description": "Develop a practical solution for a more sustainable university or city.",
    },
    {
        "name": "Smart Mobility Case Competition",
        "organizer": "Mobility Lab",
        "deadline": "2027-01-18",
        "description": "Design a data-driven solution for urban mobility and transportation.",
    },
    {
        "name": "Digital Health Innovation Sprint",
        "organizer": "HealthTech Society",
        "deadline": "2027-02-10",
        "description": "Create a student-led digital health concept with measurable user value.",
    },
]


def seed_competitions():
    init_db()
    conn = get_db()
    for item in COMPETITIONS:
        exists = conn.execute(
            "SELECT id FROM competitions WHERE name = :name",
            {"name": item["name"]},
        ).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO competitions(name, organizer, deadline, description)
                   VALUES (:name, :organizer, :deadline, :description)""",
                item,
            )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed_competitions()
    print("Seeded competition fixtures without creating demo accounts.")
