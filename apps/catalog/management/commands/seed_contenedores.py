from django.core.management.base import BaseCommand

from apps.catalog.models import SampleRequirement
from apps.catalog.services.seeding_containers import seed_containers


class Command(BaseCommand):
    help = (
        "Siembra los tubos/envases de toma y asigna tubo a cada examen que no tenga uno "
        "(Fase 09). Idempotente: no toca asignaciones existentes. Ejecutar con: "
        "python manage.py tenant_command seed_contenedores --schema=<schema_name>"
    )

    def handle(self, *args, **options):
        seed_containers()
        total = SampleRequirement.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Tubos sembrados; {total} asignaciones."))
