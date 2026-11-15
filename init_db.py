from db import get_database_url, init_db

if __name__ == "__main__":
    init_db()
    backend = "PostgreSQL" if get_database_url().startswith("postgresql") else "SQLite"
    print(f"TeamMatch schema is ready ({backend}).")
