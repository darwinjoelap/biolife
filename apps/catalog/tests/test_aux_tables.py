"""Tablas auxiliares sin /admin (Fase 11d)."""
from decimal import Decimal

from apps.accounts.models import AuditLog, Membership, Role, User
from apps.billing.models import Currency, Discount
from apps.billing.services.seeding import seed_billing_defaults
from apps.catalog.models import (
    CodedOptionSet,
    ObservationTemplate,
    ReagentLot,
    Section,
    Test,
    Unit,
)
from apps.catalog.tests.test_catalog_screens import CatalogBase, form_data


class AuxBase(CatalogBase):
    def setUp(self):
        super().setUp()
        user = User.objects.create_user(username="aux", password="x")
        Membership.objects.create(user=user, role=Role.objects.get(code="AUXILIAR_TOMA"))
        self.users["AUXILIAR_TOMA"] = user

    def screen(self, url):
        ctx = self.client.get(url).context
        formsets = [fs for _, fs, _ in ctx["formsets"]]
        return form_data(ctx["form"], *formsets), formsets


class HubTests(AuxBase):
    def test_indice_segun_rol(self):
        body = self.client.get("/tablas/").content.decode()
        for title in ("Secciones", "Unidades", "Listas de opciones", "Tubos y envases",
                      "Lotes de reactivos", "Monedas", "Descuentos"):
            assert title in body
        self.login("TECNICO")
        assert self.client.get("/tablas/unidades/").status_code == 200
        assert self.client.get("/tablas/unidades/nuevo/").status_code == 403
        self.login("AUXILIAR_TOMA")
        assert self.client.get("/tablas/").status_code == 403
        assert self.client.get("/tablas/no-existe/").status_code == 404

    def test_menu_ya_no_manda_a_admin(self):
        body = self.client.get("/tablas/").content.decode()
        assert "/admin/catalog/" not in body and 'href="/tablas/"' in body


class CatalogTablesTests(AuxBase):
    def test_crear_unidad_queda_en_bitacora(self):
        data, _ = self.screen("/tablas/unidades/nuevo/")
        data.update({"symbol": "copias/mL", "description": "Copias por mililitro",
                     "is_active": "on"})
        response = self.client.post("/tablas/unidades/nuevo/", data)
        unit = Unit.objects.get(symbol="copias/mL")
        assert response.status_code == 302 and str(unit.pk) in response["Location"]
        assert AuditLog.objects.filter(action="TABLA_CREADA",
                                       model_name="catalog.Unit").exists()

    def test_seccion_en_uso_conserva_el_codigo(self):
        section = Test.objects.get(code="HEM_COMP").section
        url = f"/tablas/secciones/{section.pk}/"
        data, _ = self.screen(url)
        data.update({"code": "OTRO", "name": "HEMATOLOGÍA GENERAL"})
        self.client.post(url, data)
        section.refresh_from_db()
        assert section.name == "HEMATOLOGÍA GENERAL" and section.code != "OTRO"

    def test_bioanalista_agrega_opcion_y_la_lista_no_queda_vacia(self):
        self.login("BIOANALISTA")
        data, (options,) = self.screen("/tablas/opciones/nuevo/")
        data.update({"code": "hallazgo x", "name": "Hallazgo X", "is_active": "on",
                     "opciones-0-value": "PRESENTE", "opciones-0-order_index": 1,
                     "opciones-0-is_active": "on"})
        self.client.post("/tablas/opciones/nuevo/", data)
        option_set = CodedOptionSet.objects.get(code="HALLAZGO_X")
        assert list(option_set.options.values_list("value", flat=True)) == ["PRESENTE"]

        url = f"/tablas/opciones/{option_set.pk}/"
        data, _ = self.screen(url)
        data.pop("opciones-0-is_active")
        response = self.client.post(url, data)
        assert "al menos una opción activa" in response.content.decode()
        assert option_set.options.get().is_active

        self.login("TECNICO")
        assert self.client.post(url, data).status_code == 403

    def test_observacion_general_no_mezcla_las_de_examen(self):
        test = Test.objects.get(code="HEM_COMP")
        ObservationTemplate.objects.create(text="SÓLO DE HEMATOLOGÍA", test=test)
        data, _ = self.screen("/tablas/observaciones/nuevo/")
        data.update({"text": "MUESTRA HEMOLIZADA", "order_index": 1, "is_active": "on"})
        self.client.post("/tablas/observaciones/nuevo/", data)
        body = self.client.get("/tablas/observaciones/").content.decode()
        assert "MUESTRA HEMOLIZADA" in body and "SÓLO DE HEMATOLOGÍA" not in body
        assert ObservationTemplate.objects.get(text="MUESTRA HEMOLIZADA").test is None


