from .models import Circle, UserActivity


ACTION_LABELS = {
    "circle_create": "创建圈子", "circle_join": "加入圈子",
    "circle_leave": "退出圈子", "circle_delete": "解散圈子",
    "circle_edit": "修改圈子设置", "circle_invite": "重置邀请码",
    "circle_transfer": "转让圈主", "member_remove": "移出成员",
    "post_create": "发布记录", "post_edit": "编辑记录", "post_delete": "删除记录",
    "album_create": "新建分册", "album_edit": "编辑分册", "album_delete": "删除分册",
    "line_create": "新建时间线", "line_edit": "编辑时间线", "line_delete": "删除时间线",
    "comment_create": "发表评论", "comment_delete": "删除评论", "report_create": "提交举报",
    "circle_apply": "申请加入圈子", "member_role": "调整管理员", "join_review": "审核入圈申请",
    "announcement_create": "发布圈子公告", "announcement_delete": "删除圈子公告",
    "post_like": "点赞记录", "post_unlike": "取消点赞", "favorite_add": "收藏记录",
    "favorite_remove": "移除收藏",
}


def record_activity(db, user_id, circle_id, action, target_kind, target_id,
                    label="", post_id=None, event_key=None, created_at=None):
    circle = db.get(Circle, circle_id)
    if action.endswith("_create") and event_key is None:
        event_key = f"{target_kind}:create:{target_id}"
    event = UserActivity(
        user_id=user_id, circle_id=circle_id, circle_name=circle.name,
        action=action, target_kind=target_kind, target_id=target_id,
        target_label=label[:128], post_id=post_id, event_key=event_key,
    )
    if created_at is not None:
        event.created_at = created_at
    db.add(event)
    return event
