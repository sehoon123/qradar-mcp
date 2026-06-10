# IBM QRadar MCP Server - Read-Only Local Fork

An open-source Model Context Protocol (MCP) server for IBM QRadar SIEM. This
fork is optimized for local Python usage and keeps the default runtime profile
read-only.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

The server exposes QRadar data to MCP clients through FastMCP tools. It can
query offenses, Ariel search data, saved searches, assets, log sources, rules,
system metadata, QID/category metadata, health data, API discovery metadata,
forensics cases, QVM data, and composite investigation context.

This branch keeps QRadar data mutation disabled by default:

- `GET` tools are enabled by default.
- `DELETE` is disabled.
- Non-allowlisted `POST` tools are disabled.
- Two Ariel `POST` tools are explicitly allowlisted because they are read-only
  from a QRadar data perspective:
  - `CreateArielSearchTool` creates a transient Ariel search job.
  - `ValidateAQLTool` validates AQL without changing QRadar data.
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

The adapter currently tracks 80 tool implementations. The default
`feature_toggles.json` profile registers the read-only-safe subset and skips
mutating tools.

Enabled read-only areas include:

- Offenses and offense context
- Ariel searches, saved searches, AQL validation, and Ariel metadata
- Reference data reads
- Assets and asset properties
- Log sources and log source types
- Analytics rules, building blocks, and custom actions
- System and access metadata
- Network hierarchy, domains, regex properties, and calculated properties
- QID records, DSM event mappings, and event categories
- Health data summaries
- QRadar API endpoint discovery
- Forensics cases
- QVM vulnerabilities and assets
- Composite offense investigation context

Network service tools are present but disabled by default in the read-only local
profile.

## Local Python Setup

Use this path when Docker is not available.

### 1. Clone and enter the repository

```bash
git clone https://github.com/sehoon123/qradar-mcp.git
cd qradar-mcp
git checkout read-only-composite-tools
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
    "host": "qradar.example.com",
    "sec_token": "",
    "csrf_token": "",
    "authorized_service_token": "YOUR_AUTHORIZED_SERVICE_TOKEN",
    "app_id": "",
    "verify_ssl": false,
    "proxy": null
  },
  "server": {
    "host": "127.0.0.1",
    "port": 5000,
    "debug": true
  }
}
```

Notes:

- `qradar.host` can include or omit `https://`; the client calls QRadar over
  HTTPS.
- Do not include `/api` in `qradar.host`.
- Use `verify_ssl: true` when your local trust store can validate the QRadar
  certificate.
- User session auth is also supported with `sec_token` and `csrf_token`.

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
    "DELETE": false
  },
  "read_only_post_allowlist": [
    "CreateArielSearchTool",
    "ValidateAQLTool"
  ]
}
```

For strict read-only operation, keep `read_only_mode` enabled and keep
`POST`/`DELETE` disabled. To hide a whole category, set its group toggle to
`false`.

## Optional Docker Usage

Docker is not required for local Python mode. If you do use Docker, the compose
file mounts `config.json` at `/opt/app-root/config.json`, which is where the
config loader expects it inside the container.

```bash
cp config.example.json config.json
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
  -p 5001:5000 \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=5000 \
  -v $(pwd)/config.json:/opt/app-root/config.json:ro \
  qradar-mcp:latest
```

## Development

Install development dependencies when you want to run the full test suite:

```bash
python -m pip install -e ".[dev]"
python -m pytest tests
```

Useful focused checks for the read-only fork:

```bash
python -m pytest tests/test_read_only_allowlist.py
python -m pytest tests/test_compatibility.py
python -m pytest tests/test_composite_read_only.py
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
- SSL errors in a lab: set `verify_ssl: false`. Prefer `true` for production.
- Tool reports unsupported endpoint: the compatibility gate did not find that
  endpoint in the connected QRadar console's `/help/endpoints` catalog.

## Security

- Never commit `config.json`, `mcp_settings.json`, or `.env`.
- Prefer authorized service tokens scoped for the minimum required access.
- Keep the server bound to `127.0.0.1` for local-only operation.
- Keep `read_only_mode` enabled for no-mutation operation.
- Do not enable `DELETE` or non-allowlisted `POST` tools unless you explicitly
  intend to allow QRadar data changes.

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
