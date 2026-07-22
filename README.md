# EDA_MCP Server

A Model Context Protocol (MCP) server that bridges your local AI tools (like Claude Desktop, Cursor, etc.) to a remote EDA server over SSH. It automatically sources your shell setup script (e.g. `/cadance/cshrc`) inside a `csh` execution environment and enables command execution and file transfer via SFTP.

## Features

1. **Stateful Command Execution (`run_remote_command`)**: Runs terminal commands on the remote EDA server inside a `csh` session with the environment script sourced.
2. **File Reading (`read_remote_file`)**: Reads file contents directly from the remote server over SSH (ideal for loading large logs or reports).
3. **File Writing (`write_remote_file`)**: Writes or updates files on the remote server (great for creating Tcl/SKILL scripts for Innovus/Genus/Tempus/Virtuoso).
4. **Cadence Virtuoso Control (`virtuoso`)**: Initializes Virtuoso, sends SKILL commands via FIFO IPC with response polling, and handles graceful session termination.

---

## Installation & Setup

### 1. Install Dependencies
Make sure you have Python 3 and pip installed, then run:
```bash
pip3 install -r requirements.txt
```

### 2. Configure SSH Settings
Create a `config.json` file in the root of this project (see `config.json.template`):
```json
{
  "ssh_host": "eda-uni",
  "ssh_config_path": "~/.ssh/config",
  "env_setup_cmd": "source /cadance/cshrc"
}
```
*Note: Make sure your `~/.ssh/config` has the `eda-uni` host configured (with hostname, username, and key file).*

---

## Configuring with AI Clients

### Claude Desktop
Add the following configuration to your `claude_desktop_config.json` (typically located at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

### Cursor or Windsurf
Go to Settings -> MCP -> Add New MCP Server:
- **Name**: `EDA_MCP`
- **Type**: `stdio`
- **Command**: `python3 /Users/vs/function/EDA_MCP/server.py`

---

## API & Modular Structure

* `config.json`: Stores user-specific environment variables and server target.
* `ssh_client.py`: Low-level SSH transport backbone managing persistent `csh` shell sessions, command execution, and file I/O.
* `virtuoso_client.py`: High-level Cadence Virtuoso client encapsulating SKILL comment processing, FIFO pipe communication, output polling, and process lifecycle.
* `server.py`: Defines FastMCP tools (`run_remote_command`, `read_remote_file`, `write_remote_file`, `virtuoso`) exposed to AI clients.
