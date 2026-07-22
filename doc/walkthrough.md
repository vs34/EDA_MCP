# Walkthrough: Modular Virtuoso MCP Tool Implementation

We have refactored the EDA_MCP server into a highly modular and maintainable architecture.

---

## 🏗️ Modular Architecture Overview

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

### 1. Low-Level SSH Transport Backbone ([ssh_client.py](file:///Users/vs/function/EDA_MCP/ssh_client.py))
Contains standard SSH primitives:
- `connect()`
- `execute_command(command: str)`
- `read_file(remote_path: str)`
- `write_file(remote_path: str, content: str)`

### 2. High-Level Tool Client ([virtuoso_client.py](file:///Users/vs/function/EDA_MCP/virtuoso_client.py))
Encapsulates `VirtuosoClient` class:
- `initialize(work_dir)`: Starts Virtuoso and captures PID.
- `run(skill_code, timeout)`: Pre-processes SKILL, writes to `MCP.command` FIFO, and polls `mcp_output.txt`.
- `exit()`: Gracefully exits Virtuoso via SKILL and PID check/kill.
- `_clean_skill_command()`: Strips line/inline `;;` comments and formats single line string.

### 3. FastMCP Server Entrypoint ([server.py](file:///Users/vs/function/EDA_MCP/server.py))
Instantiates:
```python
session = RemoteSession(config_path=config_path)
virtuoso_client = VirtuosoClient(session=session)
```
And registers `@mcp.tool()` `virtuoso(action, command="", work_dir="~/Desktop/cmos65")` delegating directly to `virtuoso_client`.

---

## Verification
- `python3 -m py_compile ssh_client.py virtuoso_client.py server.py tests/test_mcp_client.py` executed cleanly with **0 syntax errors**.
