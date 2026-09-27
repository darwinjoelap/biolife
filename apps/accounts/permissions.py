from __future__ import annotations

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def has_role(user, *codes: str) -> bool:
    """True si `user` tiene una Membership activa con alguno de los `codes` dados."""
    if not getattr(user, "is_authenticated", False):
        return False
    return user.memberships.filter(role__code__in=codes, is_active=True).exists()


def has_permission(user, permission_key: str) -> bool:
    """
    True si alguna Membership activa de `user` tiene `permission_key` en `True`
    dentro de `role.permissions`.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    return any(
        membership.role.permissions.get(permission_key, False)
        for membership in user.memberships.filter(is_active=True).select_related("role")
    )


class RoleRequiredMixin:
    """
    Mixin de vista basada en clase: exige que el usuario tenga alguno de
    `allowed_roles`. Levanta 403 si no.

    Uso:
        class PanelView(RoleRequiredMixin, View):
            allowed_roles = (Role.Code.ADMIN_LAB, Role.Code.BIOANALISTA)
    """

    allowed_roles: tuple[str, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        if not has_role(request.user, *self.allowed_roles):
            raise PermissionDenied("No tienes el rol requerido para acceder a esta página.")
        return super().dispatch(request, *args, **kwargs)


# Roles que operan la recepción (registrar pacientes y órdenes, tomar muestras). Sólo
# lectura puede consultar pero no modificar. El superusuario siempre pasa.
RECEPTION_ROLES = ("ADMIN_LAB", "RECEPCION", "BIOANALISTA", "TECNICO", "FACTURACION")
VIEW_ROLES = RECEPTION_ROLES + ("SOLO_LECTURA",)


def user_has_any_role(user, *codes: str) -> bool:
    return bool(getattr(user, "is_superuser", False)) or has_role(user, *codes)


def role_required(*codes: str):
    """Decorador de vista (función): exige sesión y alguno de `codes` (403 si no)."""
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not user_has_any_role(request.user, *codes):
                raise PermissionDenied("No tienes el rol requerido para esta acción.")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator

# Resultados (Fase 10): cargan técnico, bioanalista y administrador; validan quienes tienen
# `puede_validar_resultados` en su rol (bioanalista y administrador).
CAPTURE_ROLES = ("ADMIN_LAB", "BIOANALISTA", "TECNICO")
VALIDATE_ROLES = ("ADMIN_LAB", "BIOANALISTA")


def can_validate_results(user) -> bool:
    return bool(getattr(user, "is_superuser", False)) or has_permission(
        user, "puede_validar_resultados")
