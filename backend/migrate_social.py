"""Add circle roles, requests, personal settings, messages and collections."""
from sqlalchemy import inspect, text
from app.database import engine
from app.models import Announcement, FavoriteFolder, FavoriteItem, JoinRequest, Notification, PostLike


def migrate():
    for table, fields in {
        "users": {"auth_version": "INT NOT NULL DEFAULT 0"},
        "circle_members": {"role": "VARCHAR(16) NOT NULL DEFAULT 'member'"},
        "comments": {"reply_to_id": "INT NULL", "reply_to_name": "VARCHAR(64) NULL"},
    }.items():
        columns = {c["name"] for c in inspect(engine).get_columns(table)}
        with engine.begin() as conn:
            for name, definition in fields.items():
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE {table} ADD {name} {definition}"))
    for model in (JoinRequest, Notification, Announcement, PostLike, FavoriteFolder, FavoriteItem):
        model.__table__.create(engine, checkfirst=True)
    with engine.begin() as conn:
        conn.execute(text("UPDATE circles SET allow_member_invite = 1"))
    print("Social migration applied; existing memberships and media preserved")


if __name__ == "__main__":
    migrate()
