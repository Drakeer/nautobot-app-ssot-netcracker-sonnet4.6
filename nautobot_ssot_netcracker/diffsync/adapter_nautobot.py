"""Nautobot target adapter for the NetCracker SSoT integration.

Extends NautobotAdapter from nautobot_ssot.contrib to load existing Nautobot
data into DiffSync, and applies the configured conflict strategy when
deciding whether to create, update, or skip records.
"""

import logging
from typing import Any, Dict, Optional

from nautobot_ssot.contrib import NautobotAdapter

from nautobot_ssot_netcracker.diffsync.models import (
    NetCrackerCircuit,
    NetCrackerDevice,
    NetCrackerInterface,
    NetCrackerIPAddress,
    NetCrackerLocation,
    NetCrackerPrefix,
)
from nautobot_ssot_netcracker.utils import get_conflict_strategy

logger = logging.getLogger(__name__)


class NetCrackerNautobotAdapter(NautobotAdapter):
    """DiffSync adapter that reads from (and writes to) Nautobot via the ORM.

    Conflict strategy is enforced in create() / update() by checking the
    per-object-type setting from NetCrackerConfig.

    Conflict strategies:
        overwrite   — Apply all changes from NetCracker unconditionally.
        skip        — Create new records but never update existing ones.
        flag        — Log the conflict; do not create or update.
    """

    # Register model classes (same names as the source adapter)
    location = NetCrackerLocation
    device = NetCrackerDevice
    interface = NetCrackerInterface
    prefix = NetCrackerPrefix
    ip_address = NetCrackerIPAddress
    circuit = NetCrackerCircuit

    top_level = ["location", "prefix", "circuit"]

    def __init__(self, job=None, sync=None, **kwargs):
        super().__init__(job=job, sync=sync, **kwargs)
        self.job = job
        self.sync = sync

    # ------------------------------------------------------------------
    # Nautobot ORM model references
    # These tell NautobotAdapter which ORM models back each DiffSync model.
    # ------------------------------------------------------------------

    def _get_nautobot_location(self, ids: Dict[str, Any], attrs: Dict[str, Any]):
        """Resolve or create a Nautobot Location ORM instance."""
        from nautobot.dcim.models import Location, LocationType
        from nautobot.extras.models import Status

        location_type, _ = LocationType.objects.get_or_create(name=attrs.get("location_type", "Site"))
        status = Status.objects.get(name__iexact=attrs.get("status", "active"))
        return Location(
            name=ids["name"],
            location_type=location_type,
            status=status,
            description=attrs.get("description") or "",
            latitude=attrs.get("latitude"),
            longitude=attrs.get("longitude"),
        )

    def _get_nautobot_device(self, ids: Dict[str, Any], attrs: Dict[str, Any]):
        """Resolve or create a Nautobot Device ORM instance."""
        from nautobot.dcim.models import Device, DeviceType, Location, Manufacturer
        from nautobot.extras.models import Role, Status

        manufacturer, _ = Manufacturer.objects.get_or_create(name=attrs.get("manufacturer", "Unknown"))
        device_type, _ = DeviceType.objects.get_or_create(
            model=attrs.get("device_type", "Unknown"),
            manufacturer=manufacturer,
        )
        role, _ = Role.objects.get_or_create(name=attrs.get("role", "Unknown"))
        status = Status.objects.get(name__iexact=attrs.get("status", "active"))
        location = Location.objects.filter(name=attrs.get("location", "")).first()
        return Device(
            name=ids["name"],
            device_type=device_type,
            role=role,
            status=status,
            location=location,
            serial=attrs.get("serial") or "",
            platform=None,  # resolved separately if platform name is set
            comments=attrs.get("comments") or "",
        )

    # ------------------------------------------------------------------
    # Conflict strategy overrides
    # ------------------------------------------------------------------

    def sync_create(self, obj):
        """Create a new record in Nautobot, subject to conflict strategy."""
        strategy = get_conflict_strategy(obj.get_type())
        if strategy == "flag":
            self._log(
                "warning",
                f"[flag] Would CREATE {obj.get_type()} {obj.get_unique_id()} — skipped by conflict strategy.",
            )
            return None
        return super().sync_create(obj)

    def sync_update(self, obj):
        """Update an existing Nautobot record, subject to conflict strategy."""
        strategy = get_conflict_strategy(obj.get_type())
        if strategy == "skip":
            self._log(
                "debug",
                f"[skip] Skipping UPDATE for {obj.get_type()} {obj.get_unique_id()} — conflict strategy is 'skip'.",
            )
            return None
        if strategy == "flag":
            self._log(
                "warning",
                f"[flag] Conflict detected for {obj.get_type()} {obj.get_unique_id()} — not updating.",
            )
            return None
        # strategy == "overwrite" — proceed normally
        return super().sync_update(obj)

    def sync_delete(self, obj):
        """Delete a Nautobot record.

        Deletions are currently blocked regardless of strategy to prevent
        accidental data loss. Override this method if deletions are desired.
        """
        self._log(
            "warning",
            f"DELETE requested for {obj.get_type()} {obj.get_unique_id()} — "
            "deletions are disabled in this integration. Record will be left in Nautobot.",
        )
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _log(self, level: str, message: str):
        getattr(logger, level)(message)
        if self.job:
            log_fn = getattr(self.job.logger, level, self.job.logger.info)
            log_fn(message)
