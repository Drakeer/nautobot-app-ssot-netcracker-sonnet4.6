"""NetCracker PostgreSQL source adapter for the SSoT integration.

This adapter connects to the NetCracker PostgreSQL database via SQLAlchemy,
executes SQL queries, and populates DiffSync model instances that can then
be diffed against the Nautobot target adapter.

IMPORTANT — Schema placeholders:
    The SQL queries in each _load_* method contain placeholder table and
    column names (prefixed with NC_). These MUST be updated after running
    the NetCrackerSchemaDiscoveryJob to identify the real NetCracker table
    and column names for your deployment.

    Search for the comment "# SCHEMA: update after discovery" to find every
    placeholder that needs to be replaced.
"""

import logging
from typing import Optional

from diffsync import Adapter
from sqlalchemy.engine import Engine

from nautobot_ssot_netcracker.diffsync.models import (
    NetCrackerCircuit,
    NetCrackerDevice,
    NetCrackerInterface,
    NetCrackerIPAddress,
    NetCrackerLocation,
    NetCrackerPrefix,
)

logger = logging.getLogger(__name__)


class NetCrackerAdapter(Adapter):
    """DiffSync adapter that loads data from the NetCracker PostgreSQL database.

    Populates:
        - Locations  (Sites)
        - Devices
        - Interfaces
        - Prefixes
        - IP Addresses
        - Circuits

    Usage::

        engine = get_netcracker_engine()
        adapter = NetCrackerAdapter(engine=engine, job=job, sync=sync)
        adapter.load()
    """

    # Register DiffSync model classes
    location = NetCrackerLocation
    device = NetCrackerDevice
    interface = NetCrackerInterface
    prefix = NetCrackerPrefix
    ip_address = NetCrackerIPAddress
    circuit = NetCrackerCircuit

    # Hierarchy: locations contain devices; devices contain interfaces.
    # Prefixes and circuits are top-level.
    top_level = ["location", "prefix", "circuit"]

    def __init__(self, engine: Engine, job=None, sync=None, **kwargs):
        """Initialise the adapter.

        Args:
            engine: SQLAlchemy Engine connected to NetCracker PostgreSQL.
            job:    The running Nautobot Job (for logging).
            sync:   The Nautobot Sync record (for audit).
        """
        super().__init__(**kwargs)
        self.engine = engine
        self.job = job
        self.sync = sync

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def load(self):
        """Load all NetCracker data into the DiffSync store."""
        self._log("info", "Loading data from NetCracker PostgreSQL...")
        self._load_locations()
        self._load_devices()
        self._load_interfaces()
        self._load_prefixes()
        self._load_ip_addresses()
        self._load_circuits()
        self._log("info", "NetCracker data load complete.")

    # ------------------------------------------------------------------
    # Loaders — one per model type
    # ------------------------------------------------------------------

    def _load_locations(self):
        """Load site/location records from NetCracker.

        # SCHEMA: update after discovery
        Replace NC_LOCATION_TABLE, NC_LOCATION_NAME, etc. with the real
        table and column names identified by the schema discovery job.
        """
        query = """
            SELECT
                l.NC_LOCATION_NAME       AS name,
                l.NC_LOCATION_TYPE       AS location_type,
                l.NC_LOCATION_STATUS     AS status,
                l.NC_LOCATION_DESC       AS description,
                l.NC_LOCATION_LATITUDE   AS latitude,
                l.NC_LOCATION_LONGITUDE  AS longitude
            FROM NC_LOCATION_TABLE l
            ORDER BY l.NC_LOCATION_NAME
        """  # SCHEMA: update after discovery

        count = 0
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(self._text(query)).mappings().all()
            for row in rows:
                obj = NetCrackerLocation(
                    name=self._str(row, "name"),
                    location_type=self._str(row, "location_type", default="Site"),
                    status=self._normalize_status(row.get("status")),
                    description=row.get("description"),
                    latitude=self._float(row, "latitude"),
                    longitude=self._float(row, "longitude"),
                )
                self.add(obj)
                count += 1
        except Exception as exc:
            self._log("warning", f"_load_locations failed: {exc}. Skipping locations.")
        self._log("info", f"Loaded {count} locations from NetCracker.")

    def _load_devices(self):
        """Load device/node records from NetCracker.

        # SCHEMA: update after discovery
        """
        query = """
            SELECT
                d.NC_DEVICE_NAME         AS name,
                d.NC_DEVICE_TYPE         AS device_type,
                d.NC_MANUFACTURER        AS manufacturer,
                d.NC_DEVICE_ROLE         AS role,
                d.NC_DEVICE_STATUS       AS status,
                d.NC_LOCATION_NAME       AS location,
                d.NC_SERIAL_NUMBER       AS serial,
                d.NC_PLATFORM            AS platform,
                d.NC_COMMENTS            AS comments
            FROM NC_DEVICE_TABLE d
            ORDER BY d.NC_DEVICE_NAME
        """  # SCHEMA: update after discovery

        count = 0
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(self._text(query)).mappings().all()
            for row in rows:
                obj = NetCrackerDevice(
                    name=self._str(row, "name"),
                    device_type=self._str(row, "device_type", default="Unknown"),
                    manufacturer=self._str(row, "manufacturer", default="Unknown"),
                    role=self._str(row, "role", default="Unknown"),
                    status=self._normalize_status(row.get("status")),
                    location=self._str(row, "location", default="Unknown"),
                    serial=row.get("serial"),
                    platform=row.get("platform"),
                    comments=row.get("comments"),
                )
                # Attach device as child of its location if that location exists
                try:
                    location_obj = self.get(NetCrackerLocation, obj.location)
                    self.add(obj, parent=location_obj)
                except Exception:
                    self.add(obj)
                count += 1
        except Exception as exc:
            self._log("warning", f"_load_devices failed: {exc}. Skipping devices.")
        self._log("info", f"Loaded {count} devices from NetCracker.")

    def _load_interfaces(self):
        """Load interface records from NetCracker.

        # SCHEMA: update after discovery
        """
        query = """
            SELECT
                i.NC_DEVICE_NAME         AS device,
                i.NC_INTERFACE_NAME      AS name,
                i.NC_INTERFACE_TYPE      AS type,
                i.NC_INTERFACE_STATUS    AS status,
                i.NC_INTERFACE_ENABLED   AS enabled,
                i.NC_INTERFACE_DESC      AS description,
                i.NC_MAC_ADDRESS         AS mac_address,
                i.NC_MTU                 AS mtu
            FROM NC_INTERFACE_TABLE i
            ORDER BY i.NC_DEVICE_NAME, i.NC_INTERFACE_NAME
        """  # SCHEMA: update after discovery

        count = 0
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(self._text(query)).mappings().all()
            for row in rows:
                device_name = self._str(row, "device", default="Unknown")
                obj = NetCrackerInterface(
                    device=device_name,
                    name=self._str(row, "name"),
                    type=self._str(row, "type", default="other"),
                    status=self._normalize_status(row.get("status")),
                    enabled=bool(row.get("enabled", True)),
                    description=row.get("description"),
                    mac_address=row.get("mac_address"),
                    mtu=self._int(row, "mtu"),
                )
                try:
                    device_obj = self.get(NetCrackerDevice, device_name)
                    self.add(obj, parent=device_obj)
                except Exception:
                    self.add(obj)
                count += 1
        except Exception as exc:
            self._log("warning", f"_load_interfaces failed: {exc}. Skipping interfaces.")
        self._log("info", f"Loaded {count} interfaces from NetCracker.")

    def _load_prefixes(self):
        """Load IP prefix/subnet records from NetCracker.

        # SCHEMA: update after discovery
        """
        query = """
            SELECT
                p.NC_PREFIX_CIDR         AS prefix,
                p.NC_NAMESPACE           AS namespace,
                p.NC_PREFIX_STATUS       AS status,
                p.NC_PREFIX_DESC         AS description,
                p.NC_VRF_NAME            AS vrf,
                p.NC_LOCATION_NAME       AS location
            FROM NC_PREFIX_TABLE p
            ORDER BY p.NC_PREFIX_CIDR
        """  # SCHEMA: update after discovery

        count = 0
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(self._text(query)).mappings().all()
            for row in rows:
                obj = NetCrackerPrefix(
                    prefix=self._str(row, "prefix"),
                    namespace=self._str(row, "namespace", default="Global"),
                    status=self._normalize_status(row.get("status")),
                    description=row.get("description"),
                    vrf=row.get("vrf"),
                    location=row.get("location"),
                )
                self.add(obj)
                count += 1
        except Exception as exc:
            self._log("warning", f"_load_prefixes failed: {exc}. Skipping prefixes.")
        self._log("info", f"Loaded {count} prefixes from NetCracker.")

    def _load_ip_addresses(self):
        """Load IP address allocation records from NetCracker.

        # SCHEMA: update after discovery
        """
        query = """
            SELECT
                a.NC_IP_ADDRESS          AS address,
                a.NC_NAMESPACE           AS namespace,
                a.NC_IP_STATUS           AS status,
                a.NC_DNS_NAME            AS dns_name,
                a.NC_IP_DESC             AS description
            FROM NC_IP_ADDRESS_TABLE a
            ORDER BY a.NC_IP_ADDRESS
        """  # SCHEMA: update after discovery

        count = 0
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(self._text(query)).mappings().all()
            for row in rows:
                obj = NetCrackerIPAddress(
                    address=self._str(row, "address"),
                    namespace=self._str(row, "namespace", default="Global"),
                    status=self._normalize_status(row.get("status")),
                    dns_name=row.get("dns_name"),
                    description=row.get("description"),
                )
                self.add(obj)
                count += 1
        except Exception as exc:
            self._log("warning", f"_load_ip_addresses failed: {exc}. Skipping IP addresses.")
        self._log("info", f"Loaded {count} IP addresses from NetCracker.")

    def _load_circuits(self):
        """Load circuit/link records from NetCracker.

        # SCHEMA: update after discovery
        """
        query = """
            SELECT
                c.NC_CIRCUIT_ID          AS cid,
                c.NC_PROVIDER_NAME       AS provider,
                c.NC_CIRCUIT_TYPE        AS circuit_type,
                c.NC_CIRCUIT_STATUS      AS status,
                c.NC_CIRCUIT_DESC        AS description,
                c.NC_COMMIT_RATE         AS commit_rate,
                c.NC_CIRCUIT_COMMENTS    AS comments
            FROM NC_CIRCUIT_TABLE c
            ORDER BY c.NC_CIRCUIT_ID
        """  # SCHEMA: update after discovery

        count = 0
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(self._text(query)).mappings().all()
            for row in rows:
                obj = NetCrackerCircuit(
                    cid=self._str(row, "cid"),
                    provider=self._str(row, "provider", default="Unknown"),
                    circuit_type=self._str(row, "circuit_type", default="Unknown"),
                    status=self._normalize_status(row.get("status")),
                    description=row.get("description"),
                    commit_rate=self._int(row, "commit_rate"),
                    comments=row.get("comments"),
                )
                self.add(obj)
                count += 1
        except Exception as exc:
            self._log("warning", f"_load_circuits failed: {exc}. Skipping circuits.")
        self._log("info", f"Loaded {count} circuits from NetCracker.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _text(query: str):
        """Wrap a raw SQL string in SQLAlchemy's text() construct."""
        from sqlalchemy import text
        return text(query)

    @staticmethod
    def _str(row, key: str, default: str = "") -> str:
        val = row.get(key)
        return str(val).strip() if val is not None else default

    @staticmethod
    def _float(row, key: str) -> Optional[float]:
        val = row.get(key)
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int(row, key: str) -> Optional[int]:
        val = row.get(key)
        try:
            return int(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_status(value: Optional[str]) -> str:
        """Normalize a NetCracker status string to a Nautobot status slug.

        This is a best-effort mapping. Extend as needed once real status
        values from NetCracker are known.
        """
        if value is None:
            return "active"
        mapping = {
            "active": "active",
            "enabled": "active",
            "up": "active",
            "operational": "active",
            "inactive": "decommissioned",
            "disabled": "decommissioned",
            "down": "failed",
            "planned": "planned",
            "staged": "staged",
            "reserved": "reserved",
        }
        return mapping.get(str(value).lower().strip(), "active")

    def _log(self, level: str, message: str):
        """Log to both the Python logger and the Nautobot job log (if available)."""
        getattr(logger, level)(message)
        if self.job:
            log_fn = getattr(self.job.logger, level, self.job.logger.info)
            log_fn(message)
