# Walkthrough: Modular Virtuoso & Eldo MCP Tool Architecture

We have implemented a highly modular, state-isolated, and scalable architecture for the EDA_MCP server.

---

## 🏗️ Modular Architecture Overview

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

### 1. Low-Level SSH Transport Backbone ([ssh_client.py](../ssh_client.py))
Contains persistent SSH shellPrimitives:
- `connect()`
- `execute_command(command: str)`
- `read_file(remote_path: str)`
- `write_file(remote_path: str, content: str)`
- `load_config()`: Automatically resolves tool-specific config files in [config/](../config) with fallback searching.

### 2. Cadence Virtuoso Client ([virtuoso_client.py](../virtuoso_client.py))
Encapsulates `VirtuosoClient` class bound to `virtuoso_session`:
- `assisted_run(skill_code, work_dir, timeout)`: Auto-initializes working directory on demand, pre-processes SKILL, writes to `MCP.command` FIFO, and polls `mcp_output.txt`.
- `exit()`: Gracefully exits Virtuoso via SKILL FIFO command.

### 3. Siemens Eldo Client ([eldo_client.py](../eldo_client.py))
Encapsulates `EldoClient` class bound to `eldo_session`:
- `start_interactive(netlist_file, work_dir)`: Auto-initializes simulation working directory and spawns interactive Eldo (`eldo <netlist.cir> -inter`) REPL stream.
- `run_interactive(command)`: Checks PID status (`kill -0 <pid>`), sends commands into `interctive.fifo`, clears log, and reads output from `intective_out.txt`.
- `stop_interactive()`: Terminates background Eldo PID (`kill -9 <pid>`).
- `run_script(script_path)`: Executes batch Eldo simulation (`eldo <script_path> >& mcp_run.log`), auto-truncating output to `tail -100` if log exceeds 100 lines.
- `read_extract()`: Auto-detects and reads the latest `.extract` measurement summary file.

### 4. FastMCP Server Entrypoint ([server.py](../server.py))
Instantiates isolated sessions:
```python
remote_session = RemoteSession(config_path="config/config_remote_control.json")
virtuoso_session = RemoteSession(config_path="config/config_virtuoso.json")
eldo_session = RemoteSession(config_path="config/config_eldo.json")
```
And registers three unified `@mcp.tool()` definitions:
1. `remote_control(action, command="", path="", content="")`
2. `virtuoso(action, command="", work_dir="~/Desktop/cmos65")`
3. `eldo(action, command="", work_dir="~/Desktop/eldo")`

---

## Verification
- `python3 -m py_compile server.py ssh_client.py virtuoso_client.py eldo_client.py tests/test_eldo.py` executed cleanly with **0 syntax errors**.
