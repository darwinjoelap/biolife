from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.accounts.models import User
from apps.catalog.models import Parameter, ReferenceRange
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges


def _post_value(value):
    """Convierte un valor inicial de formulario al formato de un POST (None → omitir)."""
    value = getattr(value, "pk", value)
    if value is False or value is None:
        return None
    return "on" if value is True else value


class ParameterAdminRangesPostTests(TenantTestCase):
    """Guardado real por el admin: bloquea solapes ambiguos, avisa los resueltos por
    desempate y escribe la bitácora del admin en el esquema del tenant (ADR-020)."""

    def setUp(self):
        super().setUp()
        seed_uroanalisis()
        seed_reference_ranges()
        user = User.objects.create_superuser(username="a", email="a@a.com", password="x")
        self.client = TenantClient(self.tenant)
        self.client.force_login(user)
        self.parameter = Parameter.objects.get(code="HEM_HEMOGLOBINA")
        self.url = f"/admin/catalog/parameter/{self.parameter.pk}/change/"

    def _current_post_data(self):
        response = self.client.get(self.url)
        data = {}
        form = response.context["adminform"].form
        for name in form.fields:
            value = _post_value(form.initial.get(name, ""))
            if value is not None:
                data[name] = value
        formset = response.context["inline_admin_formsets"][0].formset
        prefix, rows = formset.prefix, list(formset.forms)
        for index, row in enumerate(rows):
            for name in row.fields:
                initial = {"id": row.instance.pk, "parameter": self.parameter.pk}
                value = _post_value(initial.get(name, row.initial.get(name, "")))
                if value is not None:
                    data[f"{prefix}-{index}-{name}"] = value
        data.update({
            f"{prefix}-TOTAL_FORMS": len(rows) + 1, f"{prefix}-INITIAL_FORMS": len(rows),
            f"{prefix}-MIN_NUM_FORMS": 0, f"{prefix}-MAX_NUM_FORMS": 1000,
        })
        return data, f"{prefix}-{len(rows)}"

    def test_guardar_rangos_desde_la_ficha_del_parametro(self):
        data, new = self._current_post_data()
        data.update({
            f"{new}-sex": "M", f"{new}-condition": "NINGUNA", f"{new}-priority": 0,
            f"{new}-range_type": "CLOSED", f"{new}-low": "1", f"{new}-high": "2",
            f"{new}-display_text": "dup", f"{new}-is_active": "on",
            f"{new}-parameter": self.parameter.pk,
        })

        # Mismo tramo y prioridad que el rango masculino existente: se bloquea.
        response = self.client.post(self.url, data)
        assert "misma prioridad" in response.content.decode()
        assert ReferenceRange.objects.filter(parameter=self.parameter).count() == 2

        # Recién nacido (hasta 28 días, exclusivo): se guarda con aviso de desempate.
        data.update({f"{new}-hasta_dias": 28, f"{new}-display_text": "RN"})
        response = self.client.post(self.url, data, follow=True)
        mensajes = [str(m) for m in response.context["messages"]]
        assert any(m.startswith("AVISO") and "se usa el más estrecho" in m for m in mensajes)
        rangos = ReferenceRange.objects.filter(parameter=self.parameter)
        assert list(rangos.filter(display_text="RN").values_list(
            "age_min_days", "age_max_days")) == [(0, 27)]
        # Los rangos existentes no cambiaron al reguardarse.
        assert set(rangos.exclude(display_text="RN").values_list(
            "sex", "age_min_days", "age_max_days")) == {("M", 0, 54750), ("F", 0, 54750)}
