# SERVER_AND_MCP_SPEC

## 1. Instance & Logging Setup ([`server.py`](../../server.py))
- **FastMCP Server**: `mcp = FastMCP("EDA_MCP")`
- **Log Location**: `logs/eda_mcp_<session_timestamp>_<pid>.log`
- **Log Handlers**:
  - `logging.FileHandler(log_filepath, encoding="utf-8")`
  - `logging.StreamHandler(sys.stderr)` (preserves stdout JSON-RPC stdio protocol)

---

## 2. Dedicated SSH Session Allocations

To prevent working directory (`cd`) or environment contamination across tools, [`server.py`](../../server.py#L54-L61) instantiates separate `RemoteSession` instances:

```python
remote_session = RemoteSession(config_path="config/config_remote_control.json")
virtuoso_session = RemoteSession(config_path="config/config_virtuoso.json")
virtuoso_interactive_session = RemoteSession(config_path="config/config_virtuoso.json")
eldo_session = RemoteSession(config_path="config/config_eldo.json")

virtuoso_client = VirtuosoClient(session=virtuoso_session)
virtuoso_standalone_client = VirtuosoClient(session=virtuoso_standalone_session)
eldo_client = EldoClient(session=eldo_session)
workboard_client = WorkBoardClient()
```

---

## 3. Tool Dispatch Table

| Tool Name | Action Argument | Target Method Invocation |
| :--- | :--- | :--- |
| `remote_control` | `"run_command"` | `remote_session.execute_command(command, timeout)` |
| `remote_control` | `"read_file"` | `remote_session.read_file(path, timeout)` |
| `remote_control` | `"write_file"` | `remote_session.write_file(path, content, timeout)` |
| `virtuoso` | `"initialize"` | `virtuoso_client.initialize(work_dir)` |
| `virtuoso` | `"assisted_run"` | `virtuoso_client.assisted_run(skill_code=command, timeout)` |
| `virtuoso` | `"start_standalone"` | `virtuoso_standalone_client.start_standalone(work_dir)` |
| `virtuoso` | `"standalone"` | `virtuoso_standalone_client.run_standalone(command, work_dir, timeout)` |
| `virtuoso` | `"stop_standalone"` | `virtuoso_standalone_client.stop_standalone()` |
| `virtuoso` | `"run_terminal_command"`| `virtuoso_client.run_terminal_command(command, work_dir, timeout)` |
| `virtuoso` | `"exit"` | `virtuoso_client.exit()` |
| `eldo` | `"initialize"` | `eldo_client.initialize(work_dir)` |
| `eldo` | `"start_interactive"` | `eldo_client.start_interactive(netlist_file=command, work_dir)` |
| `eldo` | `"run_interactive"` | `eldo_client.run_interactive(command, work_dir, timeout)` |
| `eldo` | `"stop_interactive"` | `eldo_client.stop_interactive(work_dir)` |
| `eldo` | `"run_script"` | `eldo_client.run_script(script_path=command, work_dir)` *(MISSING)* |
| `eldo` | `"read_extract"` | `eldo_client.read_extract(work_dir)` |
| `eldo` | `"run_terminal_command"`| `eldo_client.run_terminal_command(command, work_dir, timeout)` |
| `workboard` | `"initialize"` | `workboard_client.initialize(workboard_name)` |
| `workboard` | `"add"` | `workboard_client.add(remote_path, local_path, workboard_name, timeout)` |
| `workboard` | `"export"` | `workboard_client.export(local_path, remote_path, workboard_name, message, timeout)` |
| `workboard` | `"pull"` | `workboard_client.pull(local_path, workboard_name, timeout)` |
| `workboard` | `"push"` | `workboard_client.push(local_path, workboard_name, message, timeout)` |
| `workboard` | `"diff"` | `workboard_client.diff(local_path, workboard_name)` |
| `workboard` | `"status"` | `workboard_client.status(workboard_name)` |
| `workboard` | `"history"` | `workboard_client.history(local_path, workboard_name)` |
