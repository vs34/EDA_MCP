# DESIGNER_CONTEXT_SPEC (Chip Design AI Agent System Instruction)

## Repository & Client Binding
- **GitHub Repository**: [`https://github.com/vs34/EDA_MCP.git`](https://github.com/vs34/EDA_MCP.git)
- **Protocol**: Model Context Protocol (FastMCP Stdio)
- **Entrypoint**: [`server.py`](file:///Users/vs/function/EDA_MCP/server.py)

```json
{
  "mcpServers": {
    "eda-mcp": {
      "command": "python3",
      "args": ["/Users/vs/function/EDA_MCP/server.py"]
    }
  }
}
```

---

## Agent Operational Invariants (MUST FOLLOW)

1. **LIBRARY_SCOPE**: All generated cellviews, schematics, testbenches, and layouts MUST reside in library `MCP` unless explicitly overridden.
2. **SESSION_ISOLATION**:
   - Virtuoso shell commands -> `virtuoso(action="run_terminal_command")`
   - Eldo shell commands -> `eldo(action="run_terminal_command")`
   - File I/O & raw remote shell -> `remote_control`
   - DO NOT use `remote_control` for Virtuoso/Eldo tool shell commands (does not share working directory or environment).
3. **FILE_IO_RULE**: File reads/writes on remote server MUST use `remote_control(action="read_file")` and `remote_control(action="write_file")` (never use `cat`/`echo` via shell).
4. **SCHEMATIC_CHECK_POLICY**: Zero-tolerance for `schCheck` warnings. Floating gates or unattached pins must be fixed before saving or netlisting.
5. **STREAM_FLUSH_RULE**: Every SKILL file stream (`outfile`) MUST execute `drain(fileId)` before `close(fileId)`.
6. **ELDO_TITLE_RULE**: Line 1 of any `.cir` netlist is strictly treated by Eldo as a title comment line.
7. **LOCAL_COMPUTATION_RULE**: Agents are fully authorized and encouraged to use local default capabilities, Python scripts, mathematical calculators, scratch scripts, and web research to perform transistor sizing ($W/L$), bias point calculations, schematic planning, and netlist formatting prior to remote execution.
8. **ASSISTED_RUN_LENGTH_RULE**: For `virtuoso(action="assisted_run")`, the SKILL code in `command` MUST NOT be excessively long. Keep commands concise and modular for `assisted_run`. For complex/long SKILL scripts, Break long SKILL to small portion according to complexity this will also increase debuggability if anything went wrong.

---

## Agent Context Index

- [`mcp_tools_spec.md`](file:///Users/vs/function/EDA_MCP/context/designer/mcp_tools_spec.md): Complete tool interface specification (`remote_control`, `virtuoso`, `eldo`, `workboard`).
- [`virtuoso_skill_guide.md`](file:///Users/vs/function/EDA_MCP/context/designer/virtuoso_skill_guide.md): PDK parameters (`cmos065`), SKILL schematic & layout code blocks.
- [`eldo_simulation_guide.md`](file:///Users/vs/function/EDA_MCP/context/designer/eldo_simulation_guide.md): SPICE netlist syntax, level-1 fallback models, REPL commands, `.extract` parsing.
- [`workboard_sync_guide.md`](file:///Users/vs/function/EDA_MCP/context/designer/workboard_sync_guide.md): Local-remote file sync, Git commit baseline tracking ($C_{\text{sync}}$), and native Git commands.
