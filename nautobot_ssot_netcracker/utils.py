"""Utility functions for the NetCracker SSoT integration.

Provides:
- SQLAlchemy engine factory backed by NetCrackerConfig + Nautobot SecretsGroup
- Conflict strategy helper
- Schema introspection helpers used by the discovery job
"""

import logging
from typing import Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------

_engine_cache: Optional[Engine] = None


def get_netcracker_engine(force_new: bool = False) -> Engine:
    """Build (or return cached) SQLAlchemy engine for the NetCracker PostgreSQL DB.

    Credentials are retrieved from the configured Nautobot SecretsGroup so that
    plaintext passwords are never stored in the database or settings files.

    Args:
        force_new: If True, discard any cached engine and create a fresh one.

    Returns:
        A SQLAlchemy Engine instance.

    Raises:
        RuntimeError: If no NetCrackerConfig record exists.
        Exception: If the SecretsGroup fails to provide the password.
    """
    global _engine_cache

    if _engine_cache is not None and not force_new:
        return _engine_cache

    from nautobot_ssot_netcracker.models import NetCrackerConfig
    from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices

    config = NetCrackerConfig.objects.first()
    if config is None:
        raise RuntimeError(
            "No NetCrackerConfig record found. "
            "Please configure the NetCracker SSoT integration in Nautobot before running a sync."
        )

    try:
        password = config.db_secrets.get_secret_value(
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to retrieve NetCracker DB password from SecretsGroup '{config.db_secrets}': {exc}"
        ) from exc

    url = (
        f"postgresql+psycopg2://{config.db_user}:{password}"
        f"@{config.db_host}:{config.db_port}/{config.db_name}"
    )

    logger.debug("Creating SQLAlchemy engine for %s:%s/%s", config.db_host, config.db_port, config.db_name)
    _engine_cache = create_engine(url, pool_pre_ping=True, echo=False)
    return _engine_cache


# ---------------------------------------------------------------------------
# Conflict strategy helper
# ---------------------------------------------------------------------------

def get_conflict_strategy(object_type: str) -> str:
    """Return the configured conflict strategy for a given object type.

    Args:
        object_type: One of 'location', 'device', 'prefix', 'ip_address', 'circuit'.

    Returns:
        Strategy string: 'overwrite', 'skip', or 'flag'. Defaults to 'overwrite'
        if no config or no strategy is set for the given type.
    """
    from nautobot_ssot_netcracker.models import NetCrackerConfig

    config = NetCrackerConfig.objects.first()
    if config is None:
        return "overwrite"
    return config.get_strategy(object_type)


# ---------------------------------------------------------------------------
# Schema introspection helpers
# ---------------------------------------------------------------------------

CANDIDATE_KEYWORDS = {
    "location": ["location", "site", "address", "region", "rack", "building"],
    "device": ["device", "node", "equipment", "element", "host", "resource"],
    "prefix": ["prefix", "subnet", "network", "cidr", "ip_block"],
    "ip_address": ["ip_address", "ipaddress", "ip_alloc", "address"],
    "circuit": ["circuit", "link", "connection", "path", "service"],
}


def discover_schema(engine: Engine) -> dict:
    """Introspect the NetCracker PostgreSQL schema.

    Queries information_schema to enumerate all user tables and their columns.
    Then scores each table against CANDIDATE_KEYWORDS to suggest which tables
    are likely to hold each Nautobot object type.

    Args:
        engine: A SQLAlchemy Engine connected to the NetCracker database.

    Returns:
        A dict with keys:
            - 'tables': {table_name: [column_name, ...]}
            - 'candidates': {object_type: [table_name, ...]}
    """
    inspector = inspect(engine)
    schemas = inspector.get_schema_names()

    # Prefer non-system schemas
    target_schemas = [s for s in schemas if s not in ("information_schema", "pg_catalog")]
    if not target_schemas:
        target_schemas = ["public"]

    all_tables: dict[str, list[str]] = {}

    with engine.connect() as conn:
        for schema in target_schemas:
            table_names = inspector.get_table_names(schema=schema)
            for table in table_names:
                fq_name = f"{schema}.{table}" if schema != "public" else table
                try:
                    columns = inspector.get_columns(table, schema=schema)
                    all_tables[fq_name] = [col["name"] for col in columns]
                except Exception as exc:
                    logger.warning("Could not inspect table %s: %s", fq_name, exc)

    candidates: dict[str, list[str]] = {ot: [] for ot in CANDIDATE_KEYWORDS}

    for table_name, columns in all_tables.items():
        table_lower = table_name.lower()
        col_names_lower = " ".join(columns).lower()

        for object_type, keywords in CANDIDATE_KEYWORDS.items():
            for kw in keywords:
                if kw in table_lower or kw in col_names_lower:
                    candidates[object_type].append(table_name)
                    break  # only add once per table per object_type

    return {"tables": all_tables, "candidates": candidates}


def format_schema_report(schema_data: dict) -> str:
    """Format the output of discover_schema() into a human-readable string.

    Args:
        schema_data: Return value of discover_schema().

    Returns:
        A formatted multi-line string suitable for logging to a Nautobot job.
    """
    lines = []
    lines.append("=" * 70)
    lines.append("NetCracker Schema Discovery Report")
    lines.append("=" * 70)

    lines.append(f"\nTotal tables found: {len(schema_data['tables'])}\n")

    lines.append("CANDIDATE TABLE MAPPINGS")
    lines.append("-" * 40)
    for object_type, tables in schema_data["candidates"].items():
        lines.append(f"\n  {object_type.upper()}:")
        if tables:
            for t in tables:
                col_list = ", ".join(schema_data["tables"].get(t, [])[:10])
                lines.append(f"    - {t}")
                lines.append(f"      columns: {col_list}")
        else:
            lines.append("    (no candidates found)")

    lines.append("\n" + "=" * 70)
    lines.append("ALL TABLES")
    lines.append("-" * 40)
    for table, cols in sorted(schema_data["tables"].items()):
        lines.append(f"\n  {table}")
        for col in cols:
            lines.append(f"    - {col}")

    return "\n".join(lines)
