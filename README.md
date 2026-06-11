# IBM QRadar MCP Server - Read-Only Local Fork

An open-source Model Context Protocol (MCP) server for IBM QRadar SIEM. This
fork is optimized for local Python usage and keeps the default runtime profile
read-only.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

The server exposes QRadar data to MCP clients through FastMCP tools. It can
query offenses, Ariel search data, saved searches, assets, log sources, rules,
QID/category metadata, API discovery metadata, and composite investigation
context. Additional system, config, health, forensics, and QVM tool
implementations exist but are disabled in the default SOC read-only profile.

This branch keeps QRadar data mutation disabled by default:

- `GET` tools are enabled by default.
- `DELETE` is disabled.
- Non-allowlisted `POST` tools are disabled.
- A limited set of non-mutating or bounded transient-search `POST` tools is
  explicitly allowlisted:
  - `ValidateAQLTool` validates AQL without changing QRadar data.
  - `InvestigateOffenseEventsTool` runs a bounded offense event search workflow.
  - Raw `CreateArielSearchTool` and `CancelArielSearchTool` implementations are
    available for explicitly enabled operator profiles, but not the default
    profile.
- A runtime compatibility gate checks the connected QRadar console's
  `/help/versions` and `/help/endpoints` catalog before calling newly added
  tools. The intended compatibility baseline is QRadar API 24.0+.

## Project Structure

```text
qradar-mcp/
|-- client/             # QRadar REST API client
|-- tools/              # MCP tools
|-- resources/          # MCP resources
|-- utils/              # Auth, logging, feature toggles, validation
|-- tests/              # Unit and safety tests
|-- server.py           # FastMCP server entry point
|-- feature_toggles.json
|-- config.example.json
`-- Dockerfile
```

## Tool Coverage

The adapter currently tracks 123 tool implementations. The default
`feature_toggles.json` profile registers the read-only-safe subset and skips
QRadar-mutating tools before they are imported as registration candidates.

Enabled read-only areas include:

- Offenses and offense context
- Ariel searches, saved searches, search metadata, AQL validation, and Ariel metadata
- Reference data reads
- Assets and asset properties
- Log sources and log source types
- Analytics rules, building blocks, and custom actions
- QID records, DSM event mappings, and event categories
- QRadar API endpoint, version, and resource discovery
- QRadar deployment diagnostics through `qradar_doctor`
- Composite offense investigation context and Ariel event evidence workflow

System/config metadata, health metrics, forensics, QVM, and network service
tools are present but disabled by default in the read-only local profile.

## Local Python Setup

Use this path when Docker is not available.

### 1. Clone and enter the repository

```bash
git clone https://github.com/sehoon123/qradar-mcp.git
cd qradar-mcp
```

### 2. Create a virtual environment

On macOS or Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

### 4. Configure QRadar authentication

For local mode, the config loader reads `config.json` from the parent directory
of the `qradar-mcp` checkout. This is intentional and matches
`client/qradar_rest_client.py`.

On macOS or Linux:

```bash
cp config.example.json ../config.json
${EDITOR:-vi} ../config.json
```

On Windows PowerShell:

```powershell
Copy-Item .\config.example.json ..\config.json
notepad ..\config.json
```

Recommended local authentication is an authorized service token:

```json
{
  "qradar": {
    "host": "http://192.168.1.10",
    "sec_token": "",
    "csrf_token": "",
    "authorized_service_token": "YOUR_AUTHORIZED_SERVICE_TOKEN",
    "app_id": "",
    "verify_ssl": true,
    "allow_plain_http_private_network": true,
    "api_version": "27.0",
    "proxy": null
  },
  "server": {
    "host": "127.0.0.1",
    "port": 5000,
    "debug": true
  },
  "compatibility": {
    "fail_mode": "closed"
  },
  "auth": {
    "identity_probe": "strict"
  }
}
```

Notes:

- `qradar.host` can include `http://` or `https://`. The client preserves an
  explicit scheme, which supports internal lab consoles such as
  `http://192.168.x.x`. If the scheme is omitted, HTTPS is used by default.
