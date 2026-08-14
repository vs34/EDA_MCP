# WORKBOARD_SYNC_SPEC

## 1. Local-Remote Workspace Mapping
- **Local WorkBoard Root**: `./workboard/<workboard_name>/`
- **Registry File**: `./workboard/<workboard_name>/.workboard.json`
- **Sync Baseline**: `last_sync_commit` (SHA of local Git commit at last synchronized state $C_{\text{sync}}$)

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
- Agents are fully authorized to use any local environment tools (Python scripts, math/symbolic packages, scratch scripts, local file generators, and web research) to calculate transistor aspect ratios ($W/L$), generate local SPICE netlists, draft schematic definitions, or evaluate circuit equations before invoking `workboard(action="export")` or `workboard(action="push")`.

