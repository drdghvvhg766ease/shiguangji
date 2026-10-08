from .models import Post, Report


def post_snapshot(post: Post) -> dict:
    return {
        "content": post.content,
        "author": post.user.nickname if post.user else "",
        "username": post.user.username if post.user else "",
        "circle_name": post.circle.name if post.circle else "",
        "event_date": post.event_date.isoformat(),
    }


def detach_reports(db, post: Post, explanation="原记录已删除"):
    for report in db.query(Report).filter(Report.post_id == post.id).all():
        report.original_post_id = post.id
        report.snapshot = post_snapshot(post)
        report.post_id = None
        if report.status == "pending":
            from datetime import datetime
            report.status = "removed"
            report.handle_reason = explanation
            report.handled_at = datetime.utcnow()
    db.flush()
