"""Baja de laboratorios de demostración (ADR-023).

`Tenant.auto_drop_schema` sigue en False (ADR-003): un `delete()` accidental nunca borra
un esquema. Esta es la única vía para borrar uno, y sólo acepta laboratorios en estado
DEMO: un laboratorio con datos clínicos reales (ACTIVO, SUSPENDIDO, MOROSO, CANCELADO) no se
borra físicamente nunca.
"""
from django_tenants.utils import get_public_schema_name, schema_context

from apps.core.exceptions import ApplicationError
from apps.tenants.models import Tenant


def delete_demo_tenant(*, schema_name: str, confirmation: str) -> str:
    """Borra el laboratorio DEMO `schema_name`, su esquema, dominios y suscripciones.

    `confirmation` debe repetir el nombre del esquema. Devuelve el nombre del laboratorio.
    """
    if confirmation != schema_name:
        raise ApplicationError(
            "La confirmación no coincide con el esquema: no se borró nada.",
            extra={"schema_name": schema_name},
        )
    public = get_public_schema_name()
    if schema_name == public:
        raise ApplicationError("El esquema public no se puede borrar.")

    with schema_context(public):
        tenant = Tenant.objects.filter(schema_name=schema_name).first()
        if tenant is None:
            raise ApplicationError(
                f"No existe un laboratorio con el esquema '{schema_name}'.",
                extra={"schema_name": schema_name},
            )
        if tenant.status != Tenant.Status.DEMO:
            raise ApplicationError(
                f"'{tenant.name}' está en estado {tenant.get_status_display()}: sólo se "
                "borran laboratorios de demostración. Un laboratorio real se cancela, "
                "no se borra.",
                extra={"schema_name": schema_name, "status": tenant.status},
            )
        name = tenant.name
        tenant.delete(force_drop=True)  # esquema + dominios + suscripciones
    return name
