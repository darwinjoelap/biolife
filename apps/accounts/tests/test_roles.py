from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import Membership, Role, User
from apps.accounts.permissions import has_role
from apps.accounts.services.user_management import seed_system_roles


class RoleAssignmentTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        seed_system_roles()

    def test_has_role_con_membership_activa_devuelve_true(self):
        user = User.objects.create_user(username="ana", password="x")
        role = Role.objects.get(code=Role.Code.ADMIN_LAB)
        Membership.objects.create(user=user, role=role)

        assert has_role(user, "ADMIN_LAB") is True

    def test_has_role_con_membership_inactiva_devuelve_false(self):
        user = User.objects.create_user(username="beto", password="x")
        role = Role.objects.get(code=Role.Code.ADMIN_LAB)
        Membership.objects.create(user=user, role=role, is_active=False)

        assert has_role(user, "ADMIN_LAB") is False

    def test_has_role_sin_membership_devuelve_false(self):
        user = User.objects.create_user(username="carla", password="x")

        assert has_role(user, "ADMIN_LAB") is False

    def test_seed_system_roles_crea_los_7_roles(self):
        assert Role.objects.count() == 7
        assert Role.objects.filter(code="AUXILIAR_TOMA").exists()
