from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog"
    label = "catalog"
    verbose_name = "Catálogo de exámenes"

    def ready(self):
        from apps.catalog import aux_tables  # noqa: F401  (registra las tablas auxiliares)
