# MCP_TOOLS_SPECIFICATION

## Tool 1: `remote_control`
**Description**: Remote Linux shell execution and direct text file I/O.

### Interface Schema
```typescript
type RemoteControlArgs = {
  action: "run_command" | "run_remote_command" | "run" | "exec" | "execute"
        | "read_file" | "read_remote_file" | "read"
        | "write_file" | "write_remote_file" | "write";
  command?: string; // Required when action is command execution
  path?: string;    // Required for read_file / write_file
  content?: string; // Required for write_file
  timeout?: number; // Default: 60.0s
};
```

### Action Behavior & Return Formats
- `run_command`: Executes `command` in persistent `csh` session.
  - *Returns*: `Exit Status: <code>\n--- STDOUT ---\n<out>\n--- STDERR ---\n<err>`
- `read_file`: Reads text from `path`.
  - *Returns*: Text content string.
- `write_file`: Encodes `content` as Base64 and writes to `path`. Prefer WorkBoard for reviewable simulation artifacts; use direct write only when explicitly appropriate to the task.
  - *Returns*: `"Successfully wrote <bytes> bytes to remote file '<path>'."`

---

## Tool 2: `virtuoso`
**Description**: Cadence Virtuoso lifecycle management and SKILL code execution.

### Interface Schema
```typescript
type VirtuosoArgs = {
  action: "start_standalone" | "start"
        | "standalone" | "run_standalone"
        | "stop_standalone" | "stop"
        | "assisted_run" | "assisted" | "run"
        | "run_terminal_command" | "terminal" | "shell"
        | "exit";
  command?: string;  // SKILL code string or terminal shell command
  work_dir?: string; // Default: "~/Desktop/cmos65"
  timeout?: number;  // Default: 30.0s
};
```

### Action Modes
- `start_standalone`: Launches non-graphical Virtuoso REPL (`virtuoso -nograph`).
- `standalone`: Sends SKILL statement to active `virtuoso -nograph` REPL stream.
- `stop_standalone`: Sends `exit()` to non-graphical REPL and closes session.
- `assisted_run`: Sends SKILL code to GUI Virtuoso via FIFO pipe (`MCP.command`) and polls `mcp_output.txt`. **Formatting Guarantee**: The MCP server automatically strips comments (`;...`) and collapses newlines before piping to Virtuoso; standard multi-line SKILL blocks are supported natively. Do NOT write temporary `.il` files to disk. **GUI Window Display**: When asked to build or open a schematic/layout view in Virtuoso, use `geOpen(?lib ... ?cell ... ?view ...)` to display the window in the live Virtuoso GUI (do NOT call `dbClose(cv)`). **GUI Popups**: Modal popups can be dismissed programmatically (e.g., `hiFormDone(simSaveAllForm)`, `hiDBoxOK(simNetNoOp6)`).
- `run_terminal_command`: Executes shell command in Virtuoso terminal environment.

---

## Tool 3: `eldo`
**Description**: Siemens Eldo analog simulation control, measurement retrieval, and waveform visualization.

### Interface Schema
```typescript
type EldoArgs = {
  action: "start_interactive" | "start"
        | "run_interactive" | "interactive"
        | "stop_interactive" | "stop"
        | "run_script" | "script"
        | "visualize_waveforms" | "visualize" | "plot"
        | "run_terminal_command" | "terminal" | "shell";
  command?: string;   // Netlist path, REPL command ('run', 'step'), SPICE output file path, or shell command
  file_path?: string; // Simulation output file path (.raw or .spi3) when action='visualize_waveforms'
  layout?: Array<{ pane_title: string; signals: string[] }>; // Signal layout config when action='visualize_waveforms'
  work_dir?: string;  // Default: "~/Desktop/eldo"
  timeout?: number;   // Default: 30.0s
};
```

### Action Modes
- `start_interactive`: Launches `eldo <netlist> -inter` interactive session.
- `run_interactive`: Sends simulation control command (`run`, `step`, `display`) to `eldo>` REPL.
- `stop_interactive`: Sends `quit` to active Eldo REPL session.
- `run_script`: Runs batch simulation deck.
- `visualize_waveforms` / `visualize` / `plot`: Spawns a multi-pane oscilloscope window to plot SPICE transient simulation outputs (`.raw` or `.spi3` files) using custom pane layout configurations.
- `run_terminal_command`: Executes shell command in Eldo terminal environment.

---

## Tool 4: `workboard`
**Description**: Git-backed local-remote workspace synchronization and version control.

### Interface Schema
```typescript
type WorkBoardArgs = {
  action: "initialize" | "add" | "export" | "pull" | "push" | "diff" | "status" | "history";
  workboard_name?: string; // Default: "default"
  remote_path?: string;    // Required for add/export
  local_path?: string;     // Relative local path in ./workboard/<name>/
  message?: string;        // Commit message for export/push (Default: "Agent sync")
  overwrite?: boolean;     // Default: false (protects existing remote file on export)
  timeout?: number;        // Default: 60.0s
};
```

### Action Modes & Auto-Advance Behavior
- `initialize`: Creates `./workboard/<name>/` and runs `git init`.
- `add`: Downloads remote file via SCP, registers in `.workboard.json`, commits locally ($C_{\text{sync}} = \text{HEAD}$).
- `pull`: Re-fetches remote file, updates local WorkBoard, commits locally ($C_{\text{sync}} = \text{HEAD}$).
- `push`: Uploads local edits to remote server via SCP, commits locally ($C_{\text{sync}} = \text{HEAD}$).
- `diff`: Fetches remote bytes and compares with local file.
  - *If identical*: Updates `.workboard.json` sync baseline SHA to current local Git HEAD.
  - *If different*: Returns unified line-by-line diff.
- `status`: Returns tracked file table, sync baseline commit SHAs, and local git status.
- `history`: Returns local Git commit log (`git log`).

---

## Tool 5: `report_issue`
**Description**: Autonomous agent-to-agent GitHub issue & feature request reporting tool.

### Interface Schema
```typescript
type ReportIssueArgs = {
  title: string;           // Concise issue or feature request title
  body?: string;           // Freeform Markdown content (see issue_reporting_guide.md for suggestions)
  label?: string;          // Default: "bug" (e.g., "enhancement", "feature-request")
  agent_model?: string;    // Model identifier (e.g. "gemini-3.6-flash", "claude-3-5-sonnet")
  session_id?: string;     // Default: "unknown" (conversation turn ID)
};
```

### Auto-Behavior
- **Client Agent Auto-Detection**: Extracts `agent_name` (`Antigravity`, `claude-code`, `cursor`) from MCP `clientInfo` context via FastMCP `Context`.
- **Log Auto-Attachment**: Automatically references the active server log in `logs/eda_mcp_*.log`.
- **GitHub Label Auto-Creation**: Checks repository via `gh label list` and creates agent label (`gh label create`) if missing.
- **Form Suggestions**: For suggested Markdown body structure on bugs and enhancements, see [`issue_reporting_guide.md`](issue_reporting_guide.md).
