---
name: eda-mcp-virtuoso
description: Best practices, workflow patterns, and SKILL automation guidelines for controlling Cadence Virtuoso via eda-mcp server.
---

# Cadence Virtuoso Automation Guide (eda-mcp)

This skill provides operational patterns, conventions, and SKILL code templates for interacting with Cadence Virtuoso using the `eda-mcp` MCP server.

---

## 1. Core Operating Guidelines

### Dedicated Tool Terminal Sessions & Execution Rules
- **Isolated Terminal Instances:** The `eda-mcp` server manages separate, dedicated persistent SSH terminal sessions per tool:
  - **Virtuoso Session:** Dedicated SSH shell for Cadence Virtuoso (`virtuoso_session`).
  - **Eldo Session:** Dedicated SSH shell for Siemens Eldo simulator (`eldo_session`).
  - **Remote Control Session:** Separate general-purpose SSH shell (`remote_session`).
- **Use `run_terminal_command` for Tool-Specific Shell Execution:**
  - Use `virtuoso(action="run_terminal_command", command="...")` to run shell commands in the **exact same terminal and environment** where Virtuoso operates.
  - Use `eldo(action="run_terminal_command", command="...")` to run shell commands in the **exact same terminal and environment** where Eldo simulations run.
- **Use `remote_control` for File I/O Operations:** Always use `remote_control(action="read_file", path="...")` and `remote_control(action="write_file", path="...", content="...")` when reading or writing files on the remote EDA server. Avoid using raw shell commands (`cat`, `echo`, `vi`) via terminal commands for file I/O.
- **AVOID using `remote_control` for Tool Execution:** Do NOT use `remote_control(action="run_command")` for running Virtuoso or Eldo shell tasks. `remote_control` runs in a separate general SSH shell and does not share working directory state (`cd`) or environment variables with the dedicated tool terminals.

### Library Scope
- All user cellviews, test structures, schematics, and layouts created or managed through `eda-mcp` MUST be placed in the **`MCP`** library unless explicitly instructed otherwise by the user.

### Tool Initialization & Execution Modes
- **Standalone Mode (`start_standalone` / `standalone`):**
  - Uses non-graphical Virtuoso (`virtuoso -nograph`). Recommended for batch SKILL scripts, CDF parameter updates, and netlist extractions. Bypasses GUI modal dialogs and avoids 10s execution timeouts.
- **Assisted Run Mode (`assisted_run`):**
  - Used for interacting directly with the active graphical Cadence Virtuoso editor window.
- **Before executing SKILL code:**
  - Verify Virtuoso is initialized. If timed out, run `virtuoso(action="initialize", work_dir="~/Desktop/cmos65")`.

### Explicit `cds.lib` Technology Resolution
- If Virtuoso emits `DB-270172` (`Failed to open cellview cmos065/psvtgp/symbol`), ensure `cds.lib` includes explicit absolute library paths:
  ```text
  DEFINE analogLib /cadence/IC618/tools/dfII/etc/cdslib/artist/analogLib
  DEFINE basic     /cadence/IC618/tools/dfII/etc/cdslib/basic
  DEFINE cmos065   /usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/LIB/lib/OpenAccess/cmos065
  DEFINE MCP       /home/vaibhav22555/Desktop/cmos65/MCP
  ```

### SKILL File Stream Flushing Rule (`drain` + `close`)
- When writing netlists or text files via SKILL `outfile(...)`, **always** execute `drain(fileId)` before `close(fileId)`. This forces Cadence to flush RAM buffers to the server disk instantly and prevents empty (0-byte) netlist files.

### Eldo Simulator Integration & Netlist Rules
- **Circuit Title Line:** Line 1 of an Eldo `.cir` netlist MUST be an explicit title line (Eldo treats Line 1 as a title comment).
- **Level-1 Model Fallback:** If full BSIM4 SSIM model decks are unlinked, use Eldo-compatible MOS model cards:
  ```spice
  .MODEL nsvtgp NMOS (LEVEL=1 VTO=0.38 KP=150u TOX=1.85n)
  .MODEL psvtgp PMOS (LEVEL=1 VTO=-0.36 KP=50u TOX=1.85n)
  ```
