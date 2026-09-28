"""Consultas de usuarios del laboratorio (Fase 11b)."""
from django.db.models import Prefetch, Q

from apps.accounts.models import Membership, Role, User


def lab_users(*, query: str = "", show_inactive: bool = False) -> list[User]:
    users = User.objects.prefetch_related(Prefetch(
        "memberships", queryset=Membership.objects.filter(is_active=True)
        .select_related("role").order_by("role_id"), to_attr="active_memberships"))
    if not show_inactive:
        users = users.filter(is_active=True)
    query = query.strip()
    if query:
        users = users.filter(Q(username__icontains=query) | Q(first_name__icontains=query)
                             | Q(last_name__icontains=query) | Q(email__icontains=query))
    # Superusuarios de la plataforma no se listan: no son personal del laboratorio.
    return list(users.exclude(is_superuser=True, memberships__isnull=True)
                .order_by("-is_active", "first_name", "username").distinct())


def get_lab_user(*, pk) -> User:
    return User.objects.get(pk=pk)


def all_roles() -> list[Role]:
    return list(Role.objects.order_by("id"))
