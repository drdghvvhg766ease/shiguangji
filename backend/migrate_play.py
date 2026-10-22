"""Create play tables: challenges / challenge_checkins / guess_attempts."""
from app.database import engine
from app.models import Challenge, ChallengeCheckin, GuessAttempt


def migrate():
    for model in (Challenge, ChallengeCheckin, GuessAttempt):
        model.__table__.create(engine, checkfirst=True)
        print(f"ensured table {model.__tablename__}")


if __name__ == "__main__":
    migrate()
