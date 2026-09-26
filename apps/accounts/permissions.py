from __future__ import annotations

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
