import pytest
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import AuditLog
from apps.accounts.services.audit import log_action
from apps.core.exceptions import ApplicationError


class AuditLogTests(TenantTestCase):
    def test_log_action_crea_registro(self):
        entry = log_action(action="LOGIN_OK")

        assert AuditLog.objects.filter(pk=entry.pk, action="LOGIN_OK").exists()

    def test_auditlog_no_se_puede_modificar(self):
        entry = log_action(action="LOGIN_OK")
        entry.action = "LOGIN_FALLIDO"

        with pytest.raises(ApplicationError):
            entry.save()

    def test_auditlog_no_se_puede_borrar(self):
        entry = log_action(action="LOGIN_OK")

        with pytest.raises(ApplicationError):
            entry.delete()

        assert AuditLog.objects.filter(pk=entry.pk).exists()
