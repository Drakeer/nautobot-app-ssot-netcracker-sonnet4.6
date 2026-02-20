"""Nautobot App configuration for nautobot-app-ssot-netcracker."""

from nautobot.apps import NautobotAppConfig


class NetCrackerSSOTConfig(NautobotAppConfig):
    """App config for the NetCracker SSoT integration."""

    name = "nautobot_ssot_netcracker"
    verbose_name = "NetCracker SSoT"
    description = "Nautobot SSoT integration that syncs Devices, Sites, IPs, and Circuits from NetCracker into Nautobot."
    version = "0.1.0"
    author = "Network Automation Team"
    author_email = ""
    base_url = "ssot-netcracker"
    required_settings = []
    default_settings = {
        "netcracker_db_host": "",
        "netcracker_db_port": 5432,
        "netcracker_db_name": "",
        "netcracker_db_user": "",
    }
    caching_config = {}

    def ready(self):
        """Perform app-ready actions including signal registration."""
        super().ready()
        from nautobot_ssot_netcracker import signals  # noqa: F401


config = NetCrackerSSOTConfig
