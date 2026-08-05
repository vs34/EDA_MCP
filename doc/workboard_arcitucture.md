# 🏛️ WorkBoard Architecture Specification (`EDA_MCP`)

## 1. Executive Summary & Core Motivation

### 1.1 The Remote EDA vs. Local AI Divide
Modern integrated circuit (IC) design relies on heavy Electronic Design Automation (EDA) suites (Cadence Virtuoso, Siemens Eldo, Mentor Calibre) executing on remote Linux clusters. Conversely, AI coding agents (such as Antigravity) and user IDEs operate on local workstations.

Connecting local AI agents to remote EDA servers over SSH creates critical bottlenecks:
* **Visual Blindness**: Simulation outputs (`.tr0`, `.vcd`, `.extract`) sit on the remote server. Neither the user nor the local AI agent can view simulation plots or open waveform viewers natively.
* **Token Bloat & SSH Delays**: Reading multi-thousand-line netlists over remote SSH commands line-by-line is slow, token-expensive, and prone to connection timeouts.
* **Locked-Down Remote Environments**: Remote Linux clusters often lack modern Python libraries (`matplotlib`, `optuna`, `spicelib`, `graphviz`) or local GUI apps, restricting the AI agent from running advanced optimization algorithms locally.

### 1.2 The WorkBoard Solution
**WorkBoard** establishes a **Local Control Plane + Remote Execution Engine** hybrid model:
* **Local Machine = Control & Intelligence**: Runs the AI agent, local Git version control, Python optimization algorithms, netlist parsers, and visual chart renderers.
* **Remote Host = Compute Engine**: Executes heavy Eldo simulations, Virtuoso SKILL scripts, and Calibre DRC/LVS runs.

---

## 2. Key Objectives & Capabilities

| Objective | Description |
| :--- | :--- |
| **Instant Waveform Visualization** | Automatically pull simulation outputs and render high-resolution PNG/SVG plot artifacts directly in your chat interface or open them in local desktop GTKWave. |
| **Arbitrary Path Pulling & Renaming** | Pull files from *any path* on the remote server (`/cadence/pdk/...`, `~/Desktop/eldo/...`, `/tmp/...`), rename them locally, and organize them into clean local subfolders (`netlists/`, `results/`, `models/`). |
| **Local Git Backend** | Local `./workboard/` workspace operates as a local Git repository, providing automatic commit history, local rollback (`git checkout`), and native line diffs (`git diff`) without requiring Git on the remote server. |
| **Agent Git-Style Interface** | Exposes a clean, familiar 5-action interface (`initialize`, `pull`, `push`, `diff`, `status`, `plot`) to the AI agent. |

---

## 3. Full System Architecture

### 3.1 Architectural Overview Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             LOCAL SYSTEM (Your Machine)                          │
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                      EDA_MCP (FastMCP Python Server)                     │   │
│   │                                                                          │   │
│   │   ┌───────────────────┐    ┌────────────────────┐    ┌────────────────┐  │   │
│   │   │  workboard tool   │    │  netlist_parser.py │    │waveform_engine.│  │   │
│   │   └─────────┬─────────┘    └────────────────────┘    └────────────────┘  │   │
│   │             │                                                           │   │
│   │   ┌─────────▼────────────────────────────────────────────────────────┐   │   │
│   │   │                     workboard_client.py                          │   │   │
│   │   │  • Git Engine Wrapper (subprocess/git)   • Sync Manager          │   │   │
│   │   │  • Registry Manager (.workboard.json)    • Diff Engine           │   │   │
│   │   └─────────┬────────────────────────────────────────────────────────┘   │   │
│   └─────────────┼────────────────────────────────────────────────────────────┘   │
│                 │                                                                │
│   ┌─────────────▼────────────────────────────────────────────────────────────┐   │
│   │             Local WorkBoard Directory (Local Git Repository)             │   │
│   │                    (e.g., ./workboard/inverter_design/)                  │   │
│   │  ├── .git/               (Local Commit History & Branching)              │   │
│   │  ├── .gitignore          (Ignores *.tr0, *.wdb binary dumps)             │   │
│   │  ├── .workboard.json     (Remote-to-Local File Registry)                 │   │
│   │  ├── netlists/inv_tb.cir                                                 │   │
│   │  ├── models/tt.lib                                                       │   │
│   │  └── results/dc_sweep.extract                                            │   │
│   └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────┼────────────────────────────────────────┘
                                          │ SSH Transport
                                          │ (base64 / scp / ssh)
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│                             REMOTE EDA SERVER                                    │
│                                                                                  │
│  ├── ~/Desktop/eldo/inv_tb.cir          (Netlist File)                           │
│  ├── /cadence/pdk/cmos65/models/tt.lib  (PDK Model File)                        │
│  └── /tmp/sim_run_991/deck.extract      (Simulation Output Output)               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specification

### 4.1 The Registry Manifest (`.workboard.json`)
The manifest lives inside the root of each local workboard directory. It maps local relative file paths to arbitrary remote server paths:

```json
{
  "workboard_name": "inverter_design",
  "remote_default_dir": "~/Desktop/eldo",
  "local_root": "./workboard/inverter_design",
  "last_synced": "2026-08-05T15:00:00Z",
  "files": {
    "netlists/inv_tb.cir": {
      "remote_path": "~/Desktop/eldo/inv_tb.cir",
      "local_checksum": "e3b0c44298fc1c14...",
      "remote_mtime": "1722802000",
      "sync_status": "IN_SYNC",
      "is_binary": false
    },
    "results/dc_sweep.extract": {
      "remote_path": "/tmp/sim_run_991/deck.extract",
      "local_checksum": "a1b2c3d4e5f67890...",
      "remote_mtime": "1722802500",
      "sync_status": "REMOTE_MODIFIED",
      "is_binary": false
    }
  }
}
```

