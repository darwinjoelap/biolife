from django.core.management.base import BaseCommand, CommandError

from apps.core.exceptions import ApplicationError
from apps.tenants.services.provisioning import provision_tenant


class Command(BaseCommand):
    help = "Crea un nuevo laboratorio (tenant) con su esquema y dominio."

    def add_arguments(self, parser):
        parser.add_argument("--nombre", required=True)
        parser.add_argument("--schema", required=True)
        parser.add_argument("--subdominio", required=True)
        parser.add_argument("--admin-email", required=True)
        parser.add_argument("--admin-password", default=None)
        parser.add_argument("--rif", default=None)
        parser.add_argument("--trial-dias", type=int, default=30)
        parser.add_argument(
            "--sin-catalogo", action="store_true",
            help="No sembrar catálogo, perfiles ni monedas (el laboratorio nace vacío).",
        )

    def handle(self, *args, **options):
        try:
            tenant, admin_password = provision_tenant(
                name=options["nombre"],
                schema_name=options["schema"],
                subdomain=options["subdominio"],
                admin_email=options["admin_email"],
                admin_password=options["admin_password"],
                rif=options["rif"],
                trial_days=options["trial_dias"],
                seed_catalog=not options["sin_catalogo"],
            )
        except ApplicationError as exc:
            raise CommandError(exc.message) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Laboratorio '{tenant.name}' creado (esquema: {tenant.schema_name})."
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f"Usuario admin: {options['admin_email']} — contraseña temporal: "
                f"{admin_password}\n"
                "Guárdala ahora: no queda registrada en ningún log ni se puede recuperar."
            )
        )
