# ISSUE_RESOLUTION_WORKFLOW (Coder Agent Guidelines)

This document establishes the **standard operating workflow** for Coder / Maintainer AI Agents (Agent B) when resolving GitHub issues, fixing bugs, or implementing requested tool enhancements in the `EDA_MCP` repository.

---

## Operational Invariants & Policies

### 1. 🌿 AGENT_IDENTITY_BRANCHING
- Every issue fix or enhancement MUST be implemented on a **dedicated feature branch** named after the active agent and issue ID:
  ```bash
  git checkout -b <agent_name>/issue-<issue_number>-<short-description>
  ```
- **Examples**:
  - `antigravity/issue-42-eldo-timeout-fix`
  - `codex/feature-spectre-parser`
  - `claude/issue-15-ssh-retry-logic`

---

### 2. ✍️ AGENT_IDENTITY_COMMITS
- All Git commits MUST explicitly declare author metadata corresponding to the active agent:
  ```bash
  git -c user.name="<AgentName>" -c user.email="<agent_name>@ai.local" commit -m "<type>: <concise description>"
  ```
- **Commit Types**:
  - `fix:` Bug fixes
  - `feat:` New features / tool enhancements
  - `refactor:` Code restructuring without functional changes
  - `test:` Unit test updates
  - `docs:` Documentation updates

---

### 3. 🔍 VERIFICATION BEFORE PR CREATION
- Before pushing changes or creating a Pull Request, the agent MUST run the full unit test suite and ensure all tests pass cleanly:
  ```bash
  python3 -m unittest discover tests
  ```

---

### 4. 📝 PULL REQUEST EXPLANATION & ISSUE LINKING
- The agent MUST open a Pull Request using `gh pr create`.
- The PR description MUST include:
  - **Summary**: Concise description of what was fixed or implemented.
  - **Root Cause & Technical Fix**: Technical explanation of why the bug occurred and how the code was updated.
  - **Test Verification**: Output summary of passing unit tests.
  - **Issue Link**: Explicit GitHub magic keyword tagging the original issue (`Fixes #<issue_number>` or `Closes #<issue_number>`).

#### Example PR Creation Command:
```bash
gh pr create \
  --title "fix(eldo): retry file lock acquisition during IPC polling" \
  --body "## Summary
Fixes Eldo simulation timeout caused by premature file lock failure.

## Technical Details & Root Cause
- Added exponential backoff retry loop in \`eldo_client.py\` when reading \`.chi\` output files.
- Auto-recovers from transient file locks without aborting simulation.

## Verification
- Ran \`python3 -m unittest discover tests\` (14/14 tests passing).

Fixes #42" \
  --base main
```

---

### 5. 🛑 STRICT NO AUTO-MERGE POLICY (HUMAN REVIEW GATE)
- **STRICT RULE**: The Coder Agent **MUST NEVER** execute `git merge`, `gh pr merge`, or merge code into `main`.
- Immediately after executing `gh pr create`, the Coder Agent MUST **STOP execution** and notify the human reviewer (You) that the PR is open and awaiting review.
- Only the human maintainer is authorized to review and merge code into `main`.

---

## Step-by-Step Coder Execution Checklist

1. [ ] **Inspect Issue**: Read issue details via `gh issue view <issue_number>`.
2. [ ] **Create Branch**: Run `git checkout -b <agent_name>/issue-<issue_number>-<description>`.
3. [ ] **Implement Fix**: Edit source files (`server.py`, `issue_reporter.py`, `*_client.py`).
4. [ ] **Verify Tests**: Run `python3 -m unittest discover tests` and ensure 0 failures.
5. [ ] **Commit with Identity**: Run `git -c user.name="<AgentName>" -c user.email="<agent>@ai.local" commit -m "..."`.
6. [ ] **Push Branch**: Run `git push origin <agent_name>/issue-<issue_number>-<description>`.
7. [ ] **Open Pull Request**: Run `gh pr create` with `Fixes #<issue_number>` and detailed explanation.
8. [ ] **Stop & Request Review**: Stop execution and inform the human reviewer.
