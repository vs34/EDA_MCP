# Walkthrough: Modular Virtuoso MCP Tool Implementation

We have refactored the EDA_MCP server into a highly modular and maintainable architecture.

---

## 🏗️ Modular Architecture Overview

```
                                  ┌───────────────────────────┐
                                  │         server.py         │
                                  │ (FastMCP: remote_control, │
                                  │         virtuoso)         │
                                  └──────────────┬────────────┘
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                        ▼                                                 ▼
          ┌───────────────────────────┐                     ┌───────────────────────────┐
          │      remote_session       │                     │    virtuoso_client.py     │
          │(config_remote_control.json│                     │   (VirtuosoClient Class)  │
          │   isolated SSH session)   │                     └─────────────┬─────────────┘
          └───────────────────────────┘                                   │
                                                                          ▼
                                                            ┌───────────────────────────┐
                                                            │     virtuoso_session      │
                                                            │   (config_virtuoso.json   │
                                                            │   isolated SSH session)   │
                                                            └───────────────────────────┘
```

### 1. Low-Level SSH Transport Backbone ([ssh_client.py](file:///Users/vs/function/EDA_MCP/ssh_client.py))
Contains standard SSH primitives:
- `connect()`
- `execute_command(command: str)`
- `read_file(remote_path: str)`
- `write_file(remote_path: str, content: str)`
- `load_config()`: Automatically resolves tool-specific config files in [config/](file:///Users/vs/function/EDA_MCP/config) with fallback searching.

### 2. High-Level Virtuoso Client ([virtuoso_client.py](file:///Users/vs/function/EDA_MCP/virtuoso_client.py))
Encapsulates `VirtuosoClient` class bound to `virtuoso_session`:
- `initialize(work_dir)`: Navigates to working directory and starts Virtuoso.
- `run(skill_code, timeout)`: Pre-processes SKILL, writes to `MCP.command` FIFO, and polls `mcp_output.txt`.
- `exit()`: Gracefully exits Virtuoso via SKILL FIFO command.
- `_clean_skill_command()`: Strips line/inline `;;` comments and formats single line string.

### 3. FastMCP Server Entrypoint ([server.py](file:///Users/vs/function/EDA_MCP/server.py))
Instantiates isolated sessions:
```python
remote_session = RemoteSession(config_path="config/config_remote_control.json")
virtuoso_session = RemoteSession(config_path="config/config_virtuoso.json")
virtuoso_client = VirtuosoClient(session=virtuoso_session)
```
And registers two unified `@mcp.tool()` definitions:
1. `remote_control(action, command="", path="", content="")`: Dispatches `run_command`, `read_file`, and `write_file` actions on `remote_session`.
2. `virtuoso(action, command="", work_dir="~/Desktop/cmos65")`: Dispatches `initialize`, `run`, and `exit` actions on `virtuoso_session`.

---

## Verification
- `python3 -m py_compile ssh_client.py virtuoso_client.py server.py tests/test_mcp_client.py` executed cleanly with **0 syntax errors**.
