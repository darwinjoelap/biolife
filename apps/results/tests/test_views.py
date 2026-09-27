from django_tenants.test.client import TenantClient

from apps.accounts.models import Membership, Role, User
from apps.accounts.services.user_management import seed_system_roles
from apps.catalog.models import Parameter
from apps.orders.models import Order
from apps.results.models import CriticalNotification, Result, ResultValue
from apps.results.tests.test_results import ResultsTestBase


class ResultsViewsTests(ResultsTestBase):
    def setUp(self):
        super().setUp()
        seed_system_roles()
        Membership.objects.create(user=self.tech, role=Role.objects.get(code="TECNICO"))
        Membership.objects.create(user=self.bio, role=Role.objects.get(code="BIOANALISTA"))
        self.client = TenantClient(self.tenant)
        self.order_obj = self.order("ELECTROLITOS", "HDL")
        self.url = f"/resultados/orden/{self.order_obj.pk}/"

    def post_values(self, url=None, **values):
        params = {p.code: p for p in Parameter.objects.filter(code__in=values)}
        data = {f"v_{params[c].pk}": v for c, v in values.items()}
        return self.client.post(url or self.url, data)

    def test_bandeja_y_captura_en_vivo(self):
        self.client.force_login(self.tech)
        html = self.client.get("/resultados/").content.decode()
        assert self.order_obj.number in html and "ELECTROLITOS SÉRICOS" in html

        live = self.post_values(self.url + "calcular/", QUIM_POTASIO="6,9").content.decode()
        assert 'hx-swap-oob="true"' in live and "CRÍTICO" in live
        assert not ResultValue.objects.exists()

    def test_tecnico_carga_pero_no_valida(self):
        self.client.force_login(self.tech)
        response = self.post_values(QUIM_SODIO="140", QUIM_POTASIO="4,2", QUIM_CLORO="101",
                                    LIP_HDL="50")
        assert response.status_code == 302
        assert Result.objects.filter(status=Result.Status.CARGADO).count() == 2
        assert self.client.post(self.url + "validar/").status_code == 403

        self.client.force_login(self.bio)
        self.client.post(self.url + "validar/")
        self.order_obj.refresh_from_db()
        assert self.order_obj.status == Order.Status.VALIDADA

    def test_aviso_de_critico_desde_la_pantalla(self):
        self.client.force_login(self.bio)
        self.post_values(QUIM_SODIO="140", QUIM_POTASIO="6,9", QUIM_CLORO="101")
        potasio = ResultValue.objects.get(parameter__code="QUIM_POTASIO")
        assert "Valor crítico por avisar" in self.client.get(self.url).content.decode()

        self.client.post(f"{self.url}valores/{potasio.pk}/aviso/", {
            "value_confirmed": "on", "notified_to": "Dr. Pérez", "method": "LLAMADA"})

        notice = CriticalNotification.objects.get()
        assert (notice.value_display, notice.created_by) == ("6,9", self.bio)
        assert "Valor crítico por avisar" not in self.client.get(self.url).content.decode()

    def test_valor_invalido_no_guarda_y_conserva_lo_escrito(self):
        self.client.force_login(self.tech)
        response = self.post_values(QUIM_SODIO="abc", LIP_HDL="50")
        html = response.content.decode()
        assert response.status_code == 400 and "no es un número" in html
        assert 'value="abc"' in html  # lo escrito no se pierde
        assert not ResultValue.objects.exists()

    def test_datos_clinicos_y_solo_lectura(self):
        self.client.force_login(self.tech)
        self.client.post(self.url + "datos/", {"weight_kg": "62", "height_cm": "165",
                                               "urine_volume_24h_ml": "", "patient_condition":
                                               "EMBARAZO"})
        self.order_obj.refresh_from_db()
        assert (self.order_obj.weight_kg, self.order_obj.patient_condition) == (62, "EMBARAZO")

        viewer = User.objects.create_user(username="v", email="v@lab.test", password="x")
        Membership.objects.create(user=viewer, role=Role.objects.get(code="SOLO_LECTURA"))
        self.client.force_login(viewer)
        assert self.client.get(self.url).status_code == 200
        assert self.post_values(LIP_HDL="50").status_code == 403