- Plain HTTP is blocked unless `allow_plain_http_private_network` is explicitly
  enabled and the host is a private IP or internal hostname such as `.local` or
  `.internal`.
- Do not include `/api` in `qradar.host`; the client tolerates it but normalizes
  API paths internally.
- `qradar.api_version` is sent as the QRadar `Version` header on every API
  request. Set it to the API version supported by your console.
- `verify_ssl` defaults to `true`. Set it to `false` only for lab or
  self-signed certificate environments.
- User session auth is also supported with `sec_token` and `csrf_token`.
- `compatibility.fail_mode` defaults to `open` in code for lab friendliness, but
  the example config uses `closed` so `/help/versions` and `/help/endpoints`
  must be available before gated tools run.
- `auth.identity_probe` defaults to `strict`. `permissive` lets a request with
  a QRadar token proceed when identity lookup endpoints are unavailable, and
  `disabled_for_local_config` skips the identity lookup for local config tokens.

### 5. Run the server

```bash
python server.py
```

With the default example config, the MCP endpoint is:

```text
http://127.0.0.1:5000/mcp
```

The server bind address comes from `../config.json`:

```json
"server": {
  "host": "127.0.0.1",
  "port": 5000
}
```

You can override the bind address without editing the config:

On macOS or Linux:

```bash
MCP_PORT=5002 python server.py
```

On Windows PowerShell:

```powershell
$env:MCP_PORT = "5002"
python server.py
```

`MCP_HOST` is also supported. For local-only usage, keep it at `127.0.0.1`
unless you intentionally need another machine to reach the server.

### 6. Verify the local server

In a second terminal with the virtual environment activated:

```bash
python tests/local_mcp_connection.py
```

The smoke test reads the same parent `../config.json` file, connects to the
configured MCP endpoint, initializes an MCP session, and lists available tools.
You can override the target URL with `MCP_BASE_URL`, for example:

```bash
MCP_BASE_URL=http://127.0.0.1:5002 python tests/local_mcp_connection.py
```

Process health endpoints are also available:

```text
GET /healthz  # process liveness, no QRadar API call
GET /readyz   # server initialization checks, no QRadar API call
```

These endpoints bypass QRadar authentication middleware so Docker and
orchestrator health checks do not depend on QRadar token validity or console
availability.

After connecting an MCP client, run `qradar_doctor` to check the configured
host scheme, API Version header, `/help` catalog availability, identity probe,
feature-toggle posture, and transport warnings for internal HTTP deployments.

## MCP Client Configuration

Point your MCP client at:

```text
http://127.0.0.1:5000/mcp
```

When the server runs with `../config.json`, QRadar authentication can come from
that local config file. Clients that support custom headers may also pass QRadar
tokens directly:

```text
SEC: <authorized_service_token_or_sec_token>
QRadarCSRF: <csrf_token_for_user_session_auth>
```

## Feature Toggles

Runtime tool registration is controlled by `feature_toggles.json`.

Important default settings in this fork:

```json
{
  "read_only_mode": true,
  "compatibility_gate_enabled": true,
  "verb_toggles": {
    "GET": true,
    "POST": false,
    "DELETE": false,
    "PUT": false,
    "PATCH": false
  },
  "read_only_post_allowlist": [
    "ValidateAQLTool",
    "InvestigateOffenseEventsTool"
  ]
}
```

For strict read-only operation, keep `read_only_mode` enabled and keep
`POST`/`DELETE` disabled. To hide a whole category, set its group toggle to
`false`.

Tool outputs default to structured JSON for agent workflows. Tools that expose
`format_output` return human-readable text only when `format_output=true`.

## Optional Docker Usage

Docker is not required for local Python mode. If you do use Docker, the compose
file mounts `config.json` at `/opt/app-root/config.json`, which is where the
config loader expects it inside the container.

```bash
cp config.example.json config.json
cp .env.example .env
docker-compose up -d
```

The Docker endpoint is mapped to:

```text
http://localhost:5001/mcp
```

Manual Docker example:

```bash
docker build -t qradar-mcp:latest .
docker run -d \
  --name qradar-mcp-server \
  -p 127.0.0.1:5001:5000 \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=5000 \
  -v $(pwd)/config.json:/opt/app-root/config.json:ro \
  qradar-mcp:latest
```

