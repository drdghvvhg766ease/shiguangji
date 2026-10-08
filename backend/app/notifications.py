from .models import Notification


def notify(db, user_ids, kind, title, body="", circle_id=None, post_id=None):
    for user_id in set(user_ids):
        db.add(Notification(user_id=user_id, kind=kind, title=title[:128], body=body[:255],
                            circle_id=circle_id, post_id=post_id))
