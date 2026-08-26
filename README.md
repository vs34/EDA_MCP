# EDA_MCP: Agentic EDA Control Plane & Intelligent Chip Design Workspace

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Protocol: FastMCP](https://img.shields.io/badge/Protocol-FastMCP-8A2BE2.svg)](https://modelcontextprotocol.io/)
[![Latency: <10ms](https://img.shields.io/badge/Latency-%3C10ms%20SSH-brightgreen.svg)]()
[![PDK: cmos065](https://img.shields.io/badge/PDK-cmos065%2065nm-blue.svg)]()
[![Autonomous Agents Ready](https://img.shields.io/badge/Agents-Antigravity%20%7C%20Cursor%20%7C%20Windsurf%20%7C%20Claude-orange.svg)]()

> **Transforming AI Coding Agents into Autonomous IC Design Engineers.**  
> `EDA_MCP` is a high-performance Model Context Protocol (MCP) server that connects local AI IDEs and agents (Antigravity, Cursor, Windsurf, Claude Desktop, Claude Code) directly to remote Linux EDA compute clusters executing Cadence Virtuoso and Siemens Eldo.

---

## 📹 Demo Video

<video src="https://github.com/user-attachments/assets/091cc42f-4188-4e31-8d5c-49ad20e18e45" autoplay loop muted playsinline controls width="100%"></video>

*(Video Source: [`doc/media/demo.mp4`](file:///Users/vs/function/EDA_MCP/doc/media/demo.mp4))*

💡 **Experiment & Solve Interview Problems**: Use `EDA_MCP` to experiment with custom circuits, run SPICE simulations, and solve real-world IC design interview questions.  
🎓 **Classic Interview Demo**: The demonstration video above showcases a classic hardware/IC design interview problem — constructing, CDL netlisting, and simulating a **depletion-load inverter** live inside Cadence Virtuoso and Siemens Eldo.

---

## 💡 Why EDA_MCP? Thoughtful Workspace Technology

Modern Integrated Circuit (IC) design demands high-performance Linux compute clusters hosting multi-gigabyte EDA tool suites (Cadence Virtuoso, Siemens Eldo) and proprietary PDKs (e.g. `cmos065`). However, AI developer tools and LLM agents operate locally inside modern IDEs.

`EDA_MCP` bridges this divide with an ultra-lightweight, resilient architecture built on 6 foundational pillars:

1. ⚡ **Sub-10ms SSH Multiplexing Engine**: Eliminates SSH handshake overhead by using persistent OpenSSH `ControlMaster` unix domain sockets and streaming file transport ([`ssh_client.py`](file:///Users/vs/function/EDA_MCP/ssh_client.py) & [`scp_client.py`](file:///Users/vs/function/EDA_MCP/scp_client.py)).
2. 🗂️ **Git-Backed WorkBoard Workspace (`workboard`)**: Local-remote workspace synchronizer that mirrors, tracks, versions, and computes unified line-by-line diffs for remote EDA files locally before pushing edits back to the cluster ([`workboard_client.py`](file:///Users/vs/function/EDA_MCP/workboard_client.py)).
3. 🎨 **Window-First Live GUI & Virtuoso IPC (`virtuoso`)**: Drives Cadence Virtuoso schematic and SKILL execution live inside an open GUI window or non-graphical session via named FIFO pipes (`MCP.command`) and IPC socket handlers ([`virtuoso_client.py`](file:///Users/vs/function/EDA_MCP/virtuoso_client.py)).
4. ⚡ **Interactive Eldo SPICE Engine (`eldo`)**: Manages continuous interactive SPICE REPL streams (`eldo -inter`), truncates logs, parses `.extract` measurement reports, and runs batch simulation decks ([`eldo_client.py`](file:///Users/vs/function/EDA_MCP/eldo_client.py)).
5. 📊 **PyQtGraph SPICE Waveform Oscilloscope**: Features [`eldo_plotter.py`](file:///Users/vs/function/EDA_MCP/eldo_plotter.py), a multi-pane interactive waveform visualizer supporting `.raw` and `.spi3` SPICE transient analysis files with linked time axes, dynamic signal legends, and crosshair readouts.
6. 🤖 **Autonomous Dual-Track Context Router (`eda-mcp-context-router`)**: Equips AI agents with strict domain specs ([`context/designer`](file:///Users/vs/function/EDA_MCP/context/designer/README.md) for circuit design & PDK rules, [`context/coder`](file:///Users/vs/function/EDA_MCP/context/coder/README.md) for server maintenance & GitHub PR workflows), plus an agent-to-agent bug reporting pipeline (`report_issue`).

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              LOCAL SYSTEM (Developer / AI Agent)                        │
│                                                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              EDA_MCP (FastMCP Server)                             │  │
│  │                                                                                   │  │
│  │   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   │  │
│  │   │  workboard    │   │   virtuoso    │   │     eldo      │   │remote_control │   │  │
│  │   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘   │  │
│  └───────────┼───────────────────┼───────────────────┼───────────────────┼───────────┘  │
└──────────────┼───────────────────┼───────────────────┼───────────────────┼──────────────┘
               │                   │                   │                   │
               │        OpenSSH ControlMaster Socket (Sub-10ms Latency)    │
               ▼                   ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              REMOTE EDA LINUX SERVER / CLUSTER                          │
│                                                                                         │
│  ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐ ┌──────────────┐  │
│  │  Git Workspace /   │ │  Cadence Virtuoso  │ │    Siemens Eldo    │ │ Process PDKs │  │
│  │  WorkBoard Sync    │ │  SKILL IPC FIFO    │ │   SPICE Simulator  │ │  (cmos065)   │  │
│  └────────────────────┘ └────────────────────┘ └────────────────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### IPC Data Flow Architectures

#### 🎨 Cadence Virtuoso Named Pipe FIFO Architecture
```
[Local Agent] ──> FastMCP (`virtuoso`) ──> SSH ──> FIFO Pipe `MCP.command` ──> `MCP_sockit.py` ──> Virtuoso CIW
                                                                                                    │
[Local Agent] <── FastMCP (`virtuoso`) <── SSH <── Reads `mcp_output.txt` <── evalstring() <────────┘
```

#### ⚡ Siemens Eldo Interactive SPICE Architecture
```
[Local Agent] ──> FastMCP (`eldo`) ──> SSH ──> FIFO Pipe `interactive.fifo` (Held open by `tail -f /dev/null`)
                                                              │
                                                              ▼
                                                   `eldo -inter` REPL
                                                              │
[Local Agent] <── FastMCP (`eldo`) <── SSH <── Reads `interactive_out.txt` <── Output Stream <───────┘
```

---

## 🚀 Tool Reference & Capabilities Matrix

`EDA_MCP` exposes 5 specialized tool modules via FastMCP:

| Tool Module | Key Actions | Description & Primary Use Case |
| :--- | :--- | :--- |
| **`workboard`** | `initialize`, `add`, `pull`, `push`, `export`, `diff`, `status`, `history` | **Workspace Synchronizer & Version Control.** Tracks remote EDA files in local Git repositories under `./workboard/<name>/`. Computes line-by-line unified diffs before updating remote server files. |
| **`virtuoso`** | `assisted_run`, `run`, `start_standalone`, `run_standalone`, `exit`, `run_terminal_command` | **Cadence Virtuoso SKILL Control.** Executes SKILL scripts live in Virtuoso GUI (`assisted_run`) or non-graphical session (`start_standalone`). Enforces PDK rules and `schCheck` `(0 0)` validation. |
| **`eldo`** | `start_interactive`, `run_interactive`, `run_script`, `visualize_waveforms`, `run_terminal_command` | **Siemens Eldo Simulation Engine.** Runs batch `.cir` simulations, streams interactive SPICE REPL commands, parses `.extract` metrics, and launches waveform plotting. |
| **`remote_control`**| `run_command`, `read_file`, `write_file` | **Stateful CSH Subshell Engine.** Executes terminal commands and inspects remote server files in persistent environment sessions (`/cadence/cshrc`). |
| **`report_issue`** | `report_issue` | **Autonomous Meta-Harness Reporter.** Agent-to-agent bug & feature request submission directly to GitHub with auto-attached execution logs, agent headers, and session IDs. |

---

## 🤖 Agent Directives & Dual-Track Context Routing

`EDA_MCP` includes the `eda-mcp-context-router` directive, enabling AI agents to autonomously inspect domain specifications before execution:

```text
                                 ┌───────────────────────────────┐
                                 │   AI AGENT (Task Intent)      │
                                 └───────────────┬───────────────┘
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                        ▼                                                 ▼
        [TRACK 1: CIRCUIT DESIGN & SIM]                   [TRACK 2: CODEBASE & MAINTENANCE]
        Inspect: context/designer/README.md               Inspect: context/coder/README.md
        - Tech PDK: cmos065 (65nm)                        - Branching: <agent>/issue-<id>-<desc>
        - Devices: psvtgp (PMOS), nsvtgp (NMOS)           - Custom Git Agent Author metadata
        - CDF Units: Width/Length as Micron strings       - Automated PR header generation
        - GUI: Window-First Execution                     - STRICT NO-AUTOMERGE policy
        - Validation: schCheck (0 0) required             - Test suite validation
```

* 📘 **Designer Context Guide**: [`context/designer/README.md`](file:///Users/vs/function/EDA_MCP/context/designer/README.md)
* 📙 **Coder Context Guide**: [`context/coder/README.md`](file:///Users/vs/function/EDA_MCP/context/coder/README.md)

---

## 🛠️ Installation & Setup

### 1. Requirements
* Python 3.10 or higher
* OpenSSH client on local system
* Remote Linux server access with Cadence Virtuoso and/or Siemens Eldo installed

### 2. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Setup Configuration
Copy and configure JSON config templates inside the [`config/`](file:///Users/vs/function/EDA_MCP/config) directory:
```bash
cp config/config_remote_control.json.template config/config_remote_control.json
cp config/config_virtuoso.json.template config/config_virtuoso.json
cp config/config_eldo.json.template config/config_eldo.json
cp config/config_scp.json.template config/config_scp.json
```

Example configuration ([`config/config_remote_control.json.template`](file:///Users/vs/function/EDA_MCP/config/config_remote_control.json.template)):
```json
{
  "ssh_host": "eda-uni",
  "ssh_config_path": "~/.ssh/config",
  "env_setup_cmd": "source /cadence/cshrc"
}
```

### 4. Enable SSH Connection Multiplexing (Sub-10ms Speeds)
Add the following snippet to your local `~/.ssh/config`:
```sshconfig
Host eda-uni
    HostName eda.university.edu
    User chip_designer
    ControlMaster auto
    ControlPath ~/.ssh/control-%r@%h:%p
    ControlPersist 15m
```

---

## 🔌 AI Client Configuration

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "eda-mcp": {
      "command": "python3",
      "args": [
        "/absolute/path/to/EDA_MCP/server.py"
      ]
    }
  }
}
```

### Antigravity IDE / Cursor / Windsurf
Add a Stdio MCP server entry:
* **Server Name**: `EDA_MCP`
* **Command**: `python3`
* **Args**: `/absolute/path/to/EDA_MCP/server.py`

### Claude Code CLI
```bash
claude mcp add eda-mcp -- python3 /absolute/path/to/EDA_MCP/server.py
```

---

## 📊 SPICE Waveform Visualizer (`eldo_plotter.py`)

`EDA_MCP` includes a high-performance PyQtGraph waveform oscilloscope for transient SPICE simulation analysis:

```bash
python3 eldo_plotter.py --file path/to/simulation.raw
```

**Features:**
- Multi-pane subplot rendering for voltage and current signals.
- Dynamic signal value labels following crosshairs in real time.
- Synchronized multi-pane X-axis zooming and panning.
- Automatic parse support for Eldo `.raw` and `.spi3` binary/ASCII formats.

---

## 📂 Repository Blueprint

| File / Directory | Description |
| :--- | :--- |
| [`server.py`](file:///Users/vs/function/EDA_MCP/server.py) | FastMCP server entrypoint & tool dispatch registry |
| [`workboard_client.py`](file:///Users/vs/function/EDA_MCP/workboard_client.py) | Git-backed workspace engine & `.workboard.json` tracking |
| [`virtuoso_client.py`](file:///Users/vs/function/EDA_MCP/virtuoso_client.py) | Cadence Virtuoso SKILL IPC pipe & REPL manager |
| [`eldo_client.py`](file:///Users/vs/function/EDA_MCP/eldo_client.py) | Siemens Eldo SPICE simulation REPL & `.extract` parser |
| [`eldo_plotter.py`](file:///Users/vs/function/EDA_MCP/eldo_plotter.py) | PyQtGraph SPICE waveform oscilloscope visualizer |
| [`ssh_client.py`](file:///Users/vs/function/EDA_MCP/ssh_client.py) | Low-level persistent SSH transport with `csh` sentinels |
| [`scp_client.py`](file:///Users/vs/function/EDA_MCP/scp_client.py) | OpenSSH high-speed binary file transfer engine |
| [`issue_reporter.py`](file:///Users/vs/function/EDA_MCP/issue_reporter.py) | Meta-harness autonomous GitHub issue reporter |
| [`config/`](file:///Users/vs/function/EDA_MCP/config) | Configuration templates for SSH and tool setups |
| [`context/designer/`](file:///Users/vs/function/EDA_MCP/context/designer/README.md) | Operational specs for circuit design, PDK, and simulations |
| [`context/coder/`](file:///Users/vs/function/EDA_MCP/context/coder/README.md) | Operational specs for server maintenance & PR workflows |
| [`doc/`](file:///Users/vs/function/EDA_MCP/doc/architecture_and_gotchas.md) | Deep-dive technical architecture and gotchas guides |
| [`tests/`](file:///Users/vs/function/EDA_MCP/tests) | Comprehensive unit and integration test suite |

---

## 🧪 Testing & Verification

Run the unit test suite:
```bash
python3 -m unittest discover tests
```
or with `pytest`:
```bash
pytest tests/
```

---

## 📜 Contributing & License

* 🤝 **Contributing & Agent Guidelines**: See [`CONTRIBUTING.md`](file:///Users/vs/function/EDA_MCP/CONTRIBUTING.md) for full Designer & Coder AI Agent contribution directives.
* 📜 Distributed under the **MIT License**. See [`LICENSE`](file:///Users/vs/function/EDA_MCP/LICENSE) for details.
