from django.urls import reverse
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.accounts.models import AuditLog, Membership, Role, User
from apps.accounts.services.user_management import seed_system_roles


class LoginTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.client = TenantClient(self.tenant)
        seed_system_roles()
        self.user = User.objects.create_user(username="ana", password="clave-segura-123")
        role = Role.objects.get(code=Role.Code.ADMIN_LAB)
        Membership.objects.create(user=self.user, role=role)

    def test_login_exitoso_redirige_y_registra_auditlog(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "ana", "password": "clave-segura-123"},
        )

        assert response.status_code == 302
        assert AuditLog.objects.filter(action="LOGIN_OK", user=self.user).exists()

    def test_login_fallido_no_redirige_y_registra_auditlog_sin_usuario(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "ana", "password": "clave-incorrecta"},
        )

        assert response.status_code == 200
        assert AuditLog.objects.filter(action="LOGIN_FALLIDO", user__isnull=True).exists()
