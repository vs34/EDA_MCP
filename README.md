# EDA_MCP Server

A Model Context Protocol (MCP) server that bridges your local AI tools (like Claude Desktop, Cursor, Windsurf) to a remote EDA server over SSH. It automatically sources your CAD shell setup scripts (e.g. `/cadence/cshrc` or `/mentor2020/ams.cshrc`) inside persistent `csh` execution environments and enables remote shell control, Cadence Virtuoso SKILL execution, and Siemens Eldo simulation control.

---

## 🚀 Key Features & Tools

### 1. Remote Control (`remote_control`)
Unified remote shell execution and file management interface supporting:
- **`action='run_command'`**: Stateful terminal command execution inside a sourced `csh` session.
- **`action='read_file'`**: Reads file contents directly from the remote server.
- **`action='write_file'`**: Creates or updates remote files (e.g. Tcl/SKILL scripts).

### 2. Cadence Virtuoso Control (`virtuoso`)
Full Cadence Virtuoso lifecycle and SKILL command execution:
- **`action='initialize'`**: Navigates to project workspace (`~/Desktop/cmos65`) and launches Virtuoso in the background (`virtuoso &`).
- **`action='run'`**: Sends SKILL commands into Virtuoso via non-blocking FIFO pipe IPC (`MCP.command`) and polls `mcp_output.txt` for execution results.
- **`action='exit'`**: Gracefully terminates Virtuoso using SKILL `exit()` and process SIGTERM/SIGKILL fallback.

### 3. Siemens Eldo Control (`eldo`)
Full Siemens/Mentor Graphics Eldo analog simulation control (`source /mentor2020/ams.cshrc`):
- **`action='initialize'`**: Sets up project directory (defaults to `~/Desktop/eldo`), creates FIFO pipe (`interctive.fifo`), and output log (`intective_out.txt`).
- **`action='start_interactive'`**: Spawns a persistent background Eldo interactive process (`eldo <netlist.cir> -inter < interctive.fifo >& intective_out.txt &`) with PID tracking.
- **`action='run_interactive'`**: Checks PID status; sends commands into `interctive.fifo` and returns output from `intective_out.txt`. Prompts for `.cir` netlist if no interactive session is active.
- **`action='stop_interactive'`**: Stops the background interactive Eldo process (`kill -9 <pid>`).
- **`action='run_script'`**: Runs batch Eldo simulation (`eldo <script.cir> >& mcp_run.log`), returning execution status and log content (auto-truncating to `tail -100` if log exceeds 100 lines).
- **`action='read_extract'`**: Auto-detects and reads the latest `.extract` measurement summary file.

---

## 🛠️ Installation & Setup

### 1. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Configuration (`config/`)
Tool-specific configuration files reside in the `config/` directory (see `config/*.json.template`):
- `config/config_remote_control.json`: Setup for `remote_control` tool.
- `config/config_virtuoso.json`: Setup for `virtuoso` tool.
- `config/config_eldo.json`: Setup for `eldo` tool (`env_setup_cmd`: `"source /mentor2020/ams.cshrc"`).

Example configuration (`config/config_eldo.json`):
```json
{
  "ssh_host": "eda-uni",
  "ssh_config_path": "~/.ssh/config",
  "env_setup_cmd": "source /mentor2020/ams.cshrc"
}
```

---

## 🔌 Configuring with AI Clients

### Claude Desktop
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "eda-mcp": {
      "command": "python3",
      "args": [
        "/Users/vs/function/EDA_MCP/server.py"
      ]
    }
  }
}
```

### Cursor / Windsurf
Add a new Stdio MCP Server:
- **Name**: `EDA_MCP`
- **Command**: `python3 /Users/vs/function/EDA_MCP/server.py`

---

## 🏗️ Architecture & Modules

* `config/`: Stores tool-specific JSON configs (`config_remote_control.json`, `config_virtuoso.json`, `config_eldo.json`).
* `ssh_client.py`: Low-level SSH transport backbone managing persistent `csh` shell sessions and process sentinels.
* `virtuoso_client.py`: High-level Cadence Virtuoso client encapsulating SKILL IPC pipe communication and response polling.
* `eldo_client.py`: High-level Siemens Eldo simulation client with interactive FIFO pipe IPC, PID health checks, batch execution, and `.extract` reading.
* `server.py`: FastMCP server registering `@mcp.tool()` definitions (`remote_control`, `virtuoso`, `eldo`).
