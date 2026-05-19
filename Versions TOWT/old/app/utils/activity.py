"""Activity logging helper — call from any router to log user actions.

Supports two call patterns:
  - NEW: log_activity(db, user, module, action, resource_type, resource_id, detail)
  - OLD: log_activity(db, *, user=, action=, module=, entity_type=, entity_id=, ...)
"""
from app.models.activity_log import ActivityLog


async def log_activity(
    db,
    user_or_none=None,
    module_or_none=None,
    action_or_none=None,
    resource_type=None,
    resource_id=None,
    detail=None,
    *,
    # Keyword-only args for OLD call pattern
    user=None,
    action: str = None,
    module: str = None,
    entity_type: str = None,
    entity_id=None,
    entity_label: str = None,
    ip_address: str = None,
):
    """Log an activity. Supports both positional and keyword-only args."""
    # Resolve args from either call pattern
    _user = user or user_or_none
    _action = action or action_or_none or "unknown"
    _module = module or module_or_none or "unknown"
    _entity_type = entity_type or resource_type
    _entity_id = entity_id or resource_id
    _detail = detail
    _label = entity_label

    entry = ActivityLog(
        user_id=_user.id if _user and hasattr(_user, "id") else None,
        user_name=(_user.full_name if hasattr(_user, "full_name") else str(_user)) if _user else None,
        user_role=_user.role if _user and hasattr(_user, "role") else None,
        action=_action,
        module=_module,
        entity_type=_entity_type,
        entity_id=str(_entity_id) if _entity_id is not None else None,
        entity_label=_label or _detail,
        detail=_detail,
        ip_address=ip_address,
    )
    db.add(entry)
    try:
        await db.flush()
    except Exception:
        pass  # Never let logging break the main flow


def get_client_ip(request) -> str:
    """Extract client IP from request, handling reverse proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "unknown"
