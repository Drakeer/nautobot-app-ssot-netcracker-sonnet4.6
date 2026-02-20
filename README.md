# nautobot-app-ssot-netcracker

A Nautobot SSoT application that synchronises data from **NetCracker** (via direct PostgreSQL access) into **Nautobot**, treating NetCracker as the Single Source of Truth.
THIS IS NOT INTENDED FOR USE.  THIS IS A CLAUDE CODE USE CASE AND EVALUATION OF MODELS AND DIFFERENT CONTEXT ENGINEERING

Built on the [`nautobot-app-ssot`](https://github.com/nautobot/nautobot-app-ssot) framework using [DiffSync](https://github.com/networktocode/diffsync).

---

## Data Scope

| NetCracker concept | Nautobot object |
|--------------------|----------------|
| Site / Location    | `dcim.Location` |
| Device / Node      | `dcim.Device`   |
| Interface          | `dcim.Interface` |
| IP Prefix / Subnet | `ipam.Prefix`   |
| IP Address         | `ipam.IPAddress` |
| Circuit / Link     | `circuits.Circuit` |

---

## Requirements

- Python ≥ 3.10
- Nautobot ≥ 2.0
- nautobot-app-ssot ≥ 2.0
- PostgreSQL driver: `psycopg2-binary`

---

## Installation

```bash
pip install nautobot-app-ssot-netcracker
```

Add to `INSTALLED_APPS` in your Nautobot config:

```python
INSTALLED_APPS = [
    ...
    "nautobot_ssot",
    "nautobot_ssot_netcracker",
]
```

Run migrations:

```bash
nautobot-server migrate
```

---

## Configuration

1. In the Nautobot UI, go to **Secrets → Secrets Groups** and create a group containing your NetCracker PostgreSQL password.
2. Navigate to **Plugins → NetCracker SSoT → Configuration** and create a `NetCrackerConfig` record:
   - DB Host, Port, Name, User
   - Secrets Group (for the password)
   - Per-object conflict strategy

### Conflict Strategies

| Strategy    | Behaviour |
|-------------|-----------|
| `overwrite` | NetCracker always wins — Nautobot records are updated |
| `skip`      | Create new records only; never update existing ones |
| `flag`      | Log a conflict warning; do not create or update |

Configure independently per object type (`location`, `device`, `prefix`, `ip_address`, `circuit`).

---

## First-Time Setup — Schema Discovery

Since the NetCracker PostgreSQL schema varies by deployment, run the **Schema Discovery** job first:

1. Go to **Jobs → NetCracker SSoT → NetCracker Schema Discovery**
2. Run the job (optionally filter by table name)
3. Review the output to identify the real table and column names
4. Update the placeholder names in `adapter_netcracker.py` (search for `# SCHEMA: update after discovery`)

---

## Running a Sync

**From the Nautobot UI:**
1. Go to **Plugins → SSoT → Data Sources**
2. Select **NetCracker → Nautobot Sync**
3. Optionally enable **Dry Run** to preview changes without writing
4. Click **Run**

**From the CLI:**
```bash
nautobot-server runjob nautobot_ssot_netcracker.jobs.NetCrackerDataSource
```

**Scheduled:**
Use Nautobot's built-in Job Scheduling to run on a cron schedule.

---

## Development

```bash
# Clone and install in editable mode
git clone https://github.com/your-org/nautobot-app-ssot-netcracker
cd nautobot-app-ssot-netcracker
pip install -e ".[dev]"

# Start the dev environment (Nautobot + stub NetCracker DB)
cp development/creds.env.example development/creds.env
docker compose -f development/docker-compose.yml up -d

# Run tests
pytest tests/
```

---

## Project Structure

```
nautobot_ssot_netcracker/
├── apps.py                   # NautobotAppConfig
├── models.py                 # NetCrackerConfig (DB connection + conflict strategy)
├── forms.py                  # Configuration form
├── admin.py                  # Django admin
├── signals.py                # SSoT framework registration
├── urls.py                   # (empty — uses Jobs UI)
├── utils.py                  # SQLAlchemy engine factory + schema discovery helpers
├── jobs.py                   # NetCrackerDataSource + NetCrackerSchemaDiscoveryJob
└── diffsync/
    ├── models.py             # DiffSync model definitions
    ├── adapter_netcracker.py # PostgreSQL source adapter
    └── adapter_nautobot.py  # Nautobot target adapter (with conflict strategy)
```
