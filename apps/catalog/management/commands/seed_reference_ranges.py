from django.core.management.base import BaseCommand, CommandError

from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges
from apps.core.exceptions import ApplicationError


class Command(BaseCommand):
    help = (
        "Siembra los 4 exámenes mínimos de la Fase 06 (HEM_COMP, PERFIL_LIPIDICO, "
        "COAGUL, QUIM) y sus ReferenceRange, más el ReferenceRange cualitativo sobre "
        "URO_NITRITOS. Corre seed_uroanalisis() primero si hace falta (idempotente). "
        "Ejecutar con: python manage.py tenant_command seed_reference_ranges "
        "--schema=<schema_name>"
    )

    def handle(self, *args, **options):
        seed_uroanalisis()
        try:
            seed_reference_ranges()
        except ApplicationError as exc:
            raise CommandError(exc.message) from exc

        self.stdout.write(self.style.SUCCESS("Rangos de referencia sembrados."))
