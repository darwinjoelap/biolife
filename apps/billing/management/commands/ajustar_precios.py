from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from apps.billing.models import PriceList
from apps.billing.services.price_lists import adjust_prices
from apps.core.exceptions import ApplicationError


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise CommandError(f"Número inválido: {value}") from exc


class Command(BaseCommand):
    help = (
        "Ajusta en bloque los precios fijos de una lista. Ejemplo: python manage.py "
        "tenant_command ajustar_precios --schema=demo_uno --lista GENERAL --porcentaje 10 "
        "--redondeo 0.50"
    )

    def add_arguments(self, parser):
        parser.add_argument("--lista", required=True, help="Código de la lista de precios")
        parser.add_argument("--porcentaje", required=True, help="Ej.: 10 o -5,5")
        parser.add_argument("--redondeo", default=None, help="Múltiplo: 0.50, 1, 100...")
        parser.add_argument("--solo-examenes", action="store_true",
                            help="No ajustar los perfiles de precio fijo")

    def handle(self, *args, **options):
        try:
            price_list = PriceList.objects.get(code=options["lista"])
        except PriceList.DoesNotExist as exc:
            raise CommandError(f"No existe la lista {options['lista']}.") from exc
        try:
            changed = adjust_prices(
                price_list=price_list, percent=_decimal(options["porcentaje"]),
                round_to=_decimal(options["redondeo"]) if options["redondeo"] else None,
                include_profiles=not options["solo_examenes"],
            )
        except ApplicationError as exc:
            raise CommandError(exc.message) from exc
        self.stdout.write(self.style.SUCCESS(f"{changed} precios ajustados."))
