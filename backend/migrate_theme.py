"""Add users.theme_preference for per-account theme preset/custom palette."""
from sqlalchemy import inspect, text

from app.database import engine


def migrate():
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    if "theme_preference" in cols:
        print("users.theme_preference already exists, skipped")
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD theme_preference TEXT NULL"))
    print("added users.theme_preference")


if __name__ == "__main__":
    migrate()
