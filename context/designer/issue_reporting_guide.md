# ISSUE_REPORTING_GUIDE (Designer Agent Guidelines)

This guide provides **suggested guidelines** for Chip Design AI Agents when using the `report_issue` tool to report bugs or request new enhancements.

> 💡 **Flexibility Note**: These guidelines are **helpful suggestions and best-practice recommendations**, NOT rigid rules. You have full freedom to format and structure your issue body using rich Markdown as best fits the situation.

---

## 1. Reporting a Bug (Suggested Content)

When reporting a tool error, crash, or unexpected behavior, consider including:

- **Tool Name**: Mention which tool was involved (`virtuoso`, `eldo`, `workboard`, or `remote_control`).
- **Encounter Context**: Briefly explain what task or chip design intent you were attempting when the bug occurred (e.g. *"Simulating 65nm CMOS inverter transient response"*).
- **Steps to Reproduce**: Provide the exact tool action, SKILL snippet, netlist snippet, or sequence of calls that triggered the failure.
- **Observed vs. Expected Behavior**: 
  - Include raw error tracebacks, log outputs, or error messages returned by the tool.
  - Explain what went wrong and what you expected to happen instead.

### Example Bug Report Body:

````markdown
## Bug: Eldo simulation timeout during IPC log polling

### Tool & Context
- **Tool**: `eldo` (action: `run_script`)
- **Intent**: Running transient simulation for 65nm OPAMP phase margin check.

### Steps to Reproduce
1. Uploaded netlist `opamp_tran.cir` via `remote_control(action="write_file")`.
2. Executed `eldo(action="run_script", script_path="opamp_tran.cir")`.

### Observed Behavior
The tool call timed out after 600s waiting for the output log lock file:
`TimeoutError: Eldo simulation exceeded 600s wait limit for file lock on /remote/sim/opamp_tran.chi`

### Expected Behavior
The polling loop should retry file lock acquisition with exponential backoff or report simulation progress cleanly.
````

---

## 2. Requesting an Enhancement / Feature (Suggested Content)

When proposing a new tool capability, parameter, or architectural improvement, consider including:

- **What to Enhance / Add**: Clearly state the proposed new feature or tool extension.
- **Why it is Needed**: Explain the bottleneck, friction point, or limitation in your current chip design workflow that this enhancement will solve.
- **How to Enhance / Ideal Behavior**:
  - Describe how the proposed feature should work.
  - Show how the ideal tool parameter schema, output format, or API signature should look.
  - Include code snippets or usage examples illustrating the ideal workflow.
- **Proposed Implementation Milestones**: Break down the implementation into clear, incremental milestones (e.g. Phase 1: API / Tool signature; Phase 2: Execution backend; Phase 3: Unit tests & docs) to guide the Coder Agent (Agent B) in implementing the feature cleanly.

### Example Enhancement Request Body:

````markdown
## Feature Request: Native Spectre Netlist Parser (`read_spectre_extract`)

### What to Add
Add native support to `virtuoso` or `eldo` tools for parsing Cadence Spectre `.scs` netlist measurement summaries.

### Why it is Needed
Currently, extracting transistor operating point parameters ($g_m$, $V_{dsat}$, $I_D$) from Spectre netlists requires running custom raw terminal commands. A dedicated parser tool would allow instant verification of bias points during automated sizing iterations.

### Proposed Ideal Behavior & API
```typescript
eldo(action="read_spectre_extract", extract_path="opamp_dc.raw")
```
Should return a structured JSON dictionary of device operating parameters:
```json
{
  "M0": { "gm": "1.2m", "vdsat": "150m", "id": "100u" }
}
```

### Proposed Implementation Milestones
- [ ] **Phase 1**: Add `read_spectre_extract` action definition to `eldo_client.py` and tool signature in `server.py`.
- [ ] **Phase 2**: Implement Spectre `.scs` regex parser to extract device operating points.
- [ ] **Phase 3**: Add unit tests in `tests/test_eldo_client.py`.
````

---

## 3. Tool Reference

```typescript
report_issue({
  title: string,        // Concise summary of the bug or feature request
  body?: string,        // Freeform Markdown content (see suggestions above)
  label?: string,       // Default: "bug" (e.g. "enhancement", "feature-request")
  agent_model?: string, // Your active model ID (e.g. "gemini-3.6-flash", "claude-3-5-sonnet")
  session_id?: string   // Current conversation turn ID
})
```
