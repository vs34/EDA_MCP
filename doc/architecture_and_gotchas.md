# EDA_MCP Architecture, Design Patterns & Gotchas Guide

This document captures key technical findings, architecture details, and critical gotchas for developers or AI agents extending this repository.

---

## 🏗️ 1. Core Architecture

```
                          ┌───────────────────────────┐
                          │         server.py         │
                          │   (FastMCP Tool Definitions)│
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │    virtuoso_client.py     │
                          │   (VirtuosoClient Class)  │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │       ssh_client.py       │
                          │   (RemoteSession Backbone)│
                          └───────────────────────────┘
```

- **[server.py](file:///Users/vs/function/EDA_MCP/server.py)**: Exposes `@mcp.tool()` definitions to MCP clients (Cursor, Claude Desktop, Antigravity CLI). Handles per-instance logging in `temp/`.
- **[virtuoso_client.py](file:///Users/vs/function/EDA_MCP/virtuoso_client.py)**: High-level client encapsulating SKILL command cleaning, FIFO pipe communication, response polling, and Virtuoso lifecycle.
- **[ssh_client.py](file:///Users/vs/function/EDA_MCP/ssh_client.py)**: Low-level transport layer managing a persistent, stateful `csh` shell session over SSH (`RemoteSession`).

---

## ⚠️ 2. Critical Gotchas & Execution Rules

### 1. `csh` Shell & Tilde Expansion Quoting (CRITICAL)
- **Problem**: In `csh`, passing single-quoted tilde paths like `'~/Desktop/cmos65'` to `cd` **disables shell tilde expansion**.
- **Symptom**: `csh` searches for a literal directory named `'~/Desktop/cmos65'` and **hangs indefinitely waiting for input**, causing 3-minute MCP timeouts.
- **Rule**: Always format tilde paths starting with `~` as `$HOME` before passing to `csh` commands:
  ```python
  safe_dir = f"$HOME{path[1:]}" if path.startswith("~") else shlex.quote(path)
  cmd = f"cd {safe_dir}"
  ```

### 2. Persistent Shell Session & Sentinel Protocol
- `RemoteSession` in `ssh_client.py` uses a single long-running `csh` subprocess over SSH (`subprocess.Popen(['ssh', '-o', 'BatchMode=yes', host, 'csh'])`).
- Environment scripts (`/cadence/cshrc` or `.cshrc_cmos065`) are sourced **once** on startup.
- Sentinels (`__CMD_FINISHED_[random_hex]__`) are printed with `$status` to detect command completion and exit codes without closing the shell.
- `stderr` is merged into `stdout` (`stderr=subprocess.STDOUT`) to prevent pipe buffer deadlocks.

### 3. FastMCP Tool Return Type Contract
- All FastMCP tools annotated with `-> str` **must explicitly return a valid string**.
- Returning `None` (or omitting `return` in python) causes the FastMCP stdio transport layer to hang or crash serialization.

---

## 🔌 3. Virtuoso IPC Pipe Architecture

```
[virtuoso_client.py]
        │
        │ Writes SKILL to FIFO
        ▼
   MCP.command (FIFO Pipe on remote server)
        │
        │ Read by Python IPC socket
        ▼
   MCP_sockit.py
        │
        │ stdout piped to Virtuoso CIW (ipcBeginProcess)
        ▼
   Cadence Virtuoso (evalstring)
        │
        │ Redirects result
        ▼
   mcp_output.txt  ==> Read by virtuoso_client.py
```

- **[MCP_initalize.sh](file:///Users/vs/function/EDA_MCP/server_side/virtuoso/MCP_initalize.sh)**: Creates FIFO pipe `MCP.command`, sources `.cshrc_cmos065`, sets `DISPLAY=:0`, and launches Virtuoso.
- **[MCP_setup.il](file:///Users/vs/function/EDA_MCP/server_side/virtuoso/MCP_setup.il)**: Loaded via `.cdsinit` on Virtuoso launch. Uses `ipcBeginProcess` to start `MCP_sockit.py`.
- **[MCP_sockit.py](file:///Users/vs/function/EDA_MCP/server_side/virtuoso/MCP_sockit.py)**: Opens `MCP.command` in `r+` mode (keeping the pipe open permanently across writes) and streams lines to Virtuoso's `stdout` evaluation loop.
- **Process PID Tracking**: Cadence Virtuoso binary runs as a 64-bit process (`/usr/local/cmos065_536/.../bin/64bit/virtuoso`). Use `pgrep -u $USER -f virtuoso` with the `-f` flag to capture the actual binary PID rather than short-lived launcher script PIDs.

---

## 📜 4. Logging & Debugging

- **Session Activity Logs**: Saved automatically to `temp/eda_mcp_YYYYMMDD_HHMMSS_<PID>.log`.
- **Git Ignore**: The `temp/` folder is ignored by git (`.gitignore`).
- **Log Contents**: Logs contain timestamped records of every tool call (`[TOOL CALL]`), parameters, duration, and exit status (`[TOOL RESULT]`).
