from django.core.management.base import BaseCommand, CommandError

from apps.core.exceptions import ApplicationError
from apps.tenants.services.provisioning import provision_tenant


class Command(BaseCommand):
    help = "Crea un nuevo laboratorio (tenant) con su esquema y dominio."

    def add_arguments(self, parser):
        parser.add_argument("--nombre", required=True)
        parser.add_argument("--schema", required=True)
        parser.add_argument("--subdominio", required=True)
        parser.add_argument("--rif", default=None)
        parser.add_argument("--trial-dias", type=int, default=30)

    def handle(self, *args, **options):
        try:
            tenant = provision_tenant(
                name=options["nombre"],
                schema_name=options["schema"],
                subdomain=options["subdominio"],
                rif=options["rif"],
                trial_days=options["trial_dias"],
            )
        except ApplicationError as exc:
            raise CommandError(exc.message) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Laboratorio '{tenant.name}' creado (esquema: {tenant.schema_name})."
            )
        )
