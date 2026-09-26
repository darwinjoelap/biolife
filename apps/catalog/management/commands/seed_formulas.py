from django.core.management.base import BaseCommand, CommandError

from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_formulas import seed_formulas
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges
from apps.core.exceptions import ApplicationError


class Command(BaseCommand):
    help = (
        "Siembra los parámetros y las 16 fórmulas de la Fase 07 (CHCM, globulinas, "
        "Friedewald, Castelli, INR, depuración de creatinina...). Corre antes las "
        "siembras de las Fases 05 y 06 (idempotentes). Ejecutar con: "
        "python manage.py tenant_command seed_formulas --schema=<schema_name>"
    )

    def handle(self, *args, **options):
        try:
            seed_uroanalisis()
            seed_reference_ranges()
            seed_formulas()
        except ApplicationError as exc:
            raise CommandError(exc.message) from exc

        self.stdout.write(self.style.SUCCESS("Fórmulas sembradas."))
