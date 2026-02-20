"""Tests for DiffSync models."""

import pytest

from nautobot_ssot_netcracker.diffsync.models import (
    NetCrackerCircuit,
    NetCrackerDevice,
    NetCrackerInterface,
    NetCrackerIPAddress,
    NetCrackerLocation,
    NetCrackerPrefix,
)


class TestNetCrackerLocation:
    def test_defaults(self):
        obj = NetCrackerLocation(name="NYC-DC1")
        assert obj.name == "NYC-DC1"
        assert obj.location_type == "Site"
        assert obj.status == "active"
        assert obj.description is None
        assert obj.latitude is None
        assert obj.longitude is None

    def test_identifiers(self):
        assert NetCrackerLocation._identifiers == ("name",)

    def test_attributes(self):
        assert "location_type" in NetCrackerLocation._attributes
        assert "status" in NetCrackerLocation._attributes

    def test_modelname(self):
        assert NetCrackerLocation._modelname == "location"

    def test_full_construction(self):
        obj = NetCrackerLocation(
            name="LAX-DC2",
            location_type="Building",
            status="planned",
            description="Los Angeles datacenter",
            latitude=33.9425,
            longitude=-118.4081,
        )
        assert obj.latitude == pytest.approx(33.9425)
        assert obj.longitude == pytest.approx(-118.4081)


class TestNetCrackerDevice:
    def test_defaults(self):
        obj = NetCrackerDevice(
            name="router01",
            device_type="ASR1001",
            manufacturer="Cisco",
            location="NYC-DC1",
        )
        assert obj.role == "Unknown"
        assert obj.status == "active"
        assert obj.serial is None

    def test_identifiers(self):
        assert NetCrackerDevice._identifiers == ("name",)

    def test_modelname(self):
        assert NetCrackerDevice._modelname == "device"


class TestNetCrackerInterface:
    def test_defaults(self):
        obj = NetCrackerInterface(device="router01", name="GigabitEthernet0/0")
        assert obj.type == "other"
        assert obj.enabled is True
        assert obj.mtu is None

    def test_identifiers(self):
        assert NetCrackerInterface._identifiers == ("device", "name")

    def test_modelname(self):
        assert NetCrackerInterface._modelname == "interface"


class TestNetCrackerPrefix:
    def test_defaults(self):
        obj = NetCrackerPrefix(prefix="10.0.0.0/24", namespace="Global")
        assert obj.status == "active"
        assert obj.vrf is None

    def test_identifiers(self):
        assert NetCrackerPrefix._identifiers == ("prefix", "namespace")

    def test_modelname(self):
        assert NetCrackerPrefix._modelname == "prefix"


class TestNetCrackerIPAddress:
    def test_defaults(self):
        obj = NetCrackerIPAddress(address="10.0.0.1/24", namespace="Global")
        assert obj.status == "active"
        assert obj.dns_name is None

    def test_identifiers(self):
        assert NetCrackerIPAddress._identifiers == ("address", "namespace")

    def test_modelname(self):
        assert NetCrackerIPAddress._modelname == "ip_address"


class TestNetCrackerCircuit:
    def test_defaults(self):
        obj = NetCrackerCircuit(cid="CKT-001", provider="AT&T")
        assert obj.circuit_type == "Unknown"
        assert obj.status == "active"
        assert obj.commit_rate is None

    def test_identifiers(self):
        assert NetCrackerCircuit._identifiers == ("cid", "provider")

    def test_modelname(self):
        assert NetCrackerCircuit._modelname == "circuit"
