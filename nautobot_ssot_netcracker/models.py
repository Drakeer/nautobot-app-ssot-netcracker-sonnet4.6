"""Django models for NetCracker SSoT configuration."""

from django.db import models
from nautobot.extras.models import SecretsGroup
from nautobot.core.models import BaseModel


CONFLICT_STRATEGY_CHOICES = [
    ("overwrite", "Overwrite — NetCracker always wins"),
    ("skip", "Skip — never update existing Nautobot records"),
    ("flag", "Flag — log conflict, do not modify"),
]

DEFAULT_CONFLICT_STRATEGY = {
    "location": "overwrite",
    "device": "overwrite",
    "prefix": "overwrite",
    "ip_address": "overwrite",
    "circuit": "overwrite",
}


class NetCrackerConfig(BaseModel):
    """Singleton configuration model for the NetCracker SSoT integration.

    Stores database connection details and per-object conflict strategies.
    Only one instance of this model should exist; enforced via the UI form.
    """

    # --- Database connection ---
    db_host = models.CharField(
        max_length=255,
        verbose_name="DB Host",
        help_text="Hostname or IP address of the NetCracker PostgreSQL server.",
    )
    db_port = models.PositiveIntegerField(
        default=5432,
        verbose_name="DB Port",
        help_text="PostgreSQL port (default: 5432).",
    )
    db_name = models.CharField(
        max_length=255,
        verbose_name="DB Name",
        help_text="Name of the NetCracker PostgreSQL database.",
    )
    db_user = models.CharField(
        max_length=255,
        verbose_name="DB User",
        help_text="PostgreSQL username for connecting to NetCracker.",
    )
    db_secrets = models.ForeignKey(
        SecretsGroup,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="DB Secrets Group",
        help_text="Nautobot SecretsGroup containing the PostgreSQL password.",
    )

    # --- Sync behaviour ---
    enabled = models.BooleanField(
        default=True,
        help_text="Enable or disable the NetCracker → Nautobot sync.",
    )
    conflict_strategy = models.JSONField(
        default=dict,
        verbose_name="Conflict Strategy",
        help_text=(
            "Per-object-type conflict resolution strategy. "
            "Keys: location, device, prefix, ip_address, circuit. "
            "Values: 'overwrite' | 'skip' | 'flag'."
        ),
    )

    class Meta:
        verbose_name = "NetCracker SSoT Configuration"
        verbose_name_plural = "NetCracker SSoT Configurations"

    def __str__(self):
        return f"NetCrackerConfig ({self.db_host}:{self.db_port}/{self.db_name})"

    def save(self, *args, **kwargs):
        """Merge conflict_strategy with defaults so all keys are always present."""
        merged = dict(DEFAULT_CONFLICT_STRATEGY)
        merged.update(self.conflict_strategy or {})
        self.conflict_strategy = merged
        super().save(*args, **kwargs)

    def get_strategy(self, object_type: str) -> str:
        """Return the conflict strategy for a given object type.

        Args:
            object_type: One of 'location', 'device', 'prefix', 'ip_address', 'circuit'.

        Returns:
            Strategy string: 'overwrite', 'skip', or 'flag'.
        """
        return self.conflict_strategy.get(object_type, "overwrite")
