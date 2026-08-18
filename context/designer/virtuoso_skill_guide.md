# VIRTUOSO_SKILL_AUTOMATION_SPEC

## 1. PDK Technology Map (`cmos065`)
- **Technology**: $65\text{nm}$ LP/GP CMOS (7M4X0Y2Z metal stack option)
- **Cellview Masters Table**:
  | Logic Element | Library Name | Cell Name | View Name | Terminals / Pins |
  | :--- | :--- | :--- | :--- | :--- |
  | SVT PMOS | `cmos065` | `psvtgp` | `symbol`, `layout` | `d`, `g`, `s`, `b` |
  | SVT NMOS | `cmos065` | `nsvtgp` | `symbol`, `layout` | `d`, `g`, `s`, `b` |
  | Input Pin | `basic` | `ipin` | `symbol` | `vin` |
  | Output Pin | `basic` | `opin` | `symbol` | `vout` |
  | In/Out Pin | `basic` | `iopin` | `symbol` | `vdd`, `gnd` |

---

## 2. Explicit `cds.lib` Schema
```text
DEFINE analogLib /cadence/IC618/tools/dfII/etc/cdslib/artist/analogLib
DEFINE basic     /cadence/IC618/tools/dfII/etc/cdslib/basic
DEFINE cmos065   /usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/LIB/lib/OpenAccess/cmos065
DEFINE MCP       /home/vaibhav22555/Desktop/cmos65/MCP
```

---

## 3. SKILL Code Synthesis Templates

### Template A: Schematic Instantiation & Connectivity
```lisp
cv = dbOpenCellViewByType("MCP" "<cellName>" "schematic" "schematic" "a")

;; Reset cellview if overwriting
foreach(inst cv~>instances dbDeleteObject(inst))
foreach(shape cv~>shapes dbDeleteObject(shape))
foreach(net cv~>nets dbDeleteObject(net))
foreach(term cv~>terminals dbDeleteObject(term))

;; Transistor Placement
pInst = dbCreateInstByMasterName(cv "cmos065" "psvtgp" "symbol" "I0" list(1.0 1.5) "R0")
nInst = dbCreateInstByMasterName(cv "cmos065" "nsvtgp" "symbol" "I1" list(1.0 0.5) "R0")

;; Transistor CDF Lifecycle & Sizing (MUST use string Micron values: "2.0", "0.065")
;; Do NOT assign raw float meters (pInst~>w = 2.0u), as this bypasses CDF callbacks and truncates dimensions to 0.
initMosTransistor(pInst "2.0" "0.065")  ;; 2.0µm width, 65nm length
initMosTransistor(nInst "1.0" "0.065")  ;; 1.0µm width, 65nm length

;; Pin Placement
ip  = dbOpenCellViewByType("basic" "ipin" "symbol")
op  = dbOpenCellViewByType("basic" "opin" "symbol")
iop = dbOpenCellViewByType("basic" "iopin" "symbol")
schCreatePin(cv ip  "vin"  "input"       nil list(-0.5 1.0) "R0")
schCreatePin(cv op  "vout" "output"      nil list( 2.5 1.0) "R0")
schCreatePin(cv iop "vdd"  "inputOutput" list( 1.25 2.5) "R0")
schCreatePin(cv iop "gnd"  "inputOutput" list( 1.25 -0.5) "R0")

;; Net Connectivity
net_vdd = dbMakeNet(cv "vdd")
net_gnd = dbMakeNet(cv "gnd")
dbCreateConnByName(net_vdd pInst "b")
dbCreateConnByName(net_gnd nInst "b")

;; Zero-Warning Validation
schCheck(cv)
dbSave(cv)
```

### Template B: SKILL File Output Buffer Flush
```lisp
fp = outfile("output.net" "w")
fprintf(fp "Netlist Header\n")
drain(fp) ;; MUST EXECUTE DRAIN BEFORE CLOSE
close(fp)
```

### Template C: Displaying Schematic/Layout in Virtuoso GUI Window (`assisted_run`)
```lisp
;; Use in assisted_run when user requests creating, opening, or viewing a schematic/layout in the Virtuoso GUI window!

;; 1. Open/create cellview database object
cv = dbOpenCellViewByType("MCP" "<cellName>" "schematic" "schematic" "a")

;; ... (Instantiate transistors, pins, nets, run schCheck(cv), and dbSave(cv)) ...
schCheck(cv)
dbSave(cv)

;; 2. Open & display cellview in the live Virtuoso GUI window (guarded against duplicate window spawns)
;; CRITICAL: Use geGetCellViewWindow check to prevent duplicate windows. Do NOT call dbClose(cv) when displaying in GUI!
unless( geGetCellViewWindow(cv)
    geOpen(?lib "MCP" ?cell "<cellName>" ?view "schematic" ?viewType "schematic" ?mode "a")
)
```

---

## 4. GUI Window Opening vs. Background Batch Execution

| Execution Mode | Tool Action | Required SKILL Functions | Window / Close Rule |
| :--- | :--- | :--- | :--- |
| **Interactive GUI Mode** | `virtuoso(action="assisted_run")` | `dbOpenCellViewByType`, `schCheck`, `dbSave`, `unless(geGetCellViewWindow ... geOpen)` | **MUST guard `geOpen` with `geGetCellViewWindow(cv)`** to prevent duplicate window spawns. **DO NOT call `dbClose(cv)`**. |
| **Background Batch Mode** | `virtuoso(action="standalone")` / `run_script` | `dbOpenCellViewByType`, `schCheck`, `dbSave`, `dbClose(cv)` | Performs database editing in memory. Must call `dbClose(cv)` to release lock. |

---

## 5. Local Tooling & Computation Authorization
- Agents may freely use all local system tools (Python scripts, NumPy, SymPy, local scratch files, web research, math solvers) to compute transistor dimensions ($W/L$), gain-bandwidth product allocations, bias currents, node voltages, or netlist topologies locally before synthesizing SKILL scripts or launching remote EDA commands.

---

## 6. `assisted_run` Command Length & Error Trapping Spec
- **Length Constraint**: Keep `assisted_run` SKILL `command` strings short and modular.
- **Error Trapping (`errset`)**: Server `MCP_setup.il` automatically traps unhandled SKILL errors via `errset` and `unwindProtect` (preventing 30s timeouts). Agents may also use `errset(expr t)` inside SKILL commands to capture detailed diagnostic messages for self-healing.
- **GUI Window Display**: When asked to open or build a schematic, use `geOpen(...)` so the window appears on the user's remote Virtuoso display.
- **GUI Popup Notification**: `assisted_run` executes against the active graphical Virtuoso window. If a command opens a modal GUI popup window (e.g., save prompt, geOpen dialog, schCheck warning popup), the agent MUST explicitly notify the user to inspect and interact with the remote GUI popup.
