"""Django admin registration for the NetCracker SSoT configuration model."""

from django.contrib import admin

from nautobot_ssot_netcracker.models import NetCrackerConfig


@admin.register(NetCrackerConfig)
class NetCrackerConfigAdmin(admin.ModelAdmin):
    """Admin view for NetCrackerConfig.

    Exposes the DB connection settings and conflict strategy for
    superuser management via /admin/.
    """

    list_display = ("db_host", "db_port", "db_name", "db_user", "enabled")
    readonly_fields = ("id", "created", "last_updated")
    fieldsets = (
        (
            "Database Connection",
            {
                "fields": ("db_host", "db_port", "db_name", "db_user", "db_secrets"),
            },
        ),
        (
            "Sync Behaviour",
            {
                "fields": ("enabled", "conflict_strategy"),
            },
        ),
        (
            "Metadata",
            {
                "classes": ("collapse",),
                "fields": ("id", "created", "last_updated"),
            },
        ),
    )
