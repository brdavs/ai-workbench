import json
import os
import shlex
import subprocess
from typing import List, Optional, Dict, Any

from mcp.server import FastMCP

# If set, just validate dependencies and exit.
if os.getenv("AIW_MCP_SELFTEST", "0") == "1":
    def _try(cmd: List[str]) -> str:
        try:
            p = subprocess.run(cmd, text=True, capture_output=True)
            out = (p.stdout or p.stderr or "").strip()
            return out[:500]
        except Exception as e:
            return f"ERROR: {e}"
    print("AIW_MCP_SELFTEST=1")
    print("docker:", _try(["docker", "--version"]))
    print("docker compose:", _try(["docker", "compose", "version"]))
    raise SystemExit(0)

app = FastMCP("ai-workbench")

PROJECT_DIR = os.getenv("PROJECT_DIR", "/workspace")
ALLOW_GIT = os.getenv("MCP_ALLOW_GIT", "0") == "1"
ALLOW_COMPOSE = os.getenv("MCP_ALLOW_COMPOSE", "0") == "1"
ALLOW_PLAYWRIGHT = os.getenv("MCP_ALLOW_PLAYWRIGHT", "0") == "1"
MAX_OUT = int(os.getenv("MCP_MAX_OUTPUT_CHARS", "20000"))

DENY_TOKENS = {"sudo", "su", "passwd", "chown", "chmod", "mkfs", "mount", "umount"}
DENY_SUBSTRINGS = ["rm -rf", "curl | sh", "curl|sh", "wget | sh", "wget|sh"]

def _truncate(s: str) -> str:
    if len(s) <= MAX_OUT:
        return s
    return s[:MAX_OUT] + "\n...<truncated>..."

def _run(argv: List[str], cwd: str = PROJECT_DIR, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    if not argv:
        raise ValueError("Empty command")
    if argv[0] in DENY_TOKENS:
        raise ValueError(f"Command '{argv[0]}' is blocked")
    joined = " ".join(argv)
    for bad in DENY_SUBSTRINGS:
        if bad in joined:
            raise ValueError(f"Blocked pattern: {bad}")

    p = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, env=env)
    return {
        "exit_code": p.returncode,
        "stdout": _truncate((p.stdout or "").strip()),
        "stderr": _truncate((p.stderr or "").strip()),
        "command": argv,
        "cwd": cwd,
    }

def _compose_base() -> List[str]:
    return ["docker", "compose"]

def _compose_services() -> List[str]:
    r = _run(_compose_base() + ["config", "--services"])
    if r["exit_code"] != 0:
        return []
    return [line.strip() for line in r["stdout"].splitlines() if line.strip()]

def _compose_project_name() -> str:
    name = os.getenv("COMPOSE_PROJECT_NAME")
    if name:
        return name
    return os.path.basename(os.path.abspath(PROJECT_DIR)) or "project"

def _default_network_name() -> str:
    return f"{_compose_project_name()}_default"

def _extra_hosts() -> List[str]:
    raw = os.getenv("MCP_EXTRA_HOSTS", "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            hosts = [f"{k}:{v}" for k, v in data.items()]
        elif isinstance(data, list):
            hosts = [str(item) for item in data]
        else:
            hosts = [str(data)]
    except json.JSONDecodeError:
        hosts = [part.strip() for part in raw.split(",") if part.strip()]
    return [host.strip() for host in hosts if host and ":" in host]

@app.tool()
def git_status() -> Dict[str, Any]:
    if not ALLOW_GIT:
        raise ValueError("git tools disabled")
    return _run(["git", "status"])

@app.tool()
def git_diff(args: str = "") -> Dict[str, Any]:
    if not ALLOW_GIT:
        raise ValueError("git tools disabled")
    return _run(["git", "diff"] + shlex.split(args))

@app.tool()
def git_commit(message: str) -> Dict[str, Any]:
    if not ALLOW_GIT:
        raise ValueError("git tools disabled")
    return _run(["git", "commit", "-am", message])

@app.tool()
def compose_up(services: str = "", detached: bool = True) -> Dict[str, Any]:
    if not ALLOW_COMPOSE:
        raise ValueError("compose tools disabled")
    argv = _compose_base() + ["up"]
    if detached:
        argv.append("-d")
    if services.strip():
        argv += shlex.split(services)
    return _run(argv)

@app.tool()
def compose_down(remove_volumes: bool = False) -> Dict[str, Any]:
    if not ALLOW_COMPOSE:
        raise ValueError("compose tools disabled")
    argv = _compose_base() + ["down"]
    if remove_volumes:
        argv.append("-v")
    return _run(argv)

@app.tool()
def compose_ps() -> Dict[str, Any]:
    if not ALLOW_COMPOSE:
        raise ValueError("compose tools disabled")
    return _run(_compose_base() + ["ps"])

@app.tool()
def compose_logs(service: str = "", tail: int = 200) -> Dict[str, Any]:
    if not ALLOW_COMPOSE:
        raise ValueError("compose tools disabled")
    argv = _compose_base() + ["logs", "--tail", str(tail)]
    if service.strip():
        argv.append(service.strip())
    return _run(argv)

@app.tool()
def compose_exec(service: str, command: str) -> Dict[str, Any]:
    if not ALLOW_COMPOSE:
        raise ValueError("compose tools disabled")
    return _run(_compose_base() + ["exec", "-T", service] + shlex.split(command))

@app.tool()
def compose_run(service: str, command: str = "", remove: bool = True) -> Dict[str, Any]:
    if not ALLOW_COMPOSE:
        raise ValueError("compose tools disabled")
    argv = _compose_base() + ["run"]
    if remove:
        argv.append("--rm")
    argv += ["-T", service]
    if command.strip():
        argv += shlex.split(command)
    return _run(argv)

@app.tool()
def run_playwright(base_url: str = "http://localhost:3000", command: str = "npx playwright test") -> Dict[str, Any]:
    if not ALLOW_PLAYWRIGHT:
        raise ValueError("playwright tool disabled")

    services = _compose_services()
    if "e2e" in services:
        return _run(_compose_base() + ["run", "--rm", "-T", "e2e"])

    net = _default_network_name()
    argv = ["docker", "run", "--rm", "--network", net]
    for host in _extra_hosts():
        argv += ["--add-host", host]
    argv += [
        "--shm-size=1g",
        "-e", f"BASE_URL={base_url}",
        "-v", f"{os.path.abspath(PROJECT_DIR)}:/workspace",
        "-w", "/workspace",
        "mcr.microsoft.com/playwright:jammy",
        "bash", "-lc", command,
    ]
    return _run(argv, cwd=PROJECT_DIR, env=os.environ.copy())

if __name__ == "__main__":
    app.run()
