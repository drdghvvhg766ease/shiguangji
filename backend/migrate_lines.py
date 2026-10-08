"""Add circle timeline branches and optional record locations; idempotent."""
from sqlalchemy import inspect, text
from app.database import engine, Base
from app import models


def migrate():
    models.MemoryLine.__table__.create(engine, checkfirst=True)
    for table, fields in {
        "albums": {"line_id": "INT NULL"},
        "posts": {"line_id": "INT NULL", "latitude": "DOUBLE NULL", "longitude": "DOUBLE NULL", "location_name": "VARCHAR(128) NULL"},
    }.items():
        cols = {c["name"] for c in inspect(engine).get_columns(table)}
        with engine.begin() as conn:
            for name, definition in fields.items():
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD {name} {definition}"))
            if not any(fk["constrained_columns"] == ["line_id"] for fk in inspect(engine).get_foreign_keys(table)):
                conn.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_line FOREIGN KEY (line_id) REFERENCES memory_lines(id) ON DELETE SET NULL"))
    print("Timeline migration applied")


if __name__ == "__main__":
    migrate()
