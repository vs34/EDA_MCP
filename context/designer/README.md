# EDA-MCP Designer Context

This is an operational specification for an AI agent that designs, inspects, and simulates circuits through EDA-MCP. It is not a user tutorial and it does not prescribe one circuit-design method. Apply engineering judgment: choose an appropriate topology, analysis, execution mode, and amount of explanation from the user's objective, supplied constraints, and available tool capabilities.

## Authority, scope, and judgment

- Treat [`mcp_tools_spec.md`](mcp_tools_spec.md) and the live MCP tool schema as the interface contract. If they disagree, use the live schema and report the documentation drift only when reporting is authorized.
- `MCP` is the default library for generated cellviews, testbenches, and layouts. A user-supplied library is an explicit override.
- Do not invent tool actions, host tools, PDK APIs, file paths, model files, or simulation results. Inspect or ask for the missing fact.
- Use confirmation when a material design choice is unspecified, an operation overwrites an existing artifact, a modal GUI action needs human input, or the user has asked to review before execution. Do not introduce confirmation gates for an already-specified and authorized task.
- Use reasoning where it adds value: derive initial sizing, choose analyses and measurements, inspect diagnostics, and revise the design based on evidence. Do not substitute generic templates for electrical reasoning.

## Non-negotiable correctness constraints

1. **Session ownership** — Use `virtuoso(action="run_terminal_command")` for Virtuoso-shell commands and `eldo(action="run_terminal_command")` for Eldo-shell commands. Use `remote_control` only for its own remote-shell/read/write operations; its environment is separate.
2. **Remote artifacts** — Do not create remote files through shell redirection or shell file-creation commands. For reviewable simulation decks and downloaded artifacts, use WorkBoard. `remote_control(action="write_file")` is permitted only when the task explicitly requires direct remote file I/O and WorkBoard is unsuitable.
3. **Schematic validity** — Logical net membership alone is insufficient for this PDK. Create physical schematic wires that touch the intended instance and pin terminals, then inspect `schCheck` output. Do not claim a clean schematic unless the observed result is `(0 0)`.
4. **MOS lifecycle and units** — For `cmos065` MOS instances, initialize CDF through `initMosTransistor(inst wMicrons lMicrons)` (or the documented DK lifecycle). Pass width and length as micron strings, for example `"2.0"` and `"0.065"`.
5. **GUI lifecycle** — In `assisted_run`, guard display with `unless(geGetCellViewWindow(cv) geOpen(...))`; do not `dbClose(cv)` when leaving that view displayed. In a headless standalone flow, close database views after saving.
6. **Netlisting** — Never use the obsolete `hnlInit` / `hnlNetlist` template. Export the structural netlist from the Virtuoso schematic using a verified CDL exporter; see [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md). A simulation deck may be authored locally, but it must include the exported structural netlist rather than duplicating transistor connectivity by hand.
7. **Simulation integrity** — Treat Level-1 MOS models only as explicitly labelled sanity checks. Do not use them as a substitute for the installed `cmos065` model deck or present their results as PDK-accurate.
8. **SKILL file output** — Before closing an `outfile` stream, call `drain(fileId)`.
9. **Side effects** — Creating GitHub issues is external and persistent. Use `report_issue` only with explicit user authorization or a stated project policy that authorizes autonomous reporting; first search for a duplicate.

## Context routing

Read the smallest relevant guide before acting. If the host does not provide a tool named `view_file`, read the linked file through its normal filesystem/resource mechanism; absence of that host-specific tool is not a reason to stop.

| Intent | Read first |
| --- | --- |
| Design or edit a schematic | [`schematic_flow.md`](schematic_flow.md), then [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md) |
| Invoke Virtuoso or write SKILL | [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md) |
| Run Eldo or inspect waveforms | [`eldo_simulation_guide.md`](eldo_simulation_guide.md) |
| Transfer or version artifacts | [`workboard_sync_guide.md`](workboard_sync_guide.md) |
| Report a bug or enhancement | [`issue_reporting_guide.md`](issue_reporting_guide.md) |
| Determine any tool arguments or actions | [`mcp_tools_spec.md`](mcp_tools_spec.md) |

## Artifact workflow

1. Determine whether existing artifacts can be reused and whether the user has specified enough design intent.
2. Build or update the schematic, using physical wires and a clean `schCheck` result as the completion criterion.
3. Export a structural netlist with the verified Virtuoso CDL flow.
4. Create the simulation deck locally inside a WorkBoard, inspect it, export it, simulate it, and retrieve the resulting text/binary outputs for analysis.
5. Report measurements, assumptions, limitations, and any verification evidence. When results contradict intent, diagnose and iterate rather than asserting success.

## Guide index

- [`schematic_flow.md`](schematic_flow.md): judgment-driven design and validation workflow.
- [`mcp_tools_spec.md`](mcp_tools_spec.md): tool arguments, action modes, defaults, and side effects.
- [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md): PDK-aware SKILL, wiring, CDF, GUI, and verified netlist export guidance.
- [`eldo_simulation_guide.md`](eldo_simulation_guide.md): structural-netlist simulation and results handling.
- [`workboard_sync_guide.md`](workboard_sync_guide.md): local artifact placement and synchronization semantics.
- [`issue_reporting_guide.md`](issue_reporting_guide.md): authorized, deduplicated issue reporting.
