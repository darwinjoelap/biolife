"""Catálogo mínimo con tubos para probar órdenes sin sembrar el catálogo completo."""
import datetime
from decimal import Decimal

from apps.billing.models import Currency, PriceList
from apps.billing.services.exchange import register_exchange_rate
from apps.billing.services.price_lists import set_price
from apps.catalog.models import SampleRequirement, Section, Test
from apps.catalog.services.profiles import create_profile
from apps.catalog.services.seeding_containers import seed_container_types
from apps.patients.models import Patient
from apps.patients.services.patient_creation import create_patient
from apps.settings_lab.models import TenantSettings

ST = Test.SampleType


def paciente(**kw) -> Patient:
    settings_obj = TenantSettings.get_solo()
    if not settings_obj.lab_initials:
        settings_obj.lab_initials = "LAB"
        settings_obj.save()
    data = {"first_name": "María", "last_name": "Pérez", "sex": Patient.Sex.F,
            "document_type": Patient.DocumentType.V, "document_number": "12345678",
            "birth_date": datetime.date(1990, 5, 4)}
    data.update(kw)
    return create_patient(**data)


def catalogo():
    """HEM (morado), COL y TRI (rojo), PT (azul), URO (frasco), DEP (24 h + rojo),
    GPC (rojo, toma «Post-carga 2 h»), EXT (rojo, tubo propio), SIN (sin tubo);
    perfil LIP = COL + TRI; lista GENERAL en USD con precio para todo menos SIN."""
    tubos = seed_container_types()
    seccion = Section.objects.create(code="S", name="Sección")
    specs = {
        "HEM": (ST.SANGRE_TOTAL, [("MORADO_EDTA", "", False)]),
        "COL": (ST.SUERO, [("ROJO_SECO", "", False)]),
        "TRI": (ST.SUERO, [("ROJO_SECO", "", False)]),
        "PT": (ST.PLASMA, [("AZUL_CITRATO", "", False)]),
        "URO": (ST.ORINA, [("FRASCO_ORINA", "", False)]),
        "DEP": (ST.ORINA_24H, [("ENVASE_ORINA_24H", "", False), ("ROJO_SECO", "", False)]),
        "GPC": (ST.SUERO, [("ROJO_SECO", "Post-carga 2 h", False)]),
        "EXT": (ST.SUERO, [("ROJO_SECO", "", True)]),
        "SIN": (ST.OTRO, []),
    }
    tests = {}
    for code, (sample_type, requirements) in specs.items():
        tests[code] = Test.objects.create(code=code, name=f"Examen {code}",
                                          section=seccion, sample_type=sample_type)
        for index, (tube, label, own) in enumerate(requirements):
            SampleRequirement.objects.create(
                test=tests[code], container_type=tubos[tube], collection_label=label,
                own_container=own, order_index=index,
            )
    tests["DEP"].requires_anthropometry = True
    tests["DEP"].save()
    lip = create_profile(code="LIP", name="Perfil lipídico", tests=[tests["COL"], tests["TRI"]])
    usd = Currency.objects.create(code="USD", name="Dólar", symbol="$", is_base=True)
    ves = Currency.objects.create(code="VES", name="Bolívar", symbol="Bs.")
    register_exchange_rate(from_currency=usd, to_currency=ves, rate=Decimal("100"),
                           effective_date=datetime.date(2020, 1, 1))
    lista = PriceList.objects.create(code="GENERAL", name="General", currency=usd,
                                     is_default=True)
    for code in ("HEM", "COL", "TRI", "PT", "URO", "DEP", "GPC", "EXT"):
        set_price(price_list=lista, test=tests[code], price=Decimal("10"))
    set_price(price_list=lista, profile=lip, price=Decimal("15"))
    return {"tubos": tubos, "tests": tests, "lip": lip, "lista": lista, "usd": usd,
            "ves": ves}
