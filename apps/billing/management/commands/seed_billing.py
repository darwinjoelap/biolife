from django.core.management.base import BaseCommand

from apps.billing.services.seeding import seed_billing_defaults


class Command(BaseCommand):
    help = (
        "Crea las monedas USD (base) y VES y la lista de precios GENERAL vacía. "
        "Idempotente. Ejecutar con: python manage.py tenant_command seed_billing "
        "--schema=<schema_name>"
    )

    def handle(self, *args, **options):
        price_list = seed_billing_defaults()
        self.stdout.write(self.style.SUCCESS(f"Monedas y lista {price_list.code} listas."))