The compose example also publishes to `127.0.0.1:5001` by default. Use a
reverse proxy, VPN, or firewall allowlist before exposing the MCP server to a
shared network.

The image and compose file include a healthcheck against `/healthz`. Use
`/readyz` when an orchestrator should also verify that QRadar host settings and
the shared HTTP client were initialized.

## API Version and Permissions

Set `qradar.api_version` in `config.json` or `QRADAR_API_VERSION` in the
environment. The value is sent as the QRadar `Version` header on every REST API
request. Pin this to a version supported by your console, such as `27.0` for
current QRadar 7.5 deployments, instead of relying on QRadar's implicit latest
API behavior.

Permission and module expectations vary by console version and deployment:

| Area | Main endpoints | Expected access |
| --- | --- | --- |
| Help discovery | `/help/versions`, `/help/endpoints`, `/help/resources` | API documentation visibility |
| Offenses | `/siem/offenses`, notes, actors, saved searches | SIEM offense read access |
| Ariel | `/ariel/searches`, validators, metadata, results | Ariel event or flow search access |
| Reference data | `/reference_data_collections/*` | Reference data read access |
| Assets/log sources/rules | `/asset_model/*`, `/config/*`, `/analytics/*` | Corresponding QRadar configuration read access |
| Health metrics | `/health/*` | Health data or administrative read access |
| QVM | `/qvm/*` | QVM license/module and vulnerability read access |
| Forensics | `/forensics/*` | Forensics license/module and case read access |

The default read-only profile still allowlists transient `POST` calls for AQL
validation and the bounded composite Ariel evidence workflow. The raw Ariel
search creation/cancel tools are disabled by default and should be exposed only
in an explicit operator profile.
The REST client retries only explicitly safe POST endpoints such as AQL
validation; Ariel search creation is not automatically retried because it may
already have created a QRadar search job before a timeout is observed.

## Development

Install development dependencies when you want to run the full test suite:

```bash
python -m pip install -e ".[dev]"
python -m pytest tests --cov=qradar_mcp --cov-report=term-missing
```

Coverage has an 80% minimum gate in `pyproject.toml`. GitHub Actions runs the
same coverage check plus pylint on pushes and pull requests.

Useful focused checks for the read-only fork:

```bash
python -m pytest tests/test_read_only_allowlist.py
python -m pytest tests/test_compatibility.py
python -m pytest tests/test_composite_read_only.py
python -m pytest tests/test_endpoint_registry.py
```

## Troubleshooting

- `ModuleNotFoundError: qradar_mcp`: run `python -m pip install -e .` from the
  repository root.
- `config.json not found`: copy `config.example.json` to the parent directory
  as `../config.json`.
- `Connection refused`: check the configured `server.port`, `MCP_PORT`, and the
  URL used by your MCP client.
- `401` or authentication errors: refresh the QRadar token or verify that the
  authorized service token is still valid.
- SSL errors in a lab: set `verify_ssl: false` only when the local trust store
  cannot validate the QRadar certificate.
- Tool reports unsupported endpoint: the compatibility gate did not find that
  endpoint in the connected QRadar console's `/help/endpoints` catalog.

## Security

- Never commit `config.json`, `mcp_settings.json`, or `.env`.
- Prefer authorized service tokens scoped for the minimum required access.
- Keep the server bound to `127.0.0.1` for local-only operation.
- Keep `read_only_mode` enabled for no-mutation operation.
- Do not enable `DELETE` or non-allowlisted `POST` tools unless you explicitly
  intend to allow QRadar data changes.
- Audit and structured logs redact credentials and summarize AQL, filter, and
  note content by length and hash instead of recording raw SOC investigation
  data.

## License

Copyright 2026 IBM Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## IBM Public Repository Disclosure

All content in these repositories including code has been provided by IBM under
the associated open source software license and IBM is under no obligation to
provide enhancements, updates, or support. IBM developers produced this code as
an open source project (not as an IBM product), and IBM makes no assertions as
to the level of quality nor security, and will not be maintaining this code
going forward.
