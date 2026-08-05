# 🏛️ WorkBoard Architecture Specification (`EDA_MCP`)

## 1. Executive Summary & Core Scope

### 1.1 Core Scope Definition
`EDA_MCP` serves strictly as a **high-performance communication and file-synchronization bridge between the remote EDA server and the local AI agent**.

> [!NOTE]
> **Scope Scoping**: Domain-specific tasks like netlist parsing or waveform plotting are kept **out of scope** for `EDA_MCP` itself. Those are left to separate local scripts or agent skills. `EDA_MCP` focuses purely on robust remote command execution, file sync, local Git version control, and state management.

### 1.2 The Local Control Plane & Remote Execution Model
```
┌──────────────────────────────────────────────────────────┐                      ┌──────────────────────────┐
│              LOCAL SYSTEM (Your Machine)                 │                      │    REMOTE EDA SERVER     │
│                                                          │                      │                          │
│  ┌────────────────────────────────────────────────────┐  │      SSH Tunnel      │  • Cadence Virtuoso      │
│  │               EDA_MCP (FastMCP Server)             │  ├─────────────────────►│  • Siemens Eldo          │
│  │                                                    │  │  (Command & File IO) │  • Raw Remote Files      │
│  │  • Remote Command Exec  • Local Git WorkBoard Sync │  │◄─────────────────────┤  • Netlists & Results    │
│  └────────────────────────────────────────────────────┘  │                      └──────────────────────────┘
└──────────────────────────────────────────────────────────┘
```

---

## 2. WorkBoard Core Actions & Behavior

The `workboard` tool manages isolated local workspaces backed by local Git repositories.

### 2.1 Action Lifecycle & Specifications

#### 1. `initialize(workboard_name, local_dir)`
* **Behavior**: Creates a brand-new, clean local WorkBoard workspace directory and initializes a local Git repository (`git init`) inside it.
* **Scope**: Does **NOT** pull any files from the server during initialization.
* **Multi-WorkBoard Support**: Calling `initialize` with a new name creates an independent workboard (e.g. `opamp_v1`, `inv_tb`), allowing the agent to manage multiple designs cleanly.

#### 2. `add(remote_path, local_path, workboard_name)`
* **Behavior**: Fetches a file or directory from any location on the remote EDA server and saves it into the designated local WorkBoard workspace.
* **WorkBoard Selection**:
  * If `workboard_name` is omitted and only **one** WorkBoard exists, it automatically uses that active WorkBoard.
  * If **multiple** WorkBoards exist, `workboard_name` specifies the target workspace.
* **Path Mapping**: Downloads the remote file to the relative `local_path` inside the WorkBoard (auto-creating subdirectories), records the remote-to-local path mapping in `.workboard.json`, and commits the file into the local Git repo (`git add & git commit`).

#### 3. `pull(local_path, workboard_name)`
* **Behavior**: Re-fetches the latest version of an already-added file/directory from the remote EDA server to update the local WorkBoard file, committing the update into the local Git repo.

#### 4. `push(local_path, workboard_name, message)`
* **Behavior**: Uploads local edits from the WorkBoard back to its mapped remote server location over SSH, updating the server file and committing the change locally with a Git commit message.

#### 5. `diff(local_path, workboard_name)`
* **Behavior**: Generates a unified line-by-line diff between the local WorkBoard file and the remote server file (or local Git baseline).

#### 6. `status(workboard_name)`
* **Behavior**: Reports the status of all tracked files in the WorkBoard (`IN_SYNC`, `LOCAL_MODIFIED`, `REMOTE_MODIFIED`).

---

## 3. System Architecture & Components

### 3.1 Architectural Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             LOCAL SYSTEM (Your Machine)                          │
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                      EDA_MCP (FastMCP Python Server)                     │   │
│   │                                                                          │   │
│   │   ┌───────────────────┐               ┌──────────────────────────────┐   │   │
│   │   │  workboard tool   ├──────────────►│     workboard_client.py      │   │   │
│   │   └───────────────────┘               │  • Local Git Engine Wrapper  │   │   │
│   │                                       │  • Path Registry Manager     │   │   │
│   │                                       └──────────────┬───────────────┘   │   │
│   └──────────────────────────────────────────────────────┼───────────────────┘   │
│                                                          │                       │
│   ┌──────────────────────────────────────────────────────▼───────────────────┐   │
│   │                      Local WorkBoards Root (./workboard/)                │   │
│   │                                                                          │   │
│   │  ├── workboard_1 (e.g., ./workboard/inverter_tb/)                        │   │
│   │  │   ├── .git/                      (Local Git Repository)               │   │
│   │  │   ├── .gitignore                 (Ignores *.tr0, *.wdb)               │   │
│   │  │   ├── .workboard.json            (Remote-to-Local File Registry)      │   │
│   │  │   └── netlists/inv_tb.cir        (Synced Netlist)                     │   │
│   │  │                                                                       │   │
│   │  └── workboard_2 (e.g., ./workboard/opamp_v1/)                           │   │
│   │      ├── .git/                      (Local Git Repository)               │   │
│   │      ├── .workboard.json                                                 │   │
│   │      └── schematics/opamp.il        (Synced SKILL Code)                  │   │
│   └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────┼────────────────────────────────────────┘
                                          │ SSH Transport
                                          │ (base64 / scp / ssh)
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│                             REMOTE EDA SERVER                                    │
│                                                                                  │
│  ├── ~/Desktop/eldo/inv_tb.cir          (Netlist File)                           │
│  ├── /cadence/pdk/cmos65/models/tt.lib  (PDK Model File)                        │
│  └── /tmp/sim_run_991/deck.extract      (Simulation Extract Output)              │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. WorkBoard Registry Specification (`.workboard.json`)

