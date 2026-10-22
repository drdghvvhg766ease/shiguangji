"""Create export_jobs table for circle data exports."""
from app.database import engine
from app.models import ExportJob


def migrate():
    ExportJob.__table__.create(engine, checkfirst=True)
    print(f"ensured table {ExportJob.__tablename__}")


if __name__ == "__main__":
    migrate()
