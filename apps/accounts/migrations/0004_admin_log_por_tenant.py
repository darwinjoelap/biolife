"""ADR-020: `django.contrib.admin` pasa a TENANT_APPS.

En los esquemas de tenant ya existentes, las migraciones de `admin` figuran como aplicadas
(django-tenants las registra aunque el router no creó la tabla), así que `migrate_schemas`
no crearía `django_admin_log`. Esta migración la crea si falta en el esquema actual. En
`public` y en tenants nuevos no hace nada.
"""
from django.db import migrations
from django_tenants.utils import get_public_schema_name


def crear_bitacora_admin(apps, schema_editor):
    connection = schema_editor.connection
    if connection.schema_name == get_public_schema_name():
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name = 'django_admin_log'"
        )
        if cursor.fetchone():
            return
    schema_editor.create_model(apps.get_model("admin", "LogEntry"))


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_auditlog"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(crear_bitacora_admin, migrations.RunPython.noop),
    ]