Each WorkBoard directory contains its own isolated `.workboard.json` file:

```json
{
  "workboard_name": "inverter_tb",
  "local_root": "./workboard/inverter_tb",
  "created_at": "2026-08-05T15:42:00Z",
  "last_synced": "2026-08-05T15:45:00Z",
  "files": {
    "netlists/inv_tb.cir": {
      "remote_path": "~/Desktop/eldo/inv_tb.cir",
      "local_checksum": "e3b0c44298fc1c14...",
      "remote_mtime": "1722802000",
      "sync_status": "IN_SYNC",
      "is_directory": false
    },
    "models/tt.lib": {
      "remote_path": "/cadence/pdk/cmos65/models/tt.lib",
      "local_checksum": "a1b2c3d4e5f67890...",
      "remote_mtime": "1722802500",
      "sync_status": "IN_SYNC",
      "is_directory": false
    }
  }
}
```

---

## 5. MCP Tool Schema (`workboard`)

Exposed to the AI agent in `server.py`:

```python
@mcp.tool()
def workboard(
    action: str,
    workboard_name: str = "",
    remote_path: str = "",
    local_path: str = "",
    message: str = "Agent sync",
    recursive: bool = False,
    timeout: float = 60.0
) -> str:
    """
    Git-backed WorkBoard tool for local-remote file synchronization and version control.
    
    Actions:
      - 'initialize': Create a new local WorkBoard workspace and initialize a local Git repository.
      - 'add': Fetch a file/folder from remote server path and add it to a specific WorkBoard at local_path.
      - 'pull': Re-fetch latest remote server version of an added file to update the local WorkBoard.
      - 'push': Upload local edits from WorkBoard back to mapped remote server location and commit locally.
      - 'diff': Display unified diff between local WorkBoard file and remote server version.
      - 'status': List all tracked files and their status for a specific WorkBoard.
    """
```

---

## 6. Detailed Workflow Sequence

```
       [USER / AGENT]                     [WORKBOARD BACKEND]                  [REMOTE EDA SERVER]
             │                                    │                                     │
 1. Initialize WorkBoard ("inverter_tb")          │                                     │
             ├───────────────────────────────────►│ Creates ./workboard/inverter_tb/    │
             │                                    │ Runs 'git init' inside folder       │
             │                                    │ Creates empty .workboard.json       │
             │                                    │                                     │
 2. Add File ("add")                              │                                     │
             │ remote_path="~/Desktop/eldo/inv.cir"│                                     │
             │ local_path="netlists/inv.cir"      │                                     │
             ├───────────────────────────────────►│ Reads remote file over SSH ────────►│
             │                                    │◄── Returns file content ────────────┤
             │                                    │ Saves to netlists/inv.cir           │
             │                                    │ Records mapping in .workboard.json  │
             │                                    │ Runs 'git add & git commit'         │
             │                                    │                                     │
 3. Local Edit (Agent modifies netlist)           │                                     │
             │ Edits netlists/inv.cir locally     │                                     │
             │                                    │                                     │
 4. Check Diff & Push                             │                                     │
             ├───────────────────────────────────►│ Runs 'git diff'                     │
             │                                    │ Writes file to remote server ──────►│
             │                                    │ Runs 'git commit -am Push'          │
             │                                    │                                     │
 5. Pull Simulation Results                       │                                     │
             │ action="add"                       │                                     │
             │ remote_path="/tmp/run1/extract"    │                                     │
             │ local_path="results/run1.extract"  │                                     │
             ├───────────────────────────────────►│ Downloads file over SSH ───────────►│
             │                                    │ Saves & commits locally             │
             │◄───────────────────────────────────┤                                     │
```

---

## 7. Edge Cases & Safeguards

1. **Multi-WorkBoard Disambiguation**: If `workboard_name` is not specified when multiple WorkBoards exist, the system returns an informative error listing available WorkBoards to prompt selection.
2. **Ignored Binaries**: Large binary files (`*.tr0`, `*.wdb`) are ignored by default in local `.gitignore` to keep local Git history lightweight.
3. **Local Rollback**: If an agent edit causes remote simulation failure, the user or agent can run `git checkout -- <file>` inside the local WorkBoard to restore the last clean netlist instantly.
