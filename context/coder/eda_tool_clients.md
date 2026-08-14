# EDA_TOOL_CLIENTS_SPEC

## 1. Cadence Virtuoso Client ([`virtuoso_client.py`](file:///Users/vs/function/EDA_MCP/virtuoso_client.py))

### Assisted Run FIFO Pipe IPC State Machine
```
   [Agent SKILL Code]
          │
          ▼
   _clean_skill_command() (Strips ';;' comments)
          │
          ▼
   rm -f mcp_output.txt && touch mcp_output.txt
          │
          ▼
   echo "<clean_skill>" > MCP.command (Writes to FIFO)
          │
          ▼
   Polling Loop (Interval: 0.3s, Timeout: 30.0s)
   read_file("mcp_output.txt") until "RESULT:" appears
```

### Standalone REPL Mode
- `start_standalone(work_dir)`: Sends `virtuoso -nograph` via `execute_interactive_stream()` matching `(>\s*$|\bCIW>\s*$)`.
- `run_standalone(command)`: Sends `_clean_skill_command(command)` via `execute_interactive_stream()`.
- `stop_standalone()`: Sends `exit()` to Virtuoso REPL stream.

---

## 2. Siemens Eldo Client ([`eldo_client.py`](file:///Users/vs/function/EDA_MCP/eldo_client.py))

### Interactive REPL Mode (`eldo -inter`)
- `start_interactive(netlist_file, work_dir)`: Sends `eldo <netlist_file> -inter` via `execute_interactive_stream()` matching `(eldo>\s*$|\bELDO>\s*$)`.
- `run_interactive(command)`: Sends REPL control command (`run`, `step`, `display`) via `execute_interactive_stream()`.
- `stop_interactive()`: Sends `quit` to Eldo REPL stream.

### Extracted Measurement Retrieval (`read_extract`)
- Auto-discovery command: `ls -t *.extract 2>/dev/null | head -n 1`
- Fetches newest file via `session.read_file(extract_file)`.
