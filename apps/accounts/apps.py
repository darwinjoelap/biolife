from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        from django.contrib.auth.signals import (
            user_logged_in,
            user_logged_out,
            user_login_failed,
        )

        from apps.accounts.services.audit import (
            log_login_failed,
            log_login_success,
            log_logout,
        )

        user_logged_in.connect(log_login_success, dispatch_uid="accounts_log_login_success")
        user_logged_out.connect(log_logout, dispatch_uid="accounts_log_logout")
        user_login_failed.connect(log_login_failed, dispatch_uid="accounts_log_login_failed")
