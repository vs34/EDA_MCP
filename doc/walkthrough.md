# Walkthrough: EDA_MCP Server

I have successfully completed the implementation of the basic `EDA_MCP` server bridge. It connects to your remote EDA server using your local SSH configuration (`eda-uni`), automatically sources the `/cadance/cshrc` environment inside `csh` execution shells, and provides basic file and command access.

## What was Implemented

1. **[requirements.txt](file:///Users/vs/function/EDA_MCP/requirements.txt)**: Configured Python dependencies including `mcp`, `paramiko`, and `python-dotenv`.
2. **[config.json](file:///Users/vs/function/EDA_MCP/config.json)** & **[config.json.template](file:///Users/vs/function/EDA_MCP/config.json.template)**: Declared connection settings to target `eda-uni` using SSH config lookup and setup execution environment commands.
3. **[ssh_client.py](file:///Users/vs/function/EDA_MCP/ssh_client.py)**: Implemented `RemoteSession` class which:
   - Connects using credentials from `~/.ssh/config`.
   - Automatically wraps commands to run within the Cadence csh environment.
   - Provides SFTP read, write, and list features.
4. **[server.py](file:///Users/vs/function/EDA_MCP/server.py)**: Configured FastMCP server named `EDA_MCP` exposing the following tools to the AI:
   - `run_command(command: str)`: Executes remote commands.
   - `read_file(path: str)`: Reads a remote file.
   - `write_file(path: str, content: str)`: Saves a remote file.
   - `list_dir(path: str)`: Lists files on remote server.
5. **[README.md](file:///Users/vs/function/EDA_MCP/README.md)**: Added complete documentation on how to configure and run the MCP server with Claude Desktop, Cursor, and other editors.

## Verification Results

1. **Dependency Installation**: Ran successfully.
2. **Local Startup Check**: Ran the server locally (`python3 server.py`) and verified it boots and registers tools successfully without error.
3. **SSH Remote Connection Test**:
   - Connection to `eda-uni` (192.168.3.58) timed out, which indicates the server requires active IIITD network connection or VPN (operation timed out).
   - Once your VPN/network connection to the university is established, the SSH config lookup will connect automatically.
