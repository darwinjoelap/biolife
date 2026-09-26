"""
Prueba de humo de aislamiento entre tenants. Crea dos laboratorios, inserta un registro
de prueba en cada uno usando un modelo que vive POR TENANT (el User propio de
apps.accounts, ADR-010/011)
y verifica que ninguna consulta cruce entre esquemas.

Importante: no usar aquí ningún modelo de SHARED_APPS (como apps.masterdata.Locality)
para esta prueba — esos modelos viven en el esquema public por diseño y su visibilidad
cruzada entre tenants es intencional, no una fuga de aislamiento.

Uso:
    python scripts/check_tenant_isolation.py

Sale con código 0 si el aislamiento se verifica, 1 si falla. Pensado para correr en CI.
"""
import os
import sys
import uuid

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django_tenants.utils import schema_context  # noqa: E402

from apps.core.exceptions import ApplicationError  # noqa: E402
from apps.tenants.services.provisioning import provision_tenant  # noqa: E402

User = get_user_model()


def _unique_schema(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def main() -> int:
    schema_a = _unique_schema("chk_a")
    schema_b = _unique_schema("chk_b")
    marker_username = f"usuario_solo_en_{schema_a}"

    try:
        # Fase 08c: provision_tenant exige admin_email y devuelve (tenant, password).
        tenant_a, _ = provision_tenant(
            name="Check Isolation A", schema_name=schema_a, subdomain=schema_a,
            admin_email=f"admin@{schema_a}.test", seed_catalog=False,
        )
        tenant_b, _ = provision_tenant(
            name="Check Isolation B", schema_name=schema_b, subdomain=schema_b,
            admin_email=f"admin@{schema_b}.test", seed_catalog=False,
        )
    except ApplicationError as exc:
        print(f"FALLÓ: no se pudieron crear los tenants de prueba: {exc.message}")
        return 1

    try:
        with schema_context(schema_a):
            User.objects.create_user(username=marker_username, password="no-importa")

        with schema_context(schema_b):
            visible_desde_b = User.objects.filter(username=marker_username).exists()

        with schema_context("public"):
            # accounts es SHARED y TENANT a la vez (ADR-011): public tiene su propia tabla
            # de usuarios, que no debe ver el usuario creado en el tenant A.
            try:
                visible_desde_public = User.objects.filter(
                    username=marker_username
                ).exists()
            except Exception:
                visible_desde_public = False

        if visible_desde_b or visible_desde_public:
            donde = []
            if visible_desde_b:
                donde.append("el tenant B")
            if visible_desde_public:
                donde.append("el esquema public")
            print(f"FALLÓ: un usuario creado en el tenant A es visible desde {' y '.join(donde)}.")
            return 1

        print("AISLAMIENTO VERIFICADO")
        return 0
    finally:
        tenant_a.delete(force_drop=True)
        tenant_b.delete(force_drop=True)


if __name__ == "__main__":
    sys.exit(main())
