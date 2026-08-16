# CODER_CONTEXT_SPEC (Python MCP Server Implementation)

## Component Map & File References

| Component | Source File | Class / Function | Description |
| :--- | :--- | :--- | :--- |
| **MCP Entrypoint** | [`server.py`](file:///Users/vs/function/EDA_MCP/server.py) | `FastMCP("EDA_MCP")` | Registers 4 MCP tools, initializes per-tool SSH sessions, configures logger (`logs/eda_mcp_*.log`). |
| **SSH Transport** | [`ssh_client.py`](file:///Users/vs/function/EDA_MCP/ssh_client.py) | `RemoteSession` | Manages persistent `csh` subshell over SSH, sentinel execution (`_read_until_sentinel`), and interactive stream reading (`execute_interactive_stream`). |
| **SCP Transport** | [`scp_client.py`](file:///Users/vs/function/EDA_MCP/scp_client.py) | `SCPClient` | Executes OpenSSH `scp -O` for direct binary/folder transfer without shell escaping overhead. |
| **Virtuoso Interface** | [`virtuoso_client.py`](file:///Users/vs/function/EDA_MCP/virtuoso_client.py) | `VirtuosoClient` | Manages SKILL FIFO pipe (`MCP.command`) IPC polling (`mcp_output.txt`) and `virtuoso -nograph` REPL streaming. |
| **Eldo Interface** | [`eldo_client.py`](file:///Users/vs/function/EDA_MCP/eldo_client.py) | `EldoClient` | Manages `eldo -inter` REPL streaming and `.extract` measurement summary parsing. |
| **WorkBoard Engine** | [`workboard_client.py`](file:///Users/vs/function/EDA_MCP/workboard_client.py) | `WorkBoardClient` | Manages `./workboard/<name>/` local Git repositories, `.workboard.json` manifests, SHA-256 checksums, and unified diffs. |

---

## Coder Context Index

- [`server_and_mcp.md`](file:///Users/vs/function/EDA_MCP/context/coder/server_and_mcp.md): FastMCP tool signatures, tool action dispatching, session isolation logic.
- [`transport_layer.md`](file:///Users/vs/function/EDA_MCP/context/coder/transport_layer.md): Subshell IO pipes, sentinel token format, regex prompt match loop, SCP command generation.
- [`eda_tool_clients.md`](file:///Users/vs/function/EDA_MCP/context/coder/eda_tool_clients.md): FIFO pipe write/read contract, REPL interactive streaming state machine.
- [`workboard_backend.md`](file:///Users/vs/function/EDA_MCP/context/coder/workboard_backend.md): `.workboard.json` schema, Git subprocess wrapper (`_git_cmd`), `diff` auto-advance algorithm.
- [`known_issues_and_maintenance.md`](file:///Users/vs/function/EDA_MCP/context/coder/known_issues_and_maintenance.md): Bug audit list (missing `run_script`), test discovery commands.
