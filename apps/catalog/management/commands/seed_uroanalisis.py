from django.core.management.base import BaseCommand

from apps.catalog.services.seeding import seed_uroanalisis


class Command(BaseCommand):
    help = (
        "Siembra el examen URO (Uroanálisis) del tenant activo — Sección, Test, "
        "ParameterGroups, Parameters y CodedOptionSets. Idempotente: correrlo varias "
        "veces no duplica nada. Ejecutar con: "
        "python manage.py tenant_command seed_uroanalisis --schema=<schema_name>"
    )

    def handle(self, *args, **options):
        test = seed_uroanalisis()
        self.stdout.write(
            self.style.SUCCESS(
                f"Examen '{test.name}' ({test.code}) sembrado: "
                f"{test.parameter_groups.count()} grupos, {test.parameters.count()} parámetros."
            )
        )
