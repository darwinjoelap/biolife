import re
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from apps.core.exceptions import ApplicationError
from apps.tenants.models import Plan, Subscription, Tenant

_SCHEMA_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,30}$")
_RESERVED_PREFIXES = ("public", "pg_", "information_schema")


def provision_tenant(
    *,
    name: str,
    schema_name: str,
    subdomain: str,
    plan: Plan | None = None,
    rif: str | None = None,
    trial_days: int = 30,
) -> Tenant:
    """
    Crea el laboratorio, su esquema, su dominio primario y su suscripción de prueba.
    Idempotente: si el schema_name ya existe, levanta ApplicationError sin tocar nada.

    Siempre se ejecuta en el esquema public, sin importar el esquema activo del
    llamador — django-tenants exige crear tenants únicamente desde ahí.
    """
    if not _SCHEMA_NAME_RE.match(schema_name) or schema_name.startswith(_RESERVED_PREFIXES):
        raise ApplicationError(
            f"'{schema_name}' no es un nombre de esquema válido.",
            extra={"schema_name": schema_name},
        )

    with schema_context(get_public_schema_name()):
        if Tenant.objects.filter(schema_name=schema_name).exists():
            raise ApplicationError(
                f"Ya existe un laboratorio con el esquema '{schema_name}'.",
                extra={"schema_name": schema_name},
            )

        with transaction.atomic():
            tenant = Tenant(
                name=name,
                schema_name=schema_name,
                rif=rif,
                trial_ends_at=timezone.now() + timedelta(days=trial_days),
            )
            try:
                tenant.save()  # crea el esquema (auto_create_schema=True)
            except Exception:
                # Si el esquema quedó a medias, django-tenants no lo limpia solo.
                Tenant.objects.filter(schema_name=schema_name).delete()
                raise

            base_domain = getattr(settings, "BASE_DOMAIN", "localhost")
            tenant.domains.create(domain=f"{subdomain}.{base_domain}", is_primary=True)

            if plan is not None:
                Subscription.objects.create(
                    tenant=tenant,
                    plan=plan,
                    status=Subscription.Status.TRIAL,
                    current_period_start=timezone.now(),
                    current_period_end=timezone.now() + timedelta(days=trial_days),
                )

    return tenant
