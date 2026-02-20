-- =============================================================
-- Stub NetCracker database seed for local development / testing
--
-- Creates placeholder tables and sample data that mirror the
-- column aliases used in adapter_netcracker.py.
--
-- IMPORTANT: Replace these with the real NetCracker schema
-- after running the NetCrackerSchemaDiscoveryJob.
-- =============================================================

-- Locations / Sites
CREATE TABLE IF NOT EXISTS NC_LOCATION_TABLE (
    NC_LOCATION_NAME      VARCHAR(255) PRIMARY KEY,
    NC_LOCATION_TYPE      VARCHAR(100),
    NC_LOCATION_STATUS    VARCHAR(50),
    NC_LOCATION_DESC      TEXT,
    NC_LOCATION_LATITUDE  DOUBLE PRECISION,
    NC_LOCATION_LONGITUDE DOUBLE PRECISION
);

INSERT INTO NC_LOCATION_TABLE VALUES
    ('NYC-DC1', 'Site', 'active', 'New York primary datacenter', 40.7128, -74.0060),
    ('LAX-DC2', 'Site', 'active', 'Los Angeles secondary datacenter', 33.9425, -118.4081),
    ('CHI-DC3', 'Site', 'planned', 'Chicago expansion site', 41.8781, -87.6298);

-- Devices
CREATE TABLE IF NOT EXISTS NC_DEVICE_TABLE (
    NC_DEVICE_NAME    VARCHAR(255) PRIMARY KEY,
    NC_DEVICE_TYPE    VARCHAR(100),
    NC_MANUFACTURER   VARCHAR(100),
    NC_DEVICE_ROLE    VARCHAR(100),
    NC_DEVICE_STATUS  VARCHAR(50),
    NC_LOCATION_NAME  VARCHAR(255),
    NC_SERIAL_NUMBER  VARCHAR(100),
    NC_PLATFORM       VARCHAR(100),
    NC_COMMENTS       TEXT
);

INSERT INTO NC_DEVICE_TABLE VALUES
    ('nyc-core-01', 'ASR1001-X', 'Cisco', 'Core Router', 'active', 'NYC-DC1', 'FTX1234ABCD', 'IOS-XE', NULL),
    ('nyc-agg-01',  'Nexus 9300', 'Cisco', 'Aggregation Switch', 'active', 'NYC-DC1', 'FTX5678EFGH', 'NX-OS', NULL),
    ('lax-core-01', 'MX480',     'Juniper', 'Core Router', 'active', 'LAX-DC2', 'JN1234WXYZ', 'Junos', NULL);

-- Interfaces
CREATE TABLE IF NOT EXISTS NC_INTERFACE_TABLE (
    NC_DEVICE_NAME       VARCHAR(255),
    NC_INTERFACE_NAME    VARCHAR(255),
    NC_INTERFACE_TYPE    VARCHAR(100),
    NC_INTERFACE_STATUS  VARCHAR(50),
    NC_INTERFACE_ENABLED BOOLEAN,
    NC_INTERFACE_DESC    TEXT,
    NC_MAC_ADDRESS       VARCHAR(17),
    NC_MTU               INTEGER,
    PRIMARY KEY (NC_DEVICE_NAME, NC_INTERFACE_NAME)
);

INSERT INTO NC_INTERFACE_TABLE VALUES
    ('nyc-core-01', 'GigabitEthernet0/0', '1000base-t', 'active', TRUE, 'Uplink to ISP', '00:1A:2B:3C:4D:5E', 1500),
    ('nyc-core-01', 'GigabitEthernet0/1', '1000base-t', 'active', TRUE, 'Core link to nyc-agg-01', NULL, 9000),
    ('nyc-agg-01',  'Ethernet1/1',        '10gbase-x-sfpp', 'active', TRUE, 'Uplink to nyc-core-01', NULL, 9000),
    ('lax-core-01', 'ge-0/0/0',           '1000base-t', 'active', TRUE, 'ISP uplink', NULL, 1500);

-- IP Prefixes
CREATE TABLE IF NOT EXISTS NC_PREFIX_TABLE (
    NC_PREFIX_CIDR   VARCHAR(50) PRIMARY KEY,
    NC_NAMESPACE     VARCHAR(100),
    NC_PREFIX_STATUS VARCHAR(50),
    NC_PREFIX_DESC   TEXT,
    NC_VRF_NAME      VARCHAR(100),
    NC_LOCATION_NAME VARCHAR(255)
);

INSERT INTO NC_PREFIX_TABLE VALUES
    ('10.0.0.0/8',    'Global', 'active', 'RFC1918 summary',        NULL,      NULL),
    ('10.1.0.0/16',   'Global', 'active', 'NYC infrastructure',     NULL,      'NYC-DC1'),
    ('10.1.1.0/24',   'Global', 'active', 'NYC management subnet',  NULL,      'NYC-DC1'),
    ('10.2.0.0/16',   'Global', 'active', 'LAX infrastructure',     NULL,      'LAX-DC2'),
    ('192.168.100.0/24', 'Global', 'active', 'OOB management',      'MGMT',    NULL);

-- IP Addresses
CREATE TABLE IF NOT EXISTS NC_IP_ADDRESS_TABLE (
    NC_IP_ADDRESS VARCHAR(50) PRIMARY KEY,
    NC_NAMESPACE  VARCHAR(100),
    NC_IP_STATUS  VARCHAR(50),
    NC_DNS_NAME   VARCHAR(255),
    NC_IP_DESC    TEXT
);

INSERT INTO NC_IP_ADDRESS_TABLE VALUES
    ('10.1.1.1/24',  'Global', 'active', 'nyc-core-01.mgmt.example.com', 'NYC core router management'),
    ('10.1.1.2/24',  'Global', 'active', 'nyc-agg-01.mgmt.example.com',  'NYC agg switch management'),
    ('10.2.1.1/24',  'Global', 'active', 'lax-core-01.mgmt.example.com', 'LAX core router management'),
    ('192.168.100.10/24', 'Global', 'active', NULL,                       'OOB access');

-- Circuits
CREATE TABLE IF NOT EXISTS NC_CIRCUIT_TABLE (
    NC_CIRCUIT_ID       VARCHAR(100) PRIMARY KEY,
    NC_PROVIDER_NAME    VARCHAR(255),
    NC_CIRCUIT_TYPE     VARCHAR(100),
    NC_CIRCUIT_STATUS   VARCHAR(50),
    NC_CIRCUIT_DESC     TEXT,
    NC_COMMIT_RATE      INTEGER,
    NC_CIRCUIT_COMMENTS TEXT
);

INSERT INTO NC_CIRCUIT_TABLE VALUES
    ('CKT-NYC-001', 'AT&T',    'Internet Transit', 'active', 'NYC primary internet uplink',   10000000,  NULL),
    ('CKT-NYC-002', 'Comcast', 'Internet Transit', 'active', 'NYC secondary internet uplink', 1000000,   NULL),
    ('CKT-LAX-001', 'Zayo',    'Dark Fiber',       'active', 'LAX to NYC backbone',           100000000, 'Dark fiber between LAX and NYC');
