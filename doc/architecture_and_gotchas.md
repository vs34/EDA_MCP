# EDA_MCP Architecture, Design Patterns & Gotchas Guide

This document captures key technical findings, architecture details, and critical gotchas for developers or AI agents extending this repository.

---

## 🏗️ 1. Core Architecture

```
                                  ┌───────────────────────────┐
                                  │         server.py         │
                                  │ (FastMCP: remote_control, │
                                  │      virtuoso, eldo)      │
                                  └──────────────┬────────────┘
                                                 │
          ┌──────────────────────────────────────┼──────────────────────────────────────┐
          ▼                                      ▼                                      ▼
┌───────────────────────────┐          ┌───────────────────────────┐          ┌───────────────────────────┐
│      remote_session       │          │    virtuoso_client.py     │          │      eldo_client.py       │
│(config_remote_control.json│          │   (VirtuosoClient Class)  │          │    (EldoClient Class)     │
│   isolated SSH session)   │          └─────────────┬─────────────┘          └─────────────┬─────────────┘
└───────────────────────────┘                        │                                      │
                                                     ▼                                      ▼
                                       ┌───────────────────────────┐          ┌───────────────────────────┐
                                       │     virtuoso_session      │          │       eldo_session        │
                                       │   (config_virtuoso.json   │          │    (config_eldo.json      │
                                       │   isolated SSH session)   │          │   isolated SSH session)   │
                                       └───────────────────────────┘          └───────────────────────────┘
```

- **[server.py](file:///Users/vs/function/EDA_MCP/server.py)**: Exposes `@mcp.tool()` definitions (`remote_control`, `virtuoso`, `eldo`) to MCP clients. Instantiates distinct, isolated `RemoteSession` instances for each tool. Handles per-instance logging in `temp/`.
- **[config/](file:///Users/vs/function/EDA_MCP/config)**: Holds tool-specific JSON configuration files (`config_remote_control.json`, `config_virtuoso.json`, `config_eldo.json`). `RemoteSession.load_config()` automatically resolves tool-specific configs with a fallback to `config.json`.
- **[virtuoso_client.py](file:///Users/vs/function/EDA_MCP/virtuoso_client.py)**: High-level Cadence Virtuoso client encapsulating SKILL command cleaning, FIFO pipe communication, response polling, and Virtuoso process lifecycle.
- **[eldo_client.py](file:///Users/vs/function/EDA_MCP/eldo_client.py)**: High-level Siemens/Mentor Graphics Eldo simulation client managing FIFO pipe IPC for interactive simulation, PID health monitoring (`kill -0`), batch simulation output redirection, and `.extract` result reading.
- **[ssh_client.py](file:///Users/vs/function/EDA_MCP/ssh_client.py)**: Low-level transport layer managing persistent, stateful `csh` shell sessions over SSH (`RemoteSession`).

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
- Environment scripts (`/cadence/cshrc` or `/mentor2020/ams.cshrc`) are sourced **once** on startup.
- Sentinels (`__CMD_FINISHED_[random_hex]__`) are printed with `$status` to detect command completion and exit codes without closing the shell.
- `stderr` is merged into `stdout` (`stderr=subprocess.STDOUT`) to prevent pipe buffer deadlocks.

### 3. FastMCP Tool Return Type Contract
- All FastMCP tools annotated with `-> str` **must explicitly return a valid string**.
- Returning `None` (or omitting `return` in python) causes the FastMCP stdio transport layer to hang or crash serialization.

---

## 🔌 3. Eldo Interactive FIFO IPC Architecture

```
[eldo_client.py]
        │
        │ 1. `tail -f /dev/null > interctive.fifo &` (Keeps FIFO pipe open perpetually)
        │ 2. `eldo i.cir -inter < interctive.fifo >& intective_out.txt &`
        │ 3. Stores `self.interactive_pid`
        ▼
   interctive.fifo (Named Pipe on remote server)
        │
        │ `echo "<command>" > interctive.fifo`
        ▼
   Siemens Eldo Interactive Process (PID tracked)
        │
        │ Redirects stdout & stderr
        ▼
   intective_out.txt  ==> Read by eldo_client.py via read_file
```

- **Pipe Keeper**: In Unix/Linux, a FIFO pipe closes when the writing process finishes. To prevent Eldo from receiving `EOF` and exiting when an `echo` completes, `tail -f /dev/null > interctive.fifo &` runs in the background to hold a permanent write handle on `interctive.fifo`.
- **PID Health Tracking**: `is_interactive_running()` executes `kill -0 <pid> 2>/dev/null` prior to sending commands. If the PID is dead, the tool safely prompts the agent for the `.cir` netlist name.
- **Output Clearing**: `cp /dev/null intective_out.txt` is run before sending a command so the output file contains only fresh results.

---

## 🔌 4. Virtuoso IPC Pipe Architecture

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

---

## 📜 5. Logging & Debugging

- **Session Activity Logs**: Saved automatically to `temp/eda_mcp_YYYYMMDD_HHMMSS_<PID>.log`.
- **Git Ignore**: The `temp/` folder is ignored by git (`.gitignore`).
- **Log Contents**: Logs contain timestamped records of every tool call (`[TOOL CALL]`), parameters, duration, and exit status (`[TOOL RESULT]`).
