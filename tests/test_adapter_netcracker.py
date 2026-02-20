"""Tests for the NetCracker PostgreSQL source adapter.

Uses SQLAlchemy's in-memory SQLite engine to simulate the NetCracker
database without requiring a real PostgreSQL connection.
"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, text

from nautobot_ssot_netcracker.diffsync.adapter_netcracker import NetCrackerAdapter
from nautobot_ssot_netcracker.diffsync.models import (
    NetCrackerLocation,
    NetCrackerDevice,
    NetCrackerCircuit,
    NetCrackerPrefix,
    NetCrackerIPAddress,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sqlite_engine():
    """Create an in-memory SQLite engine with stub NetCracker tables."""
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE NC_LOCATION_TABLE (
                NC_LOCATION_NAME     TEXT PRIMARY KEY,
                NC_LOCATION_TYPE     TEXT,
                NC_LOCATION_STATUS   TEXT,
                NC_LOCATION_DESC     TEXT,
                NC_LOCATION_LATITUDE REAL,
                NC_LOCATION_LONGITUDE REAL
            )
        """))
        conn.execute(text("""
            CREATE TABLE NC_DEVICE_TABLE (
                NC_DEVICE_NAME   TEXT PRIMARY KEY,
                NC_DEVICE_TYPE   TEXT,
                NC_MANUFACTURER  TEXT,
                NC_DEVICE_ROLE   TEXT,
                NC_DEVICE_STATUS TEXT,
                NC_LOCATION_NAME TEXT,
                NC_SERIAL_NUMBER TEXT,
                NC_PLATFORM      TEXT,
                NC_COMMENTS      TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE NC_PREFIX_TABLE (
                NC_PREFIX_CIDR   TEXT PRIMARY KEY,
                NC_NAMESPACE     TEXT,
                NC_PREFIX_STATUS TEXT,
                NC_PREFIX_DESC   TEXT,
                NC_VRF_NAME      TEXT,
                NC_LOCATION_NAME TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE NC_IP_ADDRESS_TABLE (
                NC_IP_ADDRESS  TEXT PRIMARY KEY,
                NC_NAMESPACE   TEXT,
                NC_IP_STATUS   TEXT,
                NC_DNS_NAME    TEXT,
                NC_IP_DESC     TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE NC_CIRCUIT_TABLE (
                NC_CIRCUIT_ID       TEXT PRIMARY KEY,
                NC_PROVIDER_NAME    TEXT,
                NC_CIRCUIT_TYPE     TEXT,
                NC_CIRCUIT_STATUS   TEXT,
                NC_CIRCUIT_DESC     TEXT,
                NC_COMMIT_RATE      INTEGER,
                NC_CIRCUIT_COMMENTS TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE NC_INTERFACE_TABLE (
                NC_DEVICE_NAME       TEXT,
                NC_INTERFACE_NAME    TEXT,
                NC_INTERFACE_TYPE    TEXT,
                NC_INTERFACE_STATUS  TEXT,
                NC_INTERFACE_ENABLED INTEGER,
                NC_INTERFACE_DESC    TEXT,
                NC_MAC_ADDRESS       TEXT,
                NC_MTU               INTEGER,
                PRIMARY KEY (NC_DEVICE_NAME, NC_INTERFACE_NAME)
            )
        """))
        # Seed data
        conn.execute(text("""
            INSERT INTO NC_LOCATION_TABLE VALUES
            ('NYC-DC1', 'Site', 'active', 'New York DC', 40.7128, -74.0060)
        """))
        conn.execute(text("""
            INSERT INTO NC_DEVICE_TABLE VALUES
            ('router01', 'ASR1001', 'Cisco', 'Core Router', 'active', 'NYC-DC1', 'SN-12345', 'IOS-XE', NULL)
        """))
        conn.execute(text("""
            INSERT INTO NC_PREFIX_TABLE VALUES
            ('10.0.0.0/24', 'Global', 'active', 'Mgmt subnet', NULL, 'NYC-DC1')
        """))
        conn.execute(text("""
            INSERT INTO NC_IP_ADDRESS_TABLE VALUES
            ('10.0.0.1/24', 'Global', 'active', 'router01.mgmt', NULL)
        """))
        conn.execute(text("""
            INSERT INTO NC_CIRCUIT_TABLE VALUES
            ('CKT-001', 'AT&T', 'Transit', 'active', 'Internet uplink', 1000000, NULL)
        """))
        conn.execute(text("""
            INSERT INTO NC_INTERFACE_TABLE VALUES
            ('router01', 'GigabitEthernet0/0', '1000base-t', 'active', 1, 'Uplink', '00:11:22:33:44:55', 1500)
        """))
        conn.commit()
    return engine


