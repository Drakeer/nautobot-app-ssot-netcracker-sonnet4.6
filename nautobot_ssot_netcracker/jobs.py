"""Nautobot Jobs for the NetCracker SSoT integration.

Jobs:
    NetCrackerDataSource        — Full ETL sync from NetCracker → Nautobot.
    NetCrackerSchemaDiscoveryJob — Connects to NetCracker DB and logs the schema
                                   so developers can map tables to DiffSync models.
"""

import logging

from nautobot.apps.jobs import Job, BooleanVar, StringVar
from nautobot_ssot.jobs.base import DataSource, DataMapping

from nautobot_ssot_netcracker.diffsync.adapter_nautobot import NetCrackerNautobotAdapter
from nautobot_ssot_netcracker.diffsync.adapter_netcracker import NetCrackerAdapter
from nautobot_ssot_netcracker.utils import (
    discover_schema,
    format_schema_report,
    get_netcracker_engine,
)

logger = logging.getLogger(__name__)

name = "NetCracker SSoT"  # Job group name shown in Nautobot UI


# ---------------------------------------------------------------------------
# Main sync job
# ---------------------------------------------------------------------------

class NetCrackerDataSource(DataSource, Job):
    """Sync Devices, Sites, IPs, and Circuits from NetCracker PostgreSQL into Nautobot.

    This job implements the nautobot-app-ssot DataSource interface:
        1. load_source_adapter() — pulls data from NetCracker via SQLAlchemy
        2. load_target_adapter() — pulls existing data from Nautobot via ORM
        3. DiffSync calculates the diff
        4. Changes are applied to Nautobot (respecting per-type conflict strategy)

    Supports:
        - Dry-run mode (diff only, no writes)
        - Scheduled execution via Nautobot Job Scheduling
        - Manual on-demand run from the Nautobot UI
    """

    class Meta:
        name = "NetCracker → Nautobot Sync"
        description = (
            "Single Source of Truth sync from NetCracker PostgreSQL to Nautobot. "
            "Syncs Locations, Devices, Interfaces, Prefixes, IP Addresses, and Circuits."
        )
        has_sensitive_variables = False
        # Uncomment to restrict to specific groups:
        # approval_required = True

    # ------------------------------------------------------------------
    # Adapter loaders
    # ------------------------------------------------------------------

    def load_source_adapter(self):
        """Connect to NetCracker PostgreSQL and load all data into DiffSync."""
        self.logger.info("Connecting to NetCracker PostgreSQL database...")
        engine = get_netcracker_engine()
        self.source_adapter = NetCrackerAdapter(engine=engine, job=self, sync=self.sync)
        self.source_adapter.load()

    def load_target_adapter(self):
        """Load existing Nautobot data into DiffSync for comparison."""
        self.logger.info("Loading existing Nautobot data...")
        self.target_adapter = NetCrackerNautobotAdapter(job=self, sync=self.sync)
        self.target_adapter.load()

    # ------------------------------------------------------------------
    # Metadata for the SSoT UI
    # ------------------------------------------------------------------

    @classmethod
    def data_mappings(cls):
        """Describe how NetCracker concepts map to Nautobot objects."""
        from django.urls import reverse
        return (
            DataMapping("Sites / Locations", None, "Locations", reverse("dcim:location_list")),
            DataMapping("Devices / Nodes", None, "Devices", reverse("dcim:device_list")),
            DataMapping("Interfaces", None, "Interfaces", reverse("dcim:interface_list")),
            DataMapping("IP Prefixes / Subnets", None, "Prefixes", reverse("ipam:prefix_list")),
            DataMapping("IP Addresses", None, "IP Addresses", reverse("ipam:ipaddress_list")),
            DataMapping("Circuits / Links", None, "Circuits", reverse("circuits:circuit_list")),
        )

    @classmethod
    def config_information(cls):
        """Return non-sensitive configuration for display in the SSoT UI."""
        from nautobot_ssot_netcracker.models import NetCrackerConfig
        config = NetCrackerConfig.objects.first()
        if config is None:
            return {"status": "No configuration found — please create a NetCrackerConfig record."}
        return {
            "db_host": config.db_host,
            "db_port": config.db_port,
            "db_name": config.db_name,
            "db_user": config.db_user,
            "enabled": config.enabled,
            "conflict_strategy": config.conflict_strategy,
        }


# ---------------------------------------------------------------------------
# Schema discovery job
# ---------------------------------------------------------------------------

class NetCrackerSchemaDiscoveryJob(Job):
    """Connects to the NetCracker PostgreSQL database and logs the full schema.

    Run this job FIRST to discover what tables and columns exist in your
    NetCracker deployment. The output will guide you in filling in the
    placeholder table/column names in adapter_netcracker.py.

    Look for lines marked:  # SCHEMA: update after discovery
    """

    schema_filter = StringVar(
        label="Table name filter (optional)",
        description=(
            "If provided, only tables whose names contain this string will be shown. "
            "Leave blank to see all tables."
        ),
        required=False,
        default="",
    )
    show_all_columns = BooleanVar(
        label="Show all columns",
        description="If unchecked, only the first 20 columns per table are shown.",
        default=True,
    )

    class Meta:
        name = "NetCracker Schema Discovery"
        description = (
            "Connects to the NetCracker PostgreSQL database and logs the full schema. "
            "Run this before configuring the sync to identify the correct table and column names."
        )
        has_sensitive_variables = False

    def run(self, schema_filter="", show_all_columns=True):
        self.logger.info("Starting NetCracker schema discovery...")

        try:
            engine = get_netcracker_engine()
        except RuntimeError as exc:
            self.logger.error(str(exc))
            return

        self.logger.info("Connected to NetCracker database. Introspecting schema...")

        try:
            schema_data = discover_schema(engine)
        except Exception as exc:
            self.logger.error(f"Schema introspection failed: {exc}")
            return

        total_tables = len(schema_data["tables"])
        self.logger.info(f"Found {total_tables} tables in NetCracker database.")

        # Apply optional filter
        if schema_filter:
            filtered = {
                t: cols
                for t, cols in schema_data["tables"].items()
                if schema_filter.lower() in t.lower()
            }
            self.logger.info(
                f"Filter '{schema_filter}' applied: showing {len(filtered)} of {total_tables} tables."
            )
            schema_data["tables"] = filtered

        # Log candidate mappings
        self.logger.info("=== CANDIDATE TABLE MAPPINGS ===")
        for object_type, candidates in schema_data["candidates"].items():
            if schema_filter:
                candidates = [c for c in candidates if schema_filter.lower() in c.lower()]
            if candidates:
                self.logger.info(f"  {object_type.upper()}: {', '.join(candidates)}")
            else:
                self.logger.warning(f"  {object_type.upper()}: No candidates found.")

        # Log full table listing
        self.logger.info("=== ALL TABLES ===")
        for table_name, columns in sorted(schema_data["tables"].items()):
            display_cols = columns if show_all_columns else columns[:20]
            truncated = "" if show_all_columns or len(columns) <= 20 else f" ... (+{len(columns) - 20} more)"
            self.logger.info(f"  TABLE: {table_name}")
            self.logger.info(f"    COLUMNS: {', '.join(display_cols)}{truncated}")

        self.logger.info(
            "Schema discovery complete. "
            "Update the placeholder table/column names in "
            "nautobot_ssot_netcracker/diffsync/adapter_netcracker.py "
            "using the output above."
        )
