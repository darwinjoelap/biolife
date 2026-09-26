from django.core.management.base import BaseCommand, CommandError

from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_profiles import seed_profiles
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges
from apps.core.exceptions import ApplicationError


class Command(BaseCommand):
    help = (
        "Siembra el catálogo base completo (Uroanálisis, ~55 exámenes con rangos y "
        "fórmulas) y los perfiles de la Fase 08. Idempotente y no destructivo: no toca "
        "perfiles que ya existan. Ejecutar con: "
        "python manage.py tenant_command seed_profiles --schema=<schema_name>"
    )

    def handle(self, *args, **options):
        try:
            seed_uroanalisis()
            seed_reference_ranges()
            profiles = seed_profiles()
        except ApplicationError as exc:
            raise CommandError(exc.message) from exc

        self.stdout.write(self.style.SUCCESS(f"Catálogo y {len(profiles)} perfiles sembrados."))
