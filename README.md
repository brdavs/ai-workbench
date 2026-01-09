# AI Workbench v2 (multi-project) — Codex CLI + Kilo Code CLI + MCP tools + Playwright runner

A **reusable, dockerized AI dev workstation** you can use from **any existing project**.
It does **not** replace your project’s own `docker-compose.yml`. It provides a consistent CLI
environment (git, python, node, docker CLI) plus optional **MCP tools** for agent workflows,
and a portable way to run **Playwright E2E** tests.

## What you get

- **`dev` container**: Ubuntu-based CLI with:
  - `git`, `ssh`, `jq`, `ripgrep`, `fd`, etc.
  - Python 3 + venv/pip
  - Node.js + npm
  - Docker CLI + Compose plugin (uses the **host Docker socket**)
  - **Codex CLI** (`@openai/codex`)
  - **Kilo Code CLI** (`@kilocode/cli`)
- **`mcp` container** (optional): MCP server exposing safe tools for:
  - `git_status`, `git_diff`, `git_commit`
  - `compose_up/down/ps/logs/exec/run` (against the *project in /workspace*)
  - `run_playwright` (uses project `e2e` if present, else fallback runner)

> Security note: mounting `/var/run/docker.sock` gives containers effectively **host-level Docker control**.
Use on trusted machines only.

---

## One-time setup (run once per machine)

### 1) Unpack + install the `aiw` launcher
Suggested location:

```bash
mkdir -p ~/.ai-workbench
tar -xzf ai-workbench-v2.tar.gz -C ~/.ai-workbench --strip-components=1
```

Put `aiw` on your PATH:

```bash
mkdir -p ~/.local/bin
ln -sf ~/.ai-workbench/bin/aiw ~/.local/bin/aiw
chmod +x ~/.ai-workbench/bin/aiw
```

### 2) Build the workbench images once
```bash
cd ~/.ai-workbench
docker compose build
```

### 3) (Recommended) Register MCP with Codex once
This allows Codex CLI to launch the workbench MCP server automatically when needed.

```bash
# Run on your HOST (outside containers)
codex mcp add aiw -- aiw mcp
```

If `codex` is not installed on the host, install it once:
```bash
npm i -g @openai/codex
```

---

## Daily use (per project)

From any repo:

```bash
cd /path/to/your/project
aiw shell
```

Inside the container your project is mounted at `/workspace`.

### Use the project’s compose as-is
```bash
docker compose up -d
docker compose ps
docker compose exec <service> <command>
docker compose logs -f <service>
```

### Run Codex CLI
From inside `aiw shell`:
```bash
codex
```

Or from the host:
```bash
aiw codex
```

To load an external OpenSpec `AGENTS.md` (not in your project):
```bash
aiw codex-agent
```

### Docker socket permissions (common issue)
If `aiw codex` fails to start the MCP server with a Docker socket permission error,
run with the socket's group id:

```bash
AIW_GID=$(stat -c '%g' /var/run/docker.sock) aiw codex
```

This overrides the group used by the dev container so it can access `/var/run/docker.sock`.

### MCP when running Codex inside the dev container
When you run `aiw codex`, Codex runs inside the dev container, so the MCP command must
start the MCP container via Docker Compose. Set it once from inside `aiw shell`:

```bash
codex mcp add aiw -- bash -lc 'PROJECT_DIR="$PROJECT_DIR_HOST" docker compose -f /aiw/docker-compose.yml run --rm -T mcp'
```

If you see `groups: cannot find name for group ID 998`, it's harmless and does not
affect Docker socket permissions.

### Run Kilo Code CLI
From inside `aiw shell`:
```bash
kilocode --workspace /workspace
```

To load an external OpenSpec `AGENTS.md` (not in your project):
```bash
aiw kilocode-agent
```

### Run Playwright E2E
If your project defines an `e2e` service:
```bash
docker compose run --rm e2e
```

If it does not, use the workbench fallback:
```bash
aiw e2e --base-url http://localhost:3000
```

To keep Playwright deps out of your project, use an external E2E workspace (like OpenSpec):
```bash
aiw e2e init
aiw e2e --base-url http://localhost:3000
```
This creates `e2e/<repo-name>` under the workbench repo. You can edit tests and config there.
To see the path:
```bash
aiw e2e path
```
You can also override with `--e2e-dir PATH`, or force the project directory with `--use-project`.
If the fallback runner needs a specific Docker network, set `AIW_E2E_NETWORK` (for example: `export AIW_E2E_NETWORK=my-network`).

To resolve custom hostnames from the MCP container and the fallback Playwright runner,
add them under the `mcp` service `extra_hosts` mapping in `docker-compose.yml`, and set
`MCP_EXTRA_HOSTS` before starting MCP (host or dev container, depending on how you run it):
```yaml
services:
  mcp:
    extra_hosts:
      app.local: host-gateway
      api.local: 10.0.0.5
```
```bash
export MCP_EXTRA_HOSTS='["app.local:host-gateway","api.local:10.0.0.5"]'
```
You can also use a comma-separated string: `app.local:host-gateway,api.local:10.0.0.5`.
If your project uses an `e2e` service, add `extra_hosts` to that service as well.

---
## OpenSpec (external per-project files)

OpenSpec files live in the workbench repo (not inside your project). Create them with:

```bash
aiw openspec init
```

This runs `npx @fission-ai/openspec@latest` inside the dev container and writes to:
`openspec/<repo-name>` under the workbench repo.

```bash
aiw openspec path
```

---
## `aiw doctor` (validate your setup)

Run this on the host from any project directory:

```bash
cd /path/to/project
aiw doctor
```

It checks:
- Docker engine reachable
- `docker compose` available
- the workbench `dev` container can run
- Codex CLI availability (host + container)
- MCP server container self-test
- hints if you still need the one-time `codex mcp add aiw -- aiw mcp`

---

## Templates (optional helpers)

See `templates/`:

- `AGENT.md.example` — starter guidance file you can copy into a project root.
- `docker-compose.e2e.override.yml.example` — example how to add an `e2e` service using Playwright.

These are **optional** and safe to ignore.

---

## Files

- `docker-compose.yml` — workbench services
- `dev/` — Dockerfile for CLI image
- `mcp/` — MCP server implementation
- `bin/aiw` — convenience launcher + doctor
- `templates/` — optional templates
