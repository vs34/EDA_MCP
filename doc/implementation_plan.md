# Implementation Plan: EDA MCP Server

Build a Python-based Model Context Protocol (MCP) server that runs locally and connects to a remote Electronic Design Automation (EDA) server via SSH. The MCP server will expose tools to execute EDA commands (specifically targeting Cadence tools like Innovus, Genus, Tempus, Jasper, etc.) synchronously or asynchronously, read/write configuration and Tcl scripts, manage remote files, and check job status.

## User Review Required

> [!IMPORTANT]
> **SSH Authentication Configuration**
> By default, the server will read connection credentials from a local `.env` file or `config.json` file in the repository. Please ensure you configure this before running the MCP server.
>
> **Background Job Management**
> Since synthesis, place & route, and timing signoff can take hours, the server will run long tasks in the background using remote system utilities (like `nohup` or `screen` or shell background execution) and return a job identifier (Process ID). The LLM can monitor these jobs via a status checking tool.

## Open Questions

> [!WARNING]
> 1. **Cadence Tool Environment Setup**: Do your remote EDA tools require sourcing a specific environment setup script (e.g., `source /cadence/setup.sh` or setting `PATH`/`LM_LICENSE_FILE`) before running? We can add a configuration setting `env_setup_cmd` in `config.json` to prepend this configuration to every command execution.
> 2. **Authentication Method**: Do you prefer using SSH keys (recommended) or passwords? We will support both, but we want to confirm if your SSH keys are password-protected (which would require a passphrase).

## Proposed Changes

We will create a lightweight Python application using the official Python MCP SDK with `FastMCP`.

---

### Component: SSH Client & Execution Engine
Wraps Paramiko to manage connection persistence, SFTP for file read/write operations, and command execution (both synchronous and background).

#### [NEW] [ssh_client.py](file:///Users/vs/function/EDA_MCP/ssh_client.py)
- Implements `RemoteSession` class.
- Handles connection/reconnection to the remote SSH server.
- Supports SFTP operations: `read_file`, `write_file`, `list_dir`.
- Supports executing commands synchronously with timeout.
- Supports launching commands in the background and returning the PID (e.g., using `nohup <cmd> > <logfile> 2>&1 & echo $!`).

---

### Component: MCP Server Interface
Exposes the tools to the Model Context Protocol using FastMCP.

#### [NEW] [server.py](file:///Users/vs/function/EDA_MCP/server.py)
- Initializes `FastMCP("EDA-MCP-Server")`.
- Exposes tools:
  - `run_ssh_command(command)`: Execute low-level SSH commands.
  - `list_remote_dir(path)`: List directory contents on the remote server.
  - `read_remote_file(path)`: View contents of logs or reports on the remote server.
  - `write_remote_file(path, content)`: Upload scripts or configuration files.
  - `run_genus(script_path, run_in_background, log_path)`: Run Cadence Genus.
  - `run_innovus(script_path, run_in_background, log_path)`: Run Cadence Innovus.
  - `run_tempus(script_path, run_in_background, log_path)`: Run Cadence Tempus.
  - `run_jasper(script_path, run_in_background, log_path)`: Run Cadence Jasper.
  - `check_job_status(pid)`: Check status of background processes.
- Exposes resources:
  - `remote://file/path`: Access files dynamically as resources.
- Exposes prompts:
  - Templates for typical Cadence tasks (e.g., standard synthesis script templates, floorplanning templates).

---

### Component: Configuration & Dependency Management
Handles packages and configuration options.

#### [NEW] [requirements.txt](file:///Users/vs/function/EDA_MCP/requirements.txt)
- Declares dependencies: `mcp`, `paramiko`, `python-dotenv`.

#### [NEW] [config.json.template](file:///Users/vs/function/EDA_MCP/config.json.template)
- Template for configuring the SSH connection and remote environment settings.

#### [MODIFY] [README.md](file:///Users/vs/function/EDA_MCP/README.md)
- Documents instructions to configure and run the MCP server with Claude Desktop or other client editors.

---

## Verification Plan

### Automated Tests
 We can create a mock SSH testing script to verify the connection logic locally before running against the remote server:
- Run `python -m unittest tests/test_ssh.py` (we will place scratch tests in the scratch directory).

### Manual Verification
1. Create a local `.env` or `config.json` with test SSH connection details (e.g. local loopback or a staging server).
2. Start the server using:
   ```bash
   mcp run server.py
   ```
3. Test remote operations:
   - Run low-level remote commands (`whoami`, `hostname`, `ls`).
   - Read and write files.
   - Run a mock background job and check its status.
