# CODER_CONTEXT_SPEC (Python MCP Server Implementation)

## Component Map & File References

| Component | Source File | Class / Function | Description |
| :--- | :--- | :--- | :--- |
| **MCP Entrypoint** | [`server.py`](../../server.py) | `FastMCP("EDA_MCP")` | Registers 4 MCP tools, initializes per-tool SSH sessions, configures logger (`logs/eda_mcp_*.log`). |
| **SSH Transport** | [`ssh_client.py`](../../ssh_client.py) | `RemoteSession` | Manages persistent `csh` subshell over SSH, sentinel execution (`_read_until_sentinel`), and interactive stream reading (`execute_interactive_stream`). |
| **SCP Transport** | [`scp_client.py`](../../scp_client.py) | `SCPClient` | Executes OpenSSH `scp -O` for direct binary/folder transfer without shell escaping overhead. |
| **Virtuoso Interface** | [`virtuoso_client.py`](../../virtuoso_client.py) | `VirtuosoClient` | Manages SKILL FIFO pipe (`MCP.command`) IPC polling (`mcp_output.txt`) and `virtuoso -nograph` REPL streaming. |
| **Eldo Interface** | [`eldo_client.py`](../../eldo_client.py) | `EldoClient` | Manages `eldo -inter` REPL streaming and `.extract` measurement summary parsing. |
| **WorkBoard Engine** | [`workboard_client.py`](../../workboard_client.py) | `WorkBoardClient` | Manages `./workboard/<name>/` local Git repositories, `.workboard.json` manifests, SHA-256 checksums, and unified diffs. |

---

## Coder Agent Operational Invariants (MUST FOLLOW)

1. **AGENT_IDENTITY_BRANCHING**: Every issue fix or enhancement MUST be created on a feature branch named `<agent_name>/issue-<issue_number>-<description>` (e.g., `antigravity/issue-42-eldo-timeout-fix`).
2. **AGENT_IDENTITY_COMMITS**: All commits MUST explicitly declare custom agent author metadata: `git -c user.name="<AgentName>" -c user.email="<agent>@ai.local" commit -m "..."`.
3. **PULL_REQUEST_EXPLANATION**: Pull Requests MUST be created via `gh pr create` with a clear explanation of root cause, fix details, test verification, and issue linkage (`Fixes #<issue_number>`).
4. **STRICT_NO_AUTOMERGE_POLICY**: Coder Agents MUST NEVER merge PRs or push directly to `main`. Stop execution immediately after `gh pr create` and request Human Code Review.

---

## Coder Context Index

- [`issue_resolution_workflow.md`](issue_resolution_workflow.md): Standard operating procedure for Coder agents resolving issues, creating agent branches, PR formatting, and human review gates.
- [`server_and_mcp.md`](server_and_mcp.md): FastMCP tool signatures, tool action dispatching, session isolation logic.
- [`transport_layer.md`](transport_layer.md): Subshell IO pipes, sentinel token format, regex prompt match loop, SCP command generation.
- [`eda_tool_clients.md`](eda_tool_clients.md): FIFO pipe write/read contract, REPL interactive streaming state machine.
- [`workboard_backend.md`](workboard_backend.md): `.workboard.json` schema, Git subprocess wrapper (`_git_cmd`), `diff` auto-advance algorithm.
- [`known_issues_and_maintenance.md`](known_issues_and_maintenance.md): Bug audit list (missing `run_script`), test discovery commands.
