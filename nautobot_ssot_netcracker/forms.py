"""Forms for the NetCracker SSoT configuration."""

from django import forms
from nautobot.extras.models import SecretsGroup
from nautobot.utilities.forms import BootstrapMixin, DynamicModelChoiceField

from nautobot_ssot_netcracker.models import NetCrackerConfig, CONFLICT_STRATEGY_CHOICES


class ConflictStrategyWidget(forms.MultiWidget):
    """Widget that renders one dropdown per object type for conflict strategy."""

    OBJECT_TYPES = ["location", "device", "prefix", "ip_address", "circuit"]

    def __init__(self, attrs=None):
        widgets = [
            forms.Select(choices=CONFLICT_STRATEGY_CHOICES, attrs={"class": "form-control"})
            for _ in self.OBJECT_TYPES
        ]
        super().__init__(widgets=widgets, attrs=attrs)

    def decompress(self, value):
        if value:
            return [value.get(ot, "overwrite") for ot in self.OBJECT_TYPES]
        return ["overwrite"] * len(self.OBJECT_TYPES)


class ConflictStrategyField(forms.MultiValueField):
    """Field that collects per-object-type conflict strategies and returns a dict."""

    OBJECT_TYPES = ["location", "device", "prefix", "ip_address", "circuit"]

    def __init__(self, *args, **kwargs):
        fields = [
            forms.ChoiceField(choices=CONFLICT_STRATEGY_CHOICES)
            for _ in self.OBJECT_TYPES
        ]
        kwargs.setdefault("widget", ConflictStrategyWidget())
        kwargs.setdefault("require_all_fields", True)
        super().__init__(fields=fields, *args, **kwargs)

    def compress(self, data_list):
        return dict(zip(self.OBJECT_TYPES, data_list))


class NetCrackerConfigForm(BootstrapMixin, forms.ModelForm):
    """Form for creating/editing the NetCracker SSoT configuration."""

    db_secrets = DynamicModelChoiceField(
        queryset=SecretsGroup.objects.all(),
        label="DB Secrets Group",
        help_text="Select the SecretsGroup that holds the PostgreSQL password.",
    )

    conflict_strategy = ConflictStrategyField(
        label="Conflict Strategy (per object type)",
        help_text="Choose how to resolve conflicts between NetCracker and Nautobot for each object type.",
    )

    class Meta:
        model = NetCrackerConfig
        fields = [
            "db_host",
            "db_port",
            "db_name",
            "db_user",
            "db_secrets",
            "enabled",
            "conflict_strategy",
        ]
        widgets = {
            "db_host": forms.TextInput(attrs={"placeholder": "postgres.example.com"}),
            "db_port": forms.NumberInput(attrs={"min": 1, "max": 65535}),
            "db_name": forms.TextInput(attrs={"placeholder": "netcracker"}),
            "db_user": forms.TextInput(attrs={"placeholder": "nc_readonly"}),
        }
