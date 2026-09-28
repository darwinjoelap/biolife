from decimal import Decimal

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.accounts.models import AuditLog, Membership, Role, User
from apps.accounts.services.user_management import seed_system_roles
from apps.billing.models import ExchangeRate, PriceList, PriceListItem
from apps.billing.services.seeding import seed_billing_defaults
from apps.catalog.models import Parameter, Profile, ReferenceRange, Test
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_containers import seed_containers
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges


def _value(bound):
    value = bound.value()
    value = getattr(value, "pk", value)
    if value is True:
        return "on"
    if value is False or value is None:
        return None
    return value


def form_data(*items) -> dict:
    """POST con los valores que muestra la pantalla (formularios y formsets)."""
    data = {}
    for item in items:
        if hasattr(item, "management_form"):
            for bound in item.management_form:
                data[bound.html_name] = bound.value()
            forms = item.forms
        else:
            forms = [item]
        for form in forms:
            for bound in form:
                if bound.field.disabled:
                    continue
                value = _value(bound)
                if isinstance(value, list):
                    data[bound.html_name] = [getattr(v, "pk", v) for v in value]
                elif value is not None:
                    data[bound.html_name] = value
    return data


class CatalogBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        seed_system_roles()
        seed_uroanalisis()
        seed_reference_ranges()
        seed_containers()
        self.users = {}
        for code in ("ADMIN_LAB", "BIOANALISTA", "TECNICO", "FACTURACION"):
            user = User.objects.create_user(username=code.lower(), password="x")
            Membership.objects.create(user=user, role=Role.objects.get(code=code))
            self.users[code] = user
        self.client = TenantClient(self.tenant)
        self.login("ADMIN_LAB")

    def login(self, code):
        self.client.force_login(self.users[code])


class TestScreenTests(CatalogBase):
    def test_crear_examen_con_tubo_grupo_y_parametro_con_rango(self):
        response = self.client.get("/catalogo/examenes/nuevo/")
        ctx = response.context
        data = form_data(ctx["form"], ctx["reqs"], ctx["groups"], ctx["obs"])
        from apps.catalog.models import ContainerType, Section
        data.update({
            "code": "ferritina", "name": "FERRITINA", "sample_type": "SUERO",
            "section": Section.objects.first().pk, "is_active": "on",
            "tubos-0-container_type": ContainerType.objects.get(code="ROJO_SECO").pk,
            "tubos-0-order_index": 0, "grupos-0-name": "", "obs-0-text": "",
        })
        response = self.client.post("/catalogo/examenes/nuevo/", data)
        test = Test.objects.get(code="FERRITINA")
        assert response.status_code == 302
        assert test.sample_requirements.count() == 1
        assert AuditLog.objects.filter(action="EXAMEN_GUARDADO").exists()

        url = f"/catalogo/examenes/{test.pk}/parametros/nuevo/"
        form = self.client.get(url).context["form"]
        data = form_data(form)
        data.update({"code": "FERR", "name": "FERRITINA", "value_type": "NUMERIC",
                     "decimals": 1, "order_index": 1, "is_printable": "on",
                     "is_active": "on"})
        response = self.client.post(url, data)
        parameter = Parameter.objects.get(code="FERR")
        assert response.status_code == 302

        ctx = self.client.get(f"/catalogo/parametros/{parameter.pk}/").context
        data = form_data(ctx["form"], ctx["ranges"])
        new = f"{ctx['ranges'].prefix}-0"
        data.update({f"{new}-sex": "ANY", f"{new}-condition": "NINGUNA",
                     f"{new}-priority": 0, f"{new}-range_type": "CLOSED",
                     f"{new}-low": "30", f"{new}-high": "400",
                     f"{new}-display_text": "30 - 400 ng/mL", f"{new}-is_active": "on"})
        self.client.post(f"/catalogo/parametros/{parameter.pk}/", data)
        assert ReferenceRange.objects.get(parameter=parameter).display_text == "30 - 400 ng/mL"

    def test_formula_invalida_no_se_guarda(self):
        test = Test.objects.get(code="HEM_COMP")
        url = f"/catalogo/examenes/{test.pk}/parametros/nuevo/"
        data = form_data(self.client.get(url).context["form"])
        data.update({"code": "X_CALC", "name": "X", "value_type": "NUMERIC_CALCULATED",
                     "decimals": 1, "order_index": 9, "formula": "{NO_EXISTE} * 2",
                     "is_active": "on"})
        response = self.client.post(url, data)
        assert response.status_code == 200 and "no existen" in response.content.decode()
        assert not Parameter.objects.filter(code="X_CALC").exists()

    def test_bioanalista_cambia_rangos_pero_no_datos(self):
        parameter = Parameter.objects.get(code="HEM_HEMOGLOBINA")
        url = f"/catalogo/parametros/{parameter.pk}/"
        self.login("BIOANALISTA")
        ctx = self.client.get(url).context
        assert ctx["form"].fields["name"].disabled
        data = form_data(ctx["form"], ctx["ranges"])
        data["name"] = "OTRO NOMBRE"
        first = f"{ctx['ranges'].prefix}-0"
        data[f"{first}-display_text"] = "12,1 - 16,0 g/dL"
        self.client.post(url, data)
        parameter.refresh_from_db()
        assert parameter.name == "HEMOGLOBINA"
        assert parameter.reference_ranges.filter(display_text="12,1 - 16,0 g/dL").exists()

        self.login("TECNICO")
        assert self.client.post(url, data).status_code == 403
        assert self.client.get(url).status_code == 200  # consulta

    def test_perfil_con_orden_y_aviso_de_insumos(self):
        codes = ["LDL_VLDL", "COLESTEROL_TOTAL"]
        ids = [str(Test.objects.get(code=c).pk) for c in codes]
        response = self.client.post("/catalogo/perfiles/nuevo/", {
            "code": "lip2", "name": "LÍPIDOS 2", "order_index": 5, "is_active": "on",
            "tests": ids}, follow=True)
        profile = Profile.objects.get(code="LIP2")
        assert [pt.test.code for pt in profile.profile_tests.order_by("order_index")] == codes
        assert "alimentan sus cálculos" in response.content.decode()


