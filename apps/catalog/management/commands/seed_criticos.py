from django.core.management.base import BaseCommand

from apps.catalog.services.seeding_critical_values import seed_critical_values


class Command(BaseCommand):
    help = (
        "Completa valores críticos propuestos (literatura) en rangos sin críticos (Fase 10). "
        "No pisa lo cargado por el laboratorio. Ejecutar con: "
        "python manage.py tenant_command seed_criticos --schema=<schema_name>"
    )

    def handle(self, *args, **options):
        updated = seed_critical_values()
        self.stdout.write(self.style.SUCCESS(f"Críticos propuestos en {updated} rango(s)."))
