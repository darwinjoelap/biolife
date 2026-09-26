from __future__ import annotations

from apps.accounts.models import AuditLog, User


def log_action(
    *,
    action: str,
    user: User | None = None,
    model_name: str = "",
    object_id: str = "",
    changes: dict | None = None,
    ip: str | None = None,
    user_agent: str = "",
) -> AuditLog:
    """
    Único punto de escritura de AuditLog en todo el sistema. Nadie más debe llamar
    a `AuditLog.objects.create(...)` directamente — así toda la lógica de qué se
    registra queda en un solo lugar.
    """
    return AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        changes=changes,
        ip=ip,
        user_agent=user_agent,
    )


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_login_success(*, sender, request, user, **kwargs) -> None:
    log_action(
        action="LOGIN_OK",
        user=user,
        ip=_client_ip(request) if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )


def log_login_failed(*, sender, credentials, request=None, **kwargs) -> None:
    log_action(
        action="LOGIN_FALLIDO",
        user=None,
        changes={"username": credentials.get("username", "")},
        ip=_client_ip(request) if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )


def log_logout(*, sender, request, user, **kwargs) -> None:
    log_action(
        action="LOGOUT",
        user=user,
        ip=_client_ip(request) if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )
