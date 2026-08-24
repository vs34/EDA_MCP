# WORKBOARD_SYNC_SPEC

## 1. Local-Remote Workspace Mapping
- **Local WorkBoard Root**: `./workboard/<workboard_name>/`
- **Registry File**: `./workboard/<workboard_name>/.workboard.json`
- **Sync Baseline**: `last_sync_commit` (SHA of local Git commit at last synchronized state $C_{\text{sync}}$)

`local_path` is relative to the selected WorkBoard root, not an arbitrary workspace path. To create a new simulation deck, first initialize/select a board, then create the file at `./workboard/<workboard_name>/<local_path>` before calling `export`.

### Local Deck Authoring Protocol
To write `./workboard/<name>/tb_<cell>.cir`:
- Write `./workboard/<name>/tb_<cell>.txt` then run `mv ./workboard/<name>/tb_<cell>.txt ./workboard/<name>/tb_<cell>.cir`.
- [Antigravity/Gemini Only]: `write_to_file` fallback requires `ArtifactMetadata: { "Summary": "Eldo deck", "UserFacing": false, "RequestFeedback": false }`.
- Export: `workboard(action="export", workboard_name="<name>", local_path="tb_<cell>.cir", remote_path="~/Desktop/eldo/tb_<cell>.cir")`.

Example lifecycle:

```text
workboard(action="initialize", workboard_name="inverter_sim")
# write ./workboard/inverter_sim/tb_inverter.txt -> mv to tb_inverter.cir
workboard(action="export", workboard_name="inverter_sim",
          local_path="tb_inverter.cir", remote_path="~/Desktop/eldo/tb_inverter.cir")
```

When more than one WorkBoard exists, pass `workboard_name` on every operation unless the current server session has already selected one. That selection is session-local; do not assume it persists across MCP server restarts.

---

## 2. Action State Matrix

| Action | Target Input | Local Git Effect | Sync Baseline ($C_{\text{sync}}$) |
| :--- | :--- | :--- | :--- |
| `initialize` | `workboard_name` | `git init`, write `.gitignore` | Created |
| `add` | `remote_path`, `local_path` | Download via SCP, `git commit` | Updated to `HEAD` |
| `pull` | `local_path` | Re-download via SCP, `git commit` | Advanced to `HEAD` |
| `push` | `local_path` | Upload via SCP, `git commit` | Advanced to `HEAD` |
| `diff` | `local_path` | Compare local vs remote bytes | Auto-advanced if 100% match |
| `status` | None | Read-only state report | Read-only |
| `history` | `local_path` | `git log -n 10` execution | Read-only |

---

## 3. Native Git Shell Navigation Commands
Agent can execute terminal commands inside `./workboard/<name>/`:
- Commit log: `git log -n 10 --oneline -- <local_path>`
- Baseline state view: `git show <commit_sha>:<local_path>`
- Revert file to baseline: `git checkout <commit_sha> -- <local_path>`
- Diff baselines: `git diff <commit_sha_1> <commit_sha_2> -- <local_path>`

---

## 4. Local Tooling & Sizing Computation Authorization
- Agents may use local tools to calculate transistor aspect ratios ($W/L$), evaluate equations, analyze retrieved results, and author **simulation decks**. Structural transistor netlists must come from the verified Virtuoso exporter, not local reconstruction.
