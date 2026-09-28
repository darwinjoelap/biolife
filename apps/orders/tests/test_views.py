from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.accounts.models import Membership, Role, User
from apps.accounts.services.user_management import seed_system_roles
from apps.orders.models import Order, Sample
from apps.orders.services.order_creation import create_order
from apps.orders.tests.factories import catalogo, paciente
from apps.patients.models import Patient


class ReceptionViewsTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.c = catalogo()
        self.t = self.c["tests"]
        self.patient = paciente()
        seed_system_roles()
        self.user = User.objects.create_user(username="recep", email="r@lab.test",
                                             password="x")
        Membership.objects.create(user=self.user, role=Role.objects.get(code="RECEPCION"))
        self.client = TenantClient(self.tenant)
        self.client.force_login(self.user)

    def _post_order(self, **extra):
        data = {"patient": self.patient.pk, "tests": [self.t["HEM"].pk, self.t["PT"].pk],
                "profiles": [self.c["lip"].pk], "priority": "URGENTE",
                "price_list": self.c["lista"].pk, "reference_currency": self.c["ves"].pk}
        data.update(extra)
        return self.client.post("/ordenes/nueva/", data)

    def test_registrar_orden_y_ver_detalle(self):
        response = self._post_order()

        order = Order.objects.get()
        assert response.status_code == 302 and response.url == f"/ordenes/{order.pk}/"
        assert order.priority == "URGENTE" and order.created_by == self.user
        assert order.samples.count() == 3
        detail = self.client.get(response.url).content.decode()
        assert order.number in detail and "Tubo azul" in detail

    def test_resumen_en_vivo_no_guarda(self):
        response = self.client.post("/ordenes/nueva/resumen/", {
            "tests": [self.t["HEM"].pk, self.t["PT"].pk], "profiles": [self.c["lip"].pk],
            "priority": "NORMAL", "price_list": self.c["lista"].pk,
        })

        html = response.content.decode()
        assert response.status_code == 200 and Order.objects.count() == 0
        assert "Tubo azul" in html and "Tubo rojo" in html and "Tubo morado" in html
        assert "35,00" in html

    def test_busquedas_de_examenes_y_pacientes(self):
        html = self.client.get("/ordenes/buscar/examenes/", {"oq": "lip"}).content.decode()
        assert "Perfil lipídico" in html
        html = self.client.get("/ordenes/buscar/pacientes/", {"pq": "12345"}).content.decode()
        assert "Pérez" in html

    def test_etiquetas_pdf(self):
        self._post_order()
        order = Order.objects.get()

        response = self.client.get(f"/ordenes/{order.pk}/etiquetas.pdf")

        assert response["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

    def test_tomar_rechazar_pagar_y_anular(self):
        self._post_order()
        order = Order.objects.get()
        first = order.samples.get(sequence=1)

        self.client.post(f"/ordenes/{order.pk}/tomar/", {"muestra": first.pk})
        self.client.post(f"/ordenes/{order.pk}/muestras/{first.pk}/rechazar/",
                         {"reason": "Coagulada"})
        self.client.post(f"/ordenes/{order.pk}/pagar/")

        order.refresh_from_db()
        assert order.is_paid
        assert order.samples.filter(status=Sample.Status.RECHAZADA).count() == 1
        assert order.samples.count() == 4
        response = self.client.post(f"/ordenes/{order.pk}/anular/", {"reason": "Prueba"},
                                    follow=True)
        order.refresh_from_db()
        assert order.status == Order.Status.ANULADA
        assert "anulada" in response.content.decode()

    def test_marcar_tomada_despues_de_cargar_resultados(self):
        self._post_order()
        order = Order.objects.get()
        Order.objects.filter(pk=order.pk).update(status=Order.Status.RESULTADOS_CARGADOS)
        html = self.client.get(f"/ordenes/{order.pk}/").content.decode()
        assert "Marcar todas tomadas" in html
        self.client.post(f"/ordenes/{order.pk}/tomar/")
        assert not order.samples.filter(status=Sample.Status.PENDIENTE).exists()
        order.refresh_from_db()
        assert order.status == Order.Status.RESULTADOS_CARGADOS  # no retrocede

    def test_lector_de_codigo_de_barras_va_directo_a_la_orden(self):
        order, _ = create_order(patient=self.patient, tests=[self.t["HEM"]],
                                price_list=self.c["lista"])
        barcode = order.samples.get().barcode

        response = self.client.get("/ordenes/", {"q": barcode})

        assert response.status_code == 302 and response.url == f"/ordenes/{order.pk}/"

    def test_solo_lectura_consulta_pero_no_registra(self):
        viewer = User.objects.create_user(username="ver", email="v@lab.test", password="x")
        Membership.objects.create(user=viewer, role=Role.objects.get(code="SOLO_LECTURA"))
        self.client.force_login(viewer)

        assert self.client.get("/ordenes/").status_code == 200
        assert self._post_order().status_code == 403
        assert self.client.get("/ordenes/nueva/").status_code == 403


class PatientRegistrationViewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        catalogo()
        paciente(document_number="1")  # configura las siglas del laboratorio
        self.client = TenantClient(self.tenant)
        self.client.force_login(User.objects.create_superuser(
            username="a", email="a@lab.test", password="x"))

    def test_menor_sin_documento_exige_y_registra_representante(self):
        data = {"document_type": "SIN_DOCUMENTO", "first_name": "Luis", "last_name": "Sutil",
                "sex": "M", "declared_age_value": 3, "declared_age_unit": "MESES",
                "next": "/ordenes/nueva/"}

        response = self.client.post("/pacientes/nuevo/", data)
        assert "requiere un representante" in response.content.decode()

        data.update({"g_document_type": "V", "g_document_number": "20111222",
                     "g_first_name": "Ana", "g_last_name": "Sutil", "g_relationship": "MADRE"})
        response = self.client.post("/pacientes/nuevo/", data)

        patient = Patient.objects.get(first_name="Luis")
        assert response.url == f"/ordenes/nueva/?paciente={patient.pk}"
        assert patient.guardians.get().guardian.document_number == "20111222"
        assert (patient.declared_age_value, patient.declared_age_unit) == (3, "MESES")
