# DESIGNER_CONTEXT_SPEC (Chip Design AI Agent System Instruction)

## Repository & Client Binding
- **GitHub Repository**: [`https://github.com/vs34/EDA_MCP.git`](https://github.com/vs34/EDA_MCP.git)
- **Protocol**: Model Context Protocol (FastMCP Stdio)
- **Entrypoint**: [`server.py`](../../server.py)

```json
{
  "mcpServers": {
    "eda-mcp": {
      "command": "python3",
      "args": ["server.py"]
    }
  }
}
```

---

## Agent Operational Invariants (Suggestion)

1. **LIBRARY_SCOPE**: All generated cellviews, schematics, testbenches, and layouts MUST reside in library `MCP` unless explicitly overridden.
2. **SESSION_ISOLATION**:
   - Virtuoso shell commands -> `virtuoso(action="run_terminal_command")`
   - Eldo shell commands -> `eldo(action="run_terminal_command")`
   - File I/O & raw remote shell -> `remote_control`
   - DO NOT use `remote_control` for Virtuoso/Eldo tool shell commands (does not share working directory or environment).
3. **FILE_IO_RULE**: DO NOT write files directly to the remote server using shell commands (`printf`, `echo`, `cat <<EOF`, `touch`). File creation and file transfers on the remote server MUST use dedicated tool actions `workboard` or programmatically export files to the target location via tool workflows.
4. **SCHEMATIC_CHECK_POLICY**: Zero-tolerance for `schCheck` warnings. Floating gates or unattached pins must be fixed before saving or netlisting.
5. **STREAM_FLUSH_RULE**: Every SKILL file stream (`outfile`) MUST execute `drain(fileId)` before `close(fileId)`.
6. **ELDO_TITLE_RULE**: Line 1 of any `.cir` netlist is strictly treated by Eldo as a title comment line.
7. **LOCAL_COMPUTATION_RULE**: Agents are fully authorized and encouraged to use local default capabilities, Python scripts, mathematical calculators, scratch scripts, and web research to perform transistor sizing ($W/L$), bias point calculations, schematic planning, and netlist formatting prior to remote execution.
8. **ASSISTED_RUN_LENGTH_RULE**: For `virtuoso(action="assisted_run")`, the SKILL code in `command` MUST NOT be excessively long. Keep commands concise and modular for `assisted_run`. For complex/long SKILL scripts, Break long SKILL to small portion according to complexity this will also increase debuggability if anything went wrong.
9. **GUI_POPUP_NOTIFY_RULE**: In `virtuoso(action="assisted_run")`, commands may trigger modal GUI popups on the remote Virtuoso window (e.g., save prompts, geOpen dialogs, schCheck confirmations). If `assisted_run` times out or requires GUI input, the agent MUST explicitly notify the user to inspect and interact with the remote Virtuoso GUI popup.
10. **ISSUE_REPORTING_GUIDELINE**: When encountering bugs or identifying new tool enhancements, agents are encouraged to use `report_issue` with structured Markdown (see [`issue_reporting_guide.md`](issue_reporting_guide.md) for suggestions on bug & enhancement reports).
11. **GUI_WINDOW_OPEN_RULE**: In `virtuoso(action="assisted_run")`, when requested to build, edit, or open a schematic or layout for the user to view in Virtuoso, the SKILL script MUST check if a window is already open using `unless(geGetCellViewWindow(cv) geOpen(?lib ... ?cell ... ?view ...))` to prevent duplicate window spawns (`window:3`, `window:4`), and MUST NOT call `dbClose(cv)` (which would purge the view).
12. **ELDO_SIMULATION_WORKFLOW_RULE**: Agents MUST NOT hand-write SPICE transistor netlists by hand. Export structural netlist directly from Virtuoso schematic (`MCP` library) to `~/Desktop/eldo/<cellName>.net`. For Mode 1 (`run_interactive`), stream commands to REPL. For Mode 2 (`run_script`), write `<cellName>.cir` configuration deck locally, export to server via WorkBoard (`workboard`), run simulation, and download output files (`.chi`, `.extract`) to local workspace using `workboard` for local bug analysis and reporting.
13. **WORKBOARD_LOCAL_REVIEW_RULE**: Agents are strongly encouraged and expected to use WorkBoard (`workboard`) to download exported Virtuoso netlists (`<cellName>.net`) from the server to the local workspace, and create/edit all Eldo simulation decks (`<cellName>.cir`) and auxiliary scripts LOCALLY first before syncing them to the server (`workboard`). This local-first workflow ensures full transparency so the user can inspect, review, and audit all netlists and simulation scripts locally, providing maximum confidence in the agent's work.

---

## 🤖 MANDATORY_AGENT_PRE_TASK_HOOKS (Machine Directives)

> **STRICT AGENT INSTRUCTION**: Before invoking any MCP tool or generating code for the tasks below, the AI Agent MUST execute `view_file` on the linked specification file to load domain constraints into active memory.

| Action Trigger / Task Intent | Mandatory Target Spec File | Required Pre-Execution Context Inspection |
| :--- | :--- | :--- |
| **Schematic Design Workflow** / Creating Analog Schematics | [`Scamatic_small.md`](/Users/vs/function/EDA_MCP2/SKILL/Scamatic_small.md) | 5-Step sequential procedure: ASCII schematic preview $\rightarrow$ `ask_question` user confirmation $\rightarrow$ Virtuoso SKILL creation & `geOpen` window display $\rightarrow$ `ask_question` for Eldo simulation. |
| **`virtuoso(...)`** / SKILL Code / Schematic Generation | [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md) | PDK cell names (`cmos065`), pin types (`ipin`/`opin`/`iopin`), zero `schCheck` warnings policy, GUI `geOpen` window display. |
| **`eldo(...)`** / SPICE Netlists / Simulations | [`eldo_simulation_guide.md`](eldo_simulation_guide.md) | Line 1 title comment rule, Level-1 fallback models, REPL commands (`run`/`step`), `.extract` result parsing. |
| **Waveform Visualization** / Plotting SPICE Waveforms | [`eldo_simulation_guide.md#6-waveform-visualization-visualize_waveforms`](eldo_simulation_guide.md#6-waveform-visualization-visualize_waveforms) | `eldo(action="visualize_waveforms")` signal grouping rules, separating currents from logic voltages, and multi-window invocations. |
| **`workboard(...)`** / Workspace Synchronization | [`workboard_sync_guide.md`](workboard_sync_guide.md) | Git baseline commit tracking ($C_{\text{sync}}$), line-by-line unified diff advancing, `.workboard.json` schema. |
| **`report_issue(...)`** / Bug Reports & Feature Requests | [`issue_reporting_guide.md`](issue_reporting_guide.md) | Freeform Markdown formatting, bug reproduction templates, enhancement implementation milestone structures. |
| **Tool Interface Schemas & Action Modes** | [`mcp_tools_spec.md`](mcp_tools_spec.md) | TypeScript interface schemas, parameter types, timeouts, action mode invariants for all 5 MCP tools. |

---

## Agent Context Index

- [`Scamatic_small.md`](/Users/vs/function/EDA_MCP2/SKILL/Scamatic_small.md): Quick step-by-step procedure for creating analog schematics, ASCII previews, `ask_question` user confirmations, and Virtuoso/Eldo workflows.
- [`mcp_tools_spec.md`](mcp_tools_spec.md): Complete tool interface specification (`remote_control`, `virtuoso`, `eldo`, `workboard`, `report_issue`).
- [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md): PDK parameters (`cmos065`), SKILL schematic & layout code blocks, GUI `geOpen` window rules.
- [`eldo_simulation_guide.md`](eldo_simulation_guide.md): SPICE netlist syntax, level-1 fallback models, REPL commands, `.extract` parsing.
- [`workboard_sync_guide.md`](workboard_sync_guide.md): Local-remote file sync, Git commit baseline tracking ($C_{\text{sync}}$), and native Git commands.
- [`issue_reporting_guide.md`](issue_reporting_guide.md): Suggested guidelines & rich Markdown formatting examples for bug reports and feature requests.
