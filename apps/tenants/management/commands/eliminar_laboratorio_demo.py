from django.core.management.base import BaseCommand, CommandError

from apps.core.exceptions import ApplicationError
from apps.tenants.services.decommission import delete_demo_tenant


class Command(BaseCommand):
    help = (
        "Borra un laboratorio en estado DEMO con su esquema, dominios y suscripciones "
        "(irreversible). Ej.: eliminar_laboratorio_demo --schema demo_dos --confirmar demo_dos"
    )

    def add_arguments(self, parser):
        parser.add_argument("--schema", required=True)
        parser.add_argument(
            "--confirmar", required=True, help="Repetir el nombre del esquema a borrar."
        )

    def handle(self, *args, **options):
        try:
            name = delete_demo_tenant(
                schema_name=options["schema"], confirmation=options["confirmar"]
            )
        except ApplicationError as exc:
            raise CommandError(exc.message) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Laboratorio '{name}' (esquema {options['schema']}) borrado."
        ))