@pytest.fixture()
def adapter(sqlite_engine):
    mock_job = MagicMock()
    mock_job.logger = MagicMock()
    return NetCrackerAdapter(engine=sqlite_engine, job=mock_job, sync=None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNetCrackerAdapterLoad:
    def test_loads_locations(self, adapter):
        adapter._load_locations()
        loc = adapter.get(NetCrackerLocation, "NYC-DC1")
        assert loc is not None
        assert loc.name == "NYC-DC1"
        assert loc.location_type == "Site"
        assert loc.status == "active"
        assert loc.latitude == pytest.approx(40.7128)

    def test_loads_devices(self, adapter):
        adapter._load_locations()
        adapter._load_devices()
        dev = adapter.get(NetCrackerDevice, "router01")
        assert dev is not None
        assert dev.device_type == "ASR1001"
        assert dev.manufacturer == "Cisco"
        assert dev.serial == "SN-12345"

    def test_loads_prefixes(self, adapter):
        adapter._load_prefixes()
        pfx = adapter.get(NetCrackerPrefix, {"prefix": "10.0.0.0/24", "namespace": "Global"})
        assert pfx is not None
        assert pfx.status == "active"

    def test_loads_ip_addresses(self, adapter):
        adapter._load_ip_addresses()
        ip = adapter.get(NetCrackerIPAddress, {"address": "10.0.0.1/24", "namespace": "Global"})
        assert ip is not None
        assert ip.dns_name == "router01.mgmt"

    def test_loads_circuits(self, adapter):
        adapter._load_circuits()
        ckt = adapter.get(NetCrackerCircuit, {"cid": "CKT-001", "provider": "AT&T"})
        assert ckt is not None
        assert ckt.circuit_type == "Transit"
        assert ckt.commit_rate == 1000000

    def test_full_load(self, adapter):
        adapter.load()
        assert len(list(adapter.get_all(NetCrackerLocation))) == 1
        assert len(list(adapter.get_all(NetCrackerDevice))) == 1
        assert len(list(adapter.get_all(NetCrackerPrefix))) == 1
        assert len(list(adapter.get_all(NetCrackerIPAddress))) == 1
        assert len(list(adapter.get_all(NetCrackerCircuit))) == 1


class TestNormalizeStatus:
    @pytest.mark.parametrize("input_val,expected", [
        ("active", "active"),
        ("ACTIVE", "active"),
        ("enabled", "active"),
        ("up", "active"),
        ("operational", "active"),
        ("inactive", "decommissioned"),
        ("disabled", "decommissioned"),
        ("down", "failed"),
        ("planned", "planned"),
        ("staged", "staged"),
        ("reserved", "reserved"),
        (None, "active"),
        ("unknown_value", "active"),
    ])
    def test_normalize(self, input_val, expected):
        result = NetCrackerAdapter._normalize_status(input_val)
        assert result == expected


class TestSchemaUtils:
    def test_discover_schema_returns_structure(self, sqlite_engine):
        from nautobot_ssot_netcracker.utils import discover_schema
        result = discover_schema(sqlite_engine)
        assert "tables" in result
        assert "candidates" in result
        assert isinstance(result["tables"], dict)
        assert isinstance(result["candidates"], dict)

    def test_discover_schema_finds_tables(self, sqlite_engine):
        from nautobot_ssot_netcracker.utils import discover_schema
        result = discover_schema(sqlite_engine)
        table_names = list(result["tables"].keys())
        assert any("LOCATION" in t.upper() or "location" in t.lower() for t in table_names)

    def test_format_schema_report(self, sqlite_engine):
        from nautobot_ssot_netcracker.utils import discover_schema, format_schema_report
        schema_data = discover_schema(sqlite_engine)
        report = format_schema_report(schema_data)
        assert "Schema Discovery Report" in report
        assert "CANDIDATE TABLE MAPPINGS" in report
