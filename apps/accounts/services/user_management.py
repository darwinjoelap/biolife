from __future__ import annotations

import secrets

from django.core.management import call_command

from apps.accounts.models import Membership, Role, User


def seed_system_roles() -> None:
    """
    Siembra los 6 roles de tenant desde `apps/accounts/fixtures/roles.json`.
    Idempotente: `loaddata` hace upsert por PK, se puede llamar en cada
    provisionamiento sin duplicar ni fallar si ya existen.
    """
    call_command("loaddata", "roles", verbosity=0)


def create_initial_admin(*, email: str, password: str | None = None) -> tuple[User, str]:
    """
    Crea el usuario ADMIN_LAB inicial de un laboratorio recién provisionado y le
    asigna el rol. Debe llamarse dentro del `schema_context()` del tenant — no
    valida ni cambia el esquema activo.

    Devuelve `(user, password)`. Si `password` es `None`, se genera una temporal
    que el llamador decide si imprime o no (este service nunca la loguea).
    """
    seed_system_roles()

    if password is None:
        password = secrets.token_urlsafe(12)

    username = email.split("@")[0]
    user = User.objects.create_user(username=username, email=email, password=password)

    role = Role.objects.get(code=Role.Code.ADMIN_LAB)
    Membership.objects.create(user=user, role=role)

    return user, password