---

### 4.2 The Local Git Backend Engine (`workboard_client.py`)
The backend uses Python `subprocess` (or `GitPython`) to run Git commands locally inside `./workboard/`:

1. **`initialize(work_dir, remote_dir)`**:
   * Creates `./workboard/{name}/` directory.
   * Runs `git init` locally.
   * Writes `.gitignore` ignoring large simulation binaries (`*.tr0`, `*.wdb`, `*.vcd`).
   * Writes initial `.workboard.json`.

2. **`pull(remote_path, local_path, recursive=False)`**:
   * Fetches remote file/directory over SSH using `ssh_client.read_file()` or `scp -r`.
   * Saves to local destination, auto-creating directories (`os.makedirs`).
   * Updates `.workboard.json` entry.
   * Runs local Git commit: `git add {local_path} && git commit -m "Pulled {remote_path}"`.

3. **`push(local_path, commit_msg="Agent update")`**:
   * Reads local file content.
   * Writes file to mapped `remote_path` over SSH via `ssh_client.write_file()`.
   * Runs local Git commit: `git commit -am "{commit_msg}"`.

4. **`diff(local_path)`**:
   * If checking local edits: Runs `git diff {local_path}` locally.
   * If checking against remote: Downloads remote content to a temporary buffer and executes `git diff --no-index temp_remote_file local_path`.

5. **`status()`**:
   * Runs `git status --short` locally to detect uncommitted edits.
   * Checks `.workboard.json` timestamps against remote file `mtime` values.

---

### 4.3 Waveform & Visual Plotting Engine (`waveform_engine.py`)
* Converts simulation extraction logs (`.extract`, `.csv`, `.vcd`) into structured data frames.
* Uses `matplotlib` to render high-resolution PNG/SVG waveform charts into `./workboard/plots/`.
* Exposes visual chart artifacts directly to the user in the AI conversation interface.
* Optionally triggers local desktop GTKWave (`open -a GTKWave ...`) for interactive waveform analysis.

---

## 5. MCP Tool Schema (`workboard`)

Exposed to the AI agent in `server.py`:

```python
@mcp.tool()
def workboard(
    action: str,
    remote_path: str = "",
    local_path: str = "",
    work_dir: str = "./workboard",
    message: str = "Agent sync",
    recursive: bool = False,
    timeout: float = 60.0
) -> str:
    """
    Git-backed Local-Remote Workspace & Synchronization Tool for EDA Workflows.
    
    Actions:
      - 'initialize': Setup local Git-backed workboard directory mapped to remote EDA paths.
      - 'pull': Download remote file/folder to local workboard (supports renaming & recursive pull).
      - 'push': Upload local file to mapped remote server location and commit local Git repo.
      - 'diff': Display unified diff between local file version and remote server version.
      - 'status': List all tracked files and their Git/Sync status (LOCAL_MODIFIED, IN_SYNC, etc.).
      - 'plot': Generate visual waveform plot image artifact from local simulation outputs.
    """
```

---

## 6. End-to-End Simulation & Optimization Loop

```
       [USER / AGENT]                     [WORKBOARD BACKEND]                  [REMOTE EDA SERVER]
             │                                    │                                     │
 1. Initialize WorkBoard                          │                                     │
             ├───────────────────────────────────►│ Runs 'git init' locally             │
             │                                    │ Creates .workboard.json             │
             │                                    │                                     │
 2. Pull Netlist & PDK Model                      │                                     │
             ├───────────────────────────────────►│ Reads remote files over SSH ───────►│
             │                                    │◄── Returns file content ────────────┤
             │                                    │ Saves to netlists/inv_tb.cir        │
             │                                    │ Runs 'git add & git commit'         │
             │                                    │                                     │
 3. Local Optimization (Optuna/Agent)             │                                     │
             │ Modifies W/L parameters locally    │                                     │
             │                                    │                                     │
 4. Check Diff & Push                             │                                     │
             ├───────────────────────────────────►│ Runs 'git diff'                     │
             │                                    │ Writes updated file over SSH ──────►│
             │                                    │ Runs 'git commit -am Push'          │
             │                                    │                                     │
 5. Run Remote Simulation                         │                                     │
             ├─────────────────────────────────────────────────────────────────────────►│ Runs Eldo sim
             │                                                                          │ Generates .extract
             │                                    │                                     │
 6. Pull Results & Render Plot                    │                                     │
             ├───────────────────────────────────►│ Downloads .extract file ───────────►│
             │                                    │ Renders PNG Plot Artifact           │
             │◄───────────────────────────────────┤                                     │
 7. Visual Plot displayed in Chat Interface!      │                                     │
```

---

## 7. Edge Cases & Safeguards

1. **Large Waveform Files**: `.tr0`, `.wdb`, `.vcd` files are ignored by local `.gitignore`. They are downloaded on demand for plotting/viewing without bloating Git repository history.
2. **Local Renames (`mv`) and Deletions (`rm`)**: The backend SHA-256 checksum matching algorithm detects when a file was renamed locally and updates `.workboard.json` without losing remote mapping.
3. **Local Rollback**: If an AI agent edit breaks a simulation, the user can run `git checkout -- <file>` locally to instantly revert to the last working netlist.
