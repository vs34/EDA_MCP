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
pInst~>w = 2.0u  pInst~>l = 65n
nInst~>w = 1.0u  nInst~>l = 65n

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
