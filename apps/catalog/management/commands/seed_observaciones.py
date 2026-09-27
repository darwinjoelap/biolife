from django.core.management.base import BaseCommand

from apps.catalog.services.seeding_observations import seed_observation_templates


class Command(BaseCommand):
    help = (
        "Siembra observaciones predefinidas por examen/sección (Fase 10). Idempotente. "
        "Ejecutar con: python manage.py tenant_command seed_observaciones --schema=<schema>"
    )

    def handle(self, *args, **options):
        created = seed_observation_templates()
        self.stdout.write(self.style.SUCCESS(f"{created} observación(es) nueva(s)."))
