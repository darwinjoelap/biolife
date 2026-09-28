from apps.accounts.permissions import ui_permissions


def ui(request):
    """`can`: qué secciones del menú ve el usuario (Fase 11b)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"can": ui_permissions(user)}
