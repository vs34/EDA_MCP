---
name: eda-mcp-virtuoso
description: Best practices, workflow patterns, and SKILL automation guidelines for controlling Cadence Virtuoso via eda-mcp server.
---

# Cadence Virtuoso Automation Guide (eda-mcp)

This skill provides operational patterns, conventions, and SKILL code templates for interacting with Cadence Virtuoso using the `eda-mcp` MCP server.

---

## 1. Core Operating Guidelines

### Library Scope
- All user cellviews, test structures, schematics, and layouts created or managed through `eda-mcp` MUST be placed in the **`MCP`** library unless explicitly instructed otherwise by the user.

### Tool Initialization
- Before executing SKILL code with `virtuoso(action="run", ...)`:
  - Verify Virtuoso is initialized.
  - If not initialized or if session timed out, run `virtuoso(action="initialize", work_dir="~/Desktop/cmos65")`.
  - Default working directory containing environment scripts: `~/Desktop/cmos65`.

### Timeout Management
- SKILL execution calls have a short execution timeout window (10–30s).
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
