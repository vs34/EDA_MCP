# Implementation Plan: Basic EDA SSH Bridge MCP Server

Build a basic Python-based Model Context Protocol (MCP) server that acts as a bridge between the local AI client and the remote EDA server. The server will initialize an SSH pipeline, source the remote shell configuration (e.g., `~/.cshrc`), and expose basic command execution and file management tools.

## User Review Required

> [!IMPORTANT]
> **SSH Credentials Configuration**
> You will need to provide your SSH connection details (Host, Username, Key Path or Password) and the path to the startup shell script (e.g., `~/.cshrc` or `~/.bashrc`) in a local `config.json` or `.env` file before launching.
>
> **Interactive CSHRC Sourcing**
> Sourcing `.cshrc` or `.bashrc` remotely over non-interactive SSH shells can sometimes skip environment setup if the script checks for interactive shells (`$-` or `$prompt`). We will configure the SSH client to allocate a pseudo-terminal (PTY) or prepend the sourcing command directly to all command execution runs to ensure environment settings are loaded.

## Open Questions

None for the basic version. We will implement support for both SSH keys and passwords, and allow configuring the shell initialization command.

## Proposed Changes

We will create a lightweight Python application using the official Python MCP SDK with `FastMCP`.

---

### Component: SSH Client
Manages a persistent connection to the remote EDA server, handles PTY allocation, sources the environment startup file, and performs SFTP file operations.

#### [NEW] [ssh_client.py](file:///Users/vs/function/EDA_MCP/ssh_client.py)
- Implements `RemoteSession` class.
- Establishes connection using Paramiko.
- Implements command execution that automatically prepends shell initialization (e.g. `source ~/.cshrc && <command>`).
- Implements SFTP-based file reading and writing.

---

### Component: MCP Server Interface
Exposes the core bridge tools using FastMCP with dedicated per-tool SSH sessions and config files in `config/`.

#### [MODIFY] [server.py](file:///Users/vs/function/EDA_MCP/server.py)
- Initializes `FastMCP("EDA_MCP")`.
- Creates dedicated SSH sessions:
  - `remote_session`: Isolated session for `remote_control` using `config/config_remote_control.json`.
  - `virtuoso_session`: Isolated session for `virtuoso` using `config/config_virtuoso.json`.
- Exposes tools:
  - `remote_control(action, command="", path="", content="")`: Remote shell command execution (`action='run_command'`), file reading (`action='read_file'`), and file writing (`action='write_file'`).
  - `virtuoso(action, command="", work_dir="~/Desktop/cmos65")`: Cadence Virtuoso initialization (`action='initialize'`), SKILL execution (`action='run'`), and session termination (`action='exit'`).

---

### Component: Configuration & Dependency Management
Handles packages and tool-specific configuration files.

#### [NEW] [config/](file:///Users/vs/function/EDA_MCP/config)
- `config/config_remote_control.json` & `config/config_remote_control.json.template`: Dedicated configuration for `remote_control`.
- `config/config_virtuoso.json` & `config/config_virtuoso.json.template`: Dedicated configuration for `virtuoso`.
- `config/config.json.template`: Fallback configuration template.

#### [MODIFY] [README.md](file:///Users/vs/function/EDA_MCP/README.md)
- Explains tool-specific configurations in `config/`, tool signatures (`remote_control`, `virtuoso`), and AI client connection instructions.

---

## Verification Plan

### Manual Verification
1. Create a `config.json` with actual SSH details.
2. Run the MCP server locally using `mcp run server.py`.
3. Call `run_command` with commands like `whoami`, `echo $PATH`, and Cadence tool version checks (`genus -version` or `innovus -version`) to verify the environment sourced correctly.
4. Call `write_file` and `read_file` to verify SFTP operations.
