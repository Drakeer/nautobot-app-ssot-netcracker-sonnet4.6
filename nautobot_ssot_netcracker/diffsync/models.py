"""DiffSync model definitions for the NetCracker SSoT integration.

Each model maps a NetCracker concept to its Nautobot equivalent.
Models extend NautobotModel from nautobot_ssot.contrib so that the
Nautobot-side adapter can drive CRUD operations automatically via the ORM.

NOTE: SQL query field mappings (which NetCracker columns map to which
      DiffSync attributes) are filled in after schema discovery.
      See adapter_netcracker.py for where the data is populated.

Nautobot ORM imports are done lazily (inside methods) to avoid issues
when models are imported before Django is fully initialized.
"""

from typing import List, Optional

from diffsync import DiffSyncModel


# ---------------------------------------------------------------------------
# Location / Site
# ---------------------------------------------------------------------------

class NetCrackerLocation(DiffSyncModel):
    """Maps a NetCracker site/location to a Nautobot Location.

    Identifiers:
        name: Unique location name as stored in NetCracker.

    Attributes:
        location_type: Nautobot LocationType name (e.g. 'Site', 'Building').
        status:        Nautobot status slug (e.g. 'active').
        description:   Free-text description.
        latitude:      Optional GPS latitude.
        longitude:     Optional GPS longitude.
    """

    _modelname = "location"
    _identifiers = ("name",)
    _attributes = ("location_type", "status", "description", "latitude", "longitude")

    name: str
    location_type: str = "Site"
    status: str = "active"
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------

class NetCrackerDevice(DiffSyncModel):
    """Maps a NetCracker device/node to a Nautobot Device.

    Identifiers:
        name: Unique device name.

    Attributes:
        device_type:  Nautobot DeviceType model slug.
        manufacturer: Manufacturer name (used to resolve DeviceType).
        role:         Nautobot DeviceRole name.
        status:       Nautobot status slug.
        location:     Name of the parent Location (FK reference).
        serial:       Hardware serial number.
        platform:     Nautobot Platform name (OS).
        comments:     Free-text notes.
    """

    _modelname = "device"
    _identifiers = ("name",)
    _attributes = ("device_type", "manufacturer", "role", "status", "location", "serial", "platform", "comments")

    name: str
    device_type: str
    manufacturer: str
    role: str = "Unknown"
    status: str = "active"
    location: str
    serial: Optional[str] = None
    platform: Optional[str] = None
    comments: Optional[str] = None


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

class NetCrackerInterface(DiffSyncModel):
    """Maps a NetCracker interface to a Nautobot Interface.

    Identifiers:
        device: Parent device name.
        name:   Interface name (e.g. 'GigabitEthernet0/0').

    Attributes:
        type:        Nautobot interface type slug (e.g. '1000base-t').
        status:      Nautobot status slug.
        enabled:     Whether the interface is administratively up.
        description: Free-text description.
        mac_address: MAC address string.
        mtu:         MTU in bytes.
    """

    _modelname = "interface"
    _identifiers = ("device", "name")
    _attributes = ("type", "status", "enabled", "description", "mac_address", "mtu")

    device: str
    name: str
    type: str = "other"
    status: str = "active"
    enabled: bool = True
    description: Optional[str] = None
    mac_address: Optional[str] = None
    mtu: Optional[int] = None


# ---------------------------------------------------------------------------
# IP Prefix
# ---------------------------------------------------------------------------

class NetCrackerPrefix(DiffSyncModel):
    """Maps a NetCracker IP subnet/prefix to a Nautobot Prefix.

    Identifiers:
        prefix:     CIDR notation string (e.g. '10.0.0.0/24').
        namespace:  Nautobot Namespace name (default 'Global').

    Attributes:
        status:      Nautobot status slug.
        description: Free-text description.
        vrf:         VRF name (optional).
        location:    Site/Location name (optional).
    """

    _modelname = "prefix"
    _identifiers = ("prefix", "namespace")
    _attributes = ("status", "description", "vrf", "location")

    prefix: str
    namespace: str = "Global"
    status: str = "active"
    description: Optional[str] = None
    vrf: Optional[str] = None
    location: Optional[str] = None


# ---------------------------------------------------------------------------
# IP Address
# ---------------------------------------------------------------------------

class NetCrackerIPAddress(DiffSyncModel):
    """Maps a NetCracker IP address allocation to a Nautobot IPAddress.

    Identifiers:
        address:    IP/prefix-length string (e.g. '10.0.0.1/24').
        namespace:  Nautobot Namespace name (default 'Global').

    Attributes:
        status:     Nautobot status slug.
        dns_name:   Reverse DNS name.
        description: Free-text description.
    """

    _modelname = "ip_address"
    _identifiers = ("address", "namespace")
    _attributes = ("status", "dns_name", "description")

    address: str
    namespace: str = "Global"
    status: str = "active"
    dns_name: Optional[str] = None
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Circuit
# ---------------------------------------------------------------------------

class NetCrackerCircuit(DiffSyncModel):
    """Maps a NetCracker circuit/link to a Nautobot Circuit.

    Identifiers:
        cid:      Circuit ID / reference number.
        provider: Nautobot Provider name.

    Attributes:
        circuit_type: Nautobot CircuitType name.
        status:       Nautobot status slug.
        description:  Free-text description.
        commit_rate:  Committed bandwidth in Kbps.
        comments:     Free-text notes.
    """

    _modelname = "circuit"
    _identifiers = ("cid", "provider")
    _attributes = ("circuit_type", "status", "description", "commit_rate", "comments")

    cid: str
    provider: str
    circuit_type: str = "Unknown"
    status: str = "active"
    description: Optional[str] = None
    commit_rate: Optional[int] = None
    comments: Optional[str] = None