- **Interactive Simulation:** Initialize `eldo`, run `start_interactive(command="...")`, send `run`, then `step` via `run_interactive` to complete DC/transient sweeps.

### Timeout Management
- SKILL execution calls have a configurable execution timeout window (default 30s).
- Keep SKILL commands modular and short. Avoid unhandled blocking loops or modal dialog prompts.

---

## 2. Technology & Process Context (`cmos065`)

- **Process Technology:** `cmos065` ($65\text{nm}$ LP/GP CMOS process, 7M4X0Y2Z metallization option).
- **Core Transistors:**
  - PMOS (SVT): `cmos065` / `psvtgp`
  - NMOS (SVT): `cmos065` / `nsvtgp`
- **Pin & Symbol Libraries:**
  - Input Pin: `basic` / `ipin` (`symbol`)
  - Output Pin: `basic` / `opin` (`symbol`)
  - Input/Output Pin: `basic` / `iopin` (`symbol`)
- **Transistor Terminals:** Source (`s`), Drain (`d`), Gate (`g`), Bulk (`b`).

---

## 3. SKILL Automation Guidelines

### A. Schematic Creation Pattern
Always open schematic cellviews in append (`"a"`) or write (`"w"`) mode, place instances, create pins, connect nets, extract/check, and save.

```lisp
cv = dbOpenCellViewByType("MCP" "<cellName>" "schematic" "schematic" "a")

;; Clear existing objects if starting fresh
foreach(inst cv~>instances dbDeleteObject(inst))
foreach(shape cv~>shapes dbDeleteObject(shape))
foreach(net cv~>nets dbDeleteObject(net))
foreach(term cv~>terminals dbDeleteObject(term))

;; Place Instances
pInst = dbCreateInstByMasterName(cv "cmos065" "psvtgp" "symbol" "I0" list(1.0 1.5) "R0")
nInst = dbCreateInstByMasterName(cv "cmos065" "nsvtgp" "symbol" "I1" list(1.0 0.5) "R0")

;; Place Pins
ip  = dbOpenCellViewByType("basic" "ipin" "symbol")
op  = dbOpenCellViewByType("basic" "opin" "symbol")
iop = dbOpenCellViewByType("basic" "iopin" "symbol")
schCreatePin(cv ip  "vin"  "input"       nil list(-0.5 1.0) "R0")
schCreatePin(cv op  "vout" "output"      nil list( 2.5 1.0) "R0")
schCreatePin(cv iop "vdd"  "inputOutput" nil list( 1.25 2.5) "R0")
schCreatePin(cv iop "gnd"  "inputOutput" nil list( 1.25 -0.5) "R0")

;; Wire Interconnects & Connect Body Terminals
;; Use schCreateWire for visual wires and dbCreateConnByName for explicit net connections
net_vdd = dbMakeNet(cv "vdd")
net_gnd = dbMakeNet(cv "gnd")
dbCreateConnByName(net_vdd pInst "b")
dbCreateConnByName(net_gnd nInst "b")

;; Check & Save
schCheck(cv)
dbSave(cv)
```

### B. Layout Creation Pattern
- **Layout Layers:**
  - Poly: `("PO" "drawing")`, `("PO" "pin")`, `("PO" "label")`
  - Metal1: `("M1" "drawing")`, `("M1" "pin")`, `("M1" "label")`
- Place layout masters: `dbCreateInstByMasterName(cv "cmos065" "psvtgp" "layout" ...)`
- Add layout pins using `dbCreatePin(net pinShape pinName)` and matching `dbCreateLabel`.

