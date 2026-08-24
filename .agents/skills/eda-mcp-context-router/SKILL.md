---
name: eda-mcp-context-router
description: Autonomous task-routing and context-loading directive for AI agents in EDA_MCP. Directs the agent to execute view_file on context/designer/README.md for MCP tool execution (Virtuoso, Eldo, schematics, simulations) and context/coder/README.md for codebase development (issues, bugfixes, features, server maintenance) before taking any action.
---

# SYSTEM_DIRECTIVE: MANDATORY PRE-TASK CONTEXT ROUTING

> **STRICT AGENT EXECUTION INSTRUCTION**: Before generating code, proposing terminal commands, or invoking any MCP tool in this repository, you MUST execute `view_file` on the target context specification mapped to your current task intent.

---

## 1. Task Classification & Context Mapping

```text
TASK INTENT CLASSIFICATION                  MANDATORY SPECIFICATION TO READ (view_file)
──────────────────────────────────────────  ──────────────────────────────────────────
[CIRCUIT / MCP TOOL EXECUTION]          ──> context/designer/README.md
• Creating / editing schematics/layouts
• Running Virtuoso (assisted_run/standalone)
• Running Eldo simulations (batch/interactive)
• Writing SKILL scripts, sizing W/L, netlists
• Checking DRC/LVS or extracting operating points

[CODEBASE DEV / BUG FIXING / GITHUB]    ──> context/coder/README.md
• Resolving GitHub issues & fixing bugs
• Implementing new MCP tools / tool actions
• Modifying Python server/client backends
• Editing SSH, SCP, or WorkBoard sync logic
• Creating git branches, commits, & PRs
```

---

## 2. Track 1 Directives: Circuit Design & MCP Tools

**Trigger Intent:** User requests schematic creation, simulation, sizing, layout, or EDA tool execution.

### Pre-Execution Requirement:
```json
{
  "tool": "view_file",
  "arguments": {
    "AbsolutePath": "/Users/vs/function/EDA_MCP/context/designer/README.md"
  }
}
```

### Core Invariants Enforced:
1. `LIBRARY_SCOPE`: All generated cellviews MUST reside in library `MCP`.
2. `PDK_MAP`: Technology is `cmos065` ($65\text{nm}$ LP/GP). Core devices: `psvtgp` (PMOS), `nsvtgp` (NMOS). Pins from `basic` (`ipin`, `opin`, `iopin`).
3. `CDF_UNITS`: CDF fields `w` and `l` MUST receive string values in **Microns ($\mu\text{m}$)** (e.g., `"2.0"`, `"0.065"`). Never assign raw float meters (`2.0u`).
4. `CDF_LIFECYCLE`: Transistors MUST be initialized via `initMosTransistor(inst, wMicrons, lMicrons)` or `DK_mosInit` $\rightarrow$ `DK_CBmos('w)` $\rightarrow$ `DK_CBmos('l)` $\rightarrow$ `DK_mosDone(inst)`.
5. `SCH_CHECK`: Zero-tolerance for `schCheck` warnings (`(0 0)` required).
6. `GUI_OPEN_FIRST`: In `assisted_run`, ALWAYS open the Virtuoso GUI schematic window FIRST before building/modifying the schematic (`win = geOpen(?lib ... ?cell ... ?mode "a")`, `cv = geGetWindowCellView(win)`). Perform all schematic work (instances, wires, pins, CDF, `schCheck`) live in the open, visible window. DO NOT call `dbClose(cv)` when displaying in GUI.
7. `FILE_IO`: DO NOT write files directly to the remote server using shell commands (`printf`, `echo`, `cat <<EOF`). Use `remote_control(action="write_file")`, `workboard`, or tool export workflows.
8. `NETLIST_EXTRACTION`: DO NOT hand-write SPICE transistor netlists for Eldo. Programmatically extract structural netlist `<cellName>.net` from the Virtuoso schematic (`MCP` library) and wrap it using `.include "<cellName>.net"` inside the Eldo simulation config deck (`tb_<cellName>.cir`).
9. `ELDO_TITLE`: Line 1 of every Eldo `.cir` netlist is strictly treated as a title comment line.
10. `STATIC_CORNER_DECKS`: Process corner decks at `/modelfile_65nm/` (`typNtypP.cir`, `minNminP.cir`, `maxNmaxP.cir`, `maxNminP.cir`, `minNmaxP.cir`) are static, pre-verified server assets. DO NOT execute `remote_control` commands (`read_file`, `cat`, `ls`) to inspect or verify corner decks prior to simulation.

---

## 3. Track 2 Directives: Codebase Dev, Issue Resolution & PRs

**Trigger Intent:** User requests fixing a bug, resolving a GitHub issue, modifying Python source code, or updating server logic.

### Pre-Execution Requirement:
```json
{
  "tool": "view_file",
  "arguments": {
    "AbsolutePath": "/Users/vs/function/EDA_MCP/context/coder/README.md"
  }
}
```

### Core Invariants Enforced:
1. `BRANCH_NAMING`: Create feature branch: `<agent_name>/issue-<issue_number>-<description>`.
2. `AGENT_COMMITS`: Author commits with agent metadata: `git -c user.name="<AgentName>" -c user.email="<agent>@ai.local" commit -m "..."`.
3. `PR_CREATION`: Open PR via `gh pr create` with metadata header banner (`Resolved by Agent`, `agent_model`, `session_id`, `log_file`), root cause explanation, test proof, and `Fixes #<id>`.
4. `NO_AUTOMERGE`: NEVER push to `main` or merge PRs. Halt immediately after `gh pr create` and request human review.
5. `SESSION_ISOLATION`: Maintain strict SSH session isolation across tool instances.
