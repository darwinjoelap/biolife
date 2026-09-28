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


# Panel del laboratorio (Fase 11b) ---------------------------------------------------------
# Toma de muestras: la recepción y el auxiliar de toma (éste sólo ve «Muestras por tomar»,
# la orden sin cobro, imprime etiquetas y marca tomadas o rechazadas).
COLLECTION_ROLES = RECEPTION_ROLES + ("AUXILIAR_TOMA",)
VIEW_ORDER_ROLES = VIEW_ROLES + ("AUXILIAR_TOMA",)
ADMIN_ROLES = ("ADMIN_LAB",)
MONEY_ROLES = ("ADMIN_LAB", "RECEPCION", "FACTURACION", "BIOANALISTA", "TECNICO",
               "SOLO_LECTURA")


# Catálogo (Fase 11c, ADR-030): todos consultan; la estructura la cambia el administrador;
# rangos, críticos y observaciones también el bioanalista (criterio clínico); precios y
# tasa, el administrador y facturación.
CATALOG_EDIT_ROLES = ADMIN_ROLES
CLINICAL_EDIT_ROLES = ("ADMIN_LAB", "BIOANALISTA")
PRICE_EDIT_ROLES = ("ADMIN_LAB", "FACTURACION")
# Tablas auxiliares (Fase 11d, ADR-031): el lote de reactivo lo registra quien procesa
# (bioanalista y técnico) al cambiar de reactivo; listas de opciones y observaciones
# generales, el bioanalista; monedas y descuentos, facturación.
LOT_EDIT_ROLES = ("ADMIN_LAB", "BIOANALISTA", "TECNICO")


def can_manage_lab(user) -> bool:
    """Configura el laboratorio y sus usuarios: rol Administrador (o superusuario)."""
    return user_has_any_role(user, *ADMIN_ROLES)


def ui_permissions(user) -> dict:
    """Qué secciones ve el usuario en el menú y en las pantallas (suma de sus roles).
    Las vistas vuelven a comprobar cada permiso: esto sólo decide qué se muestra."""
    if not getattr(user, "is_authenticated", False):
        return {}
    if getattr(user, "is_superuser", False):
        codes = {"ADMIN_LAB"}
    else:
        codes = set(user.memberships.filter(is_active=True)
                    .values_list("role__code", flat=True))
    return {
        "reception": bool(codes & set(RECEPTION_ROLES)),
        "collection": bool(codes & set(COLLECTION_ROLES)),
        "orders": bool(codes & set(VIEW_ROLES)),
        "money": bool(codes & set(MONEY_ROLES)),
        "results": bool(codes & set(VIEW_ROLES)),
        "reports": bool(codes & set(VIEW_ROLES)),
        "admin": bool(codes & set(ADMIN_ROLES)),
        "catalog": bool(codes & set(VIEW_ROLES)),
        "catalog_edit": bool(codes & set(CATALOG_EDIT_ROLES)),
        "clinical_edit": bool(codes & set(CLINICAL_EDIT_ROLES)),
        "prices_edit": bool(codes & set(PRICE_EDIT_ROLES)),
        "only_collection": bool(codes) and codes <= {"AUXILIAR_TOMA"},
    }


# Qué puede hacer cada rol (pantalla «Roles»): se deriva de las mismas tuplas que usan las
# vistas, así la tabla nunca se desincroniza del control de acceso real.
def role_abilities() -> list[tuple[str, set[str]]]:
    return [
        ("Registrar pacientes y órdenes, cobrar", set(RECEPTION_ROLES)),
        ("Editar pacientes, representantes y antecedentes", set(RECEPTION_ROLES)),
        ("Ver la ficha y la evolución del paciente", set(VIEW_ROLES)),
        ("Imprimir etiquetas y marcar tubos tomados", set(COLLECTION_ROLES)),
        ("Ver órdenes y cobros", set(VIEW_ROLES)),
        ("Cargar resultados", set(CAPTURE_ROLES)),
        ("Validar resultados", set(VALIDATE_ROLES)),
        ("Emitir y entregar informes", set(RECEPTION_ROLES)),
        ("Editar exámenes, parámetros y perfiles", set(CATALOG_EDIT_ROLES)),
        ("Editar rangos, valores críticos y observaciones", set(CLINICAL_EDIT_ROLES)),
        ("Editar listas de opciones, observaciones generales y antecedentes",
         set(CLINICAL_EDIT_ROLES)),
        ("Registrar lotes de reactivos (ISI)", set(LOT_EDIT_ROLES)),
        ("Editar precios y registrar la tasa de cambio", set(PRICE_EDIT_ROLES)),
        ("Editar monedas y descuentos", set(PRICE_EDIT_ROLES)),
        ("Editar secciones, unidades, métodos y tubos", set(CATALOG_EDIT_ROLES)),
        ("Configurar el laboratorio, usuarios y roles", set(ADMIN_ROLES)),
    ]