```lisp
cv = dbOpenCellViewByType("MCP" "<cellName>" "layout" "maskLayout" "w")

;; Place layout instances
pInst = dbCreateInstByMasterName(cv "cmos065" "psvtgp" "layout" "I0" list(0.0 3.0) "R0")
nInst = dbCreateInstByMasterName(cv "cmos065" "nsvtgp" "layout" "I1" list(0.0 0.0) "R0")

;; Draw interconnect geometries
dbCreateRect(cv list("PO" "drawing") list(list(0.0 0.0) list(0.06 3.0)))
dbCreateRect(cv list("M1" "drawing") list(list(0.115 0.0) list(0.205 3.15)))

;; Add layout pins & labels
net_vin = dbMakeNet(cv "vin")
r_vin   = dbCreateRect(cv list("PO" "pin") list(list(-0.1 1.4) list(0.0 1.6)))
dbCreatePin(net_vin r_vin "vin")
dbCreateLabel(cv list("PO" "label") list(-0.05 1.5) "vin" "centerCenter" "R0" "roman" 0.1)

dbSave(cv)
```

---

## 4. Verification & Simulation Procedures

### Verification (DRC & LVS)
- **Cellview Marker Inspection:** Check `cv~>markers` for layout violations.
- **Calibre Decks Location:** Rule decks are stored under `/usr/local/cmos065_536/.../DATA/CALIBRE_CORE` and `DATA/LVS`.

### Simulation Setup (ADE L / Spectre)
- **Spectre Corner Models:** `/usr/local/cmos065_536/.../DATA/SPECTRE/CORNERS/svtgp.scs` (`tt` corner).
- Launch ADE L session: `sevStartSession(?lib "MCP" ?cell "<cellName>" ?view "schematic")`.

---

## 5. WorkBoard Local-Remote Sync Guidelines (`workboard`)

The `workboard` tool manages isolated local Git repositories (`./workboard/<name>/`) mapped to remote EDA server paths:

### Action Usage Patterns & Best Practices
- **`initialize(workboard_name="...", local_dir="./workboard")`**:
  - Creates clean local workspace `./workboard/<workboard_name>/` and runs `git init`. Sets active memory workspace. Does NOT pull remote files on init.
- **`add(remote_path="...", local_path="...")`**:
  - Downloads file/folder from remote EDA server over SSH using binary-safe transfer (`read_file_bytes`).
  - Saves to local WorkBoard path, records `last_sync_commit` baseline SHA and timestamp in `.workboard.json`, and commits to local Git.
- **`pull(local_path="...")`**:
  - Re-fetches latest version of an added file from remote server to update local WorkBoard, commits to local Git, and advances `last_sync_commit` baseline.
- **`push(local_path="...", message="...")`**:
  - Uploads local file edits back to mapped remote server path over SSH, commits to local Git, and advances `last_sync_commit` baseline.
- **`diff(local_path="...")`**:
  - Fetches live remote server file over SSH and compares line-by-line with local file.
  - **Auto-Advance Feature**: If local and remote files are **100% identical**, `diff` automatically advances `last_sync_commit` in `.workboard.json` to the current local Git HEAD commit! If files differ, returns unified line-by-line diff.
- **`status()`**:
  - Reports file-wise summary showing mapped remote path, last synced commit baseline SHA ($C_{\text{sync}}$) & timestamp, and local Git state.

### Native Git Integration & Navigation Rules
- **Built on Git Backend:** The `workboard` tool is powered by an underlying local Git repository (`./workboard/<name>/`). Every sync action (`add`, `pull`, `push`, `diff`) automatically executes `git add`, `git commit`, and manages `last_sync_commit` baselines.
- **Use Native Git Commands for History & Navigation:**
  - `workboard` is designed to be used **hand-in-hand with native Git commands**.
  - You may run native Git terminal commands inside `./workboard/<name>/` for advanced file navigation, version inspection, and rollbacks:
    - `git log -n 10 --oneline -- <local_path>`: Inspect exact commit history for a specific file.
    - `git show <commit_sha>:<local_path>`: View exact file content at a past sync baseline.
    - `git checkout <commit_sha> -- <local_path>`: Roll back a file to any past verified sync commit.
    - `git diff <commit_sha_1> <commit_sha_2> -- <local_path>`: Compare changes across historical sync baselines.

