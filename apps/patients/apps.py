from django.apps import AppConfig


class PatientsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.patients"
    label = "patients"
    verbose_name = "Pacientes"

    def ready(self):
        from apps.patients import aux_tables  # noqa: F401  (registra los antecedentes)