class PriceScreenTests(CatalogBase):
    def setUp(self):
        super().setUp()
        self.price_list = seed_billing_defaults()
        self.test = Test.objects.get(code="HEM_COMP")

    def test_precio_en_la_fila_y_quitarlo(self):
        url = f"/precios/{self.price_list.pk}/precio/"
        html = self.client.post(url, {"kind": "test", "id": self.test.pk,
                                      "mode": "FIXED", "price": "1.250,50"}).content.decode()
        item = PriceListItem.objects.get(test=self.test)
        assert item.price == Decimal("1250.50") and "Guardado" in html
        self.client.post(url, {"kind": "test", "id": self.test.pk, "mode": "FIXED",
                               "price": ""})
        item.refresh_from_db()
        assert not item.is_active
        assert "Sin precio" in self.client.get("/precios/").content.decode()

    def test_ajuste_tasa_y_copia(self):
        url = f"/precios/{self.price_list.pk}/precio/"
        self.client.post(url, {"kind": "test", "id": self.test.pk, "price": "10"})
        self.client.post(f"/precios/{self.price_list.pk}/ajustar/",
                         {"percent": "10", "round_to": "", "include_profiles": "on"})
        assert PriceListItem.objects.get(test=self.test).price == Decimal("11.00")

        from apps.billing.models import Currency
        ves = Currency.objects.get(code="VES")
        self.client.post("/precios/tasa/", {"currency": ves.pk, "rate": "150",
                                            "effective_date": "2026-09-28"})
        assert ExchangeRate.objects.get(to_currency=ves).rate == 150
        self.client.post(f"/precios/{self.price_list.pk}/copiar/", {
            "code": "bs", "name": "Bolívares", "currency": ves.pk, "percent": "0",
            "round_to": "1"})
        copy = PriceList.objects.get(code="BS")
        assert copy.items.get(test=self.test).price == Decimal("1650.00")

    def test_quien_puede_editar_precios(self):
        url = f"/precios/{self.price_list.pk}/precio/"
        self.login("FACTURACION")
        assert self.client.post(url, {"kind": "test", "id": self.test.pk,
                                      "price": "5"}).status_code == 200
        self.login("BIOANALISTA")
        assert self.client.post(url, {"kind": "test", "id": self.test.pk,
                                      "price": "6"}).status_code == 403
        assert self.client.get("/precios/").status_code == 200
