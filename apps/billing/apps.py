from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.billing"
    label = "billing"
    verbose_name = "Precios y cobro"

    def ready(self):
        from apps.billing import aux_tables  # noqa: F401  (registra monedas y descuentos)
