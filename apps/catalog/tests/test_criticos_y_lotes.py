from decimal import Decimal

from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import ReagentLot, ReferenceRange
from apps.catalog.services.reagent_lots import current_isi, set_current_lot
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_critical_values import seed_critical_values
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges


class CriticalSeedTests(TenantTestCase):
    def test_propuestos_sin_pisar_lo_del_laboratorio_ni_neonatos(self):
        seed_uroanalisis()
        seed_reference_ranges()
        hb = ReferenceRange.objects.filter(parameter__code="HEM_HEMOGLOBINA", sex="F").get()
        hb.critical_low = Decimal("6.5")
        hb.save()

        seed_critical_values()
        seed_critical_values()

        hb.refresh_from_db()
        assert hb.critical_low == Decimal("6.5") and hb.critical_note == ""
        k = ReferenceRange.objects.get(parameter__code="QUIM_POTASIO")
        assert (k.critical_low, k.critical_high) == (Decimal("2.8"), Decimal("6.2"))
        assert k.critical_note.startswith("PROPUESTO")
        neonatal = ReferenceRange.objects.filter(parameter__code="HEM_GLOBULOS_BLANCOS",
                                                 age_max_days__lt=365)
        assert all(r.critical_high is None for r in neonatal)


class ReagentLotTests(TenantTestCase):
    def test_un_solo_lote_vigente(self):
        assert current_isi() is None
        a = ReagentLot.objects.create(reagent="TROMBOPLASTINA", lot_number="A", isi=Decimal("1.1"))
        b = ReagentLot.objects.create(reagent="TROMBOPLASTINA", lot_number="B", isi=Decimal("1.3"))
        set_current_lot(lot=a)
        set_current_lot(lot=b)

        assert list(ReagentLot.objects.filter(is_current=True)) == [b]
        assert current_isi().isi == Decimal("1.3")