class LotTests(AuxBase):
    def test_tecnico_registra_lote_nuevo_y_desplaza_al_vigente(self):
        old = ReagentLot.objects.create(reagent="TROMBOPLASTINA", lot_number="A1",
                                        isi=Decimal("1.1"), is_current=True)
        self.login("TECNICO")
        data, _ = self.screen("/tablas/lotes/nuevo/")
        data.update({"reagent": "TROMBOPLASTINA", "lot_number": "b2", "is_current": "on",
                     "is_active": "on"})
        response = self.client.post("/tablas/lotes/nuevo/", data)
        assert "Indique el ISI" in response.content.decode()
        data["isi"] = "1.05"
        self.client.post("/tablas/lotes/nuevo/", data)
        new = ReagentLot.objects.get(lot_number="B2")
        old.refresh_from_db()
        assert new.is_current and not old.is_current
        self.login("FACTURACION")
        assert self.client.post(f"/tablas/lotes/{new.pk}/", data).status_code == 403


class MoneyTablesTests(AuxBase):
    def setUp(self):
        super().setUp()
        seed_billing_defaults()

    def test_moneda_nueva_no_es_base_y_la_base_no_se_desactiva(self):
        self.login("FACTURACION")
        data, _ = self.screen("/tablas/monedas/nuevo/")
        data.update({"code": "eur", "name": "Euro", "symbol": "€", "decimals": 2,
                     "order_index": 3, "is_active": "on"})
        self.client.post("/tablas/monedas/nuevo/", data)
        assert Currency.objects.get(code="EUR").is_base is False

        base = Currency.objects.get(is_base=True)
        url = f"/tablas/monedas/{base.pk}/"
        data, _ = self.screen(url)
        data.pop("is_active")
        response = self.client.post(url, data)
        assert "no se puede desactivar" in response.content.decode()
        base.refresh_from_db()
        assert base.is_active

        self.login("BIOANALISTA")
        assert self.client.post(url, data).status_code == 403

    def test_descuento_por_examen_exige_examenes(self):
        data, _ = self.screen("/tablas/descuentos/nuevo/")
        data.update({"code": "tercera edad", "name": "Tercera edad", "kind": "PERCENT",
                     "value": "150", "scope": "ITEM", "order_index": 1, "is_active": "on"})
        response = self.client.post("/tablas/descuentos/nuevo/", data).content.decode()
        assert "no pasa de 100" in response and "al menos un examen" in response
        data.update({"value": "15", "tests": [Test.objects.get(code="HEM_COMP").pk]})
        self.client.post("/tablas/descuentos/nuevo/", data)
        discount = Discount.objects.get(code="TERCERA_EDAD")
        assert discount.tests.count() == 1 and discount.currency is None

    def test_inactivos_se_ven_con_el_filtro(self):
        Section.objects.create(code="VIEJA", name="SECCIÓN VIEJA", is_active=False)
        assert "SECCIÓN VIEJA" not in self.client.get("/tablas/secciones/").content.decode()
        assert "SECCIÓN VIEJA" in self.client.get(
            "/tablas/secciones/?inactivos=1").content.decode()


class OptionLockTests(AuxBase):
    def test_con_resultados_el_texto_de_las_opciones_queda_fijo(self):
        from apps.catalog.aux_forms import OptionFormSet
        option_set = CodedOptionSet.objects.filter(options__isnull=False).first()
        formset = OptionFormSet(instance=option_set, prefix="opciones", values_locked=True)
        existing = [f for f in formset.forms if not f.instance._state.adding]
        new = [f for f in formset.forms if f.instance._state.adding]
        assert existing and all(f.fields["value"].disabled for f in existing)
        assert new and not any(f.fields["value"].disabled for f in new)
        assert not any(f.fields["is_active"].disabled for f in existing)
