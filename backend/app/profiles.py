from pathlib import Path


def avatar_url(user):
    if not user or not user.avatar:
        return None
    return f"/api/auth/users/{user.id}/avatar?v={Path(user.avatar).stem}"
