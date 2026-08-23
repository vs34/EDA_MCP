# ELDO_SIMULATION_SPEC

## 1. SPICE Netlist Syntax & Core Invariants

- **Rule 1 (Title Line)**: Line 1 of every `.cir` simulation deck is strictly treated as a title comment line. Always start line 1 with a descriptive comment (e.g. `* Inverter Transient Simulation Deck`).
- **Rule 2 (Model Fidelity & Wrapper Architecture)**:
  Cadence Virtuoso CDL (`auCdl`) netlists can export PDK-specific CDF parameters (`nfing=1 sense=0 ngcon=1 m=1 accurateFlow=0`) and unit-less dimensions (`w=2.0 l=0.065`). Native SPICE MOS primitives (`M...`) can reject these extra parameters.
  - An `X...` instance needs a compatible `.SUBCKT` definition to absorb those parameters.
  - A process-corner include alone does **not** create that wrapper or make an arbitrary Level-1 model PDK-accurate.
  - For PDK-corner simulation, inspect the selected corner deck and use its verified wrapper/model interface. Do not define a same-named wrapper until you know that it does not collide with a deck-defined model or subcircuit.
  - The wrapper below is a **Level-1 syntax smoke-test example only**. It validates parsing and connectivity; it is not suitable for sizing, corner comparison, or signoff.
  ```spice
  * Standard 65nm Subcircuit Wrappers for Eldo (absorbing Cadence CDF parameters)
  .SUBCKT psvtgp d g s b w=2.0 l=0.065 nfing=1 sense=0 ngcon=1 m=1 accurateFlow=0
  M0 d g s b psvtgp_core W='w*1u' L='l*1u' M='m'
  .ENDS

  .SUBCKT nsvtgp d g s b w=1.0 l=0.065 nfing=1 sense=0 ngcon=1 m=1 accurateFlow=0
  M0 d g s b nsvtgp_core W='w*1u' L='l*1u' M='m'
  .ENDS

  .MODEL psvtgp_core PMOS (LEVEL=1 VTO=-0.36 KP=50u TOX=1.85n)
  .MODEL nsvtgp_core NMOS (LEVEL=1 VTO=0.38 KP=150u TOX=1.85n)
  ```
  Do not extrapolate this wrapper to LP or other device variants: inspect the selected PDK deck for the correct names and parameters.
- **Rule 3 (Immutable Netlist Principle)**:
  **NEVER manually edit or sanitize the structural netlist (`<cellName>.net`) exported from Virtuoso.**
  The structural netlist is immutable. All parameter handling, unit scaling, and PDK subcircuit definitions must reside in the **simulation configuration deck (`<cellName>.cir`)** or model include files.
- **Rule 4 (Instance Prefix Hierarchy)**:
  - `X...`: Subcircuit instantiation (used in testbenches to instantiate circuit cells, e.g. `X1 IN OUT VDD VSS inverter`, and for subcircuit transistors `XM0`, `XM1`).
  - `M...`: Built-in native SPICE primitive transistor.
- **Rule 5 (PDK Process Corner Decks at `/modelfile_65nm/`)**:
  Process corner decks for 65nm simulations reside on the remote server at `/modelfile_65nm/`. Agents should include the required corner file using `.INCLUDE "/modelfile_65nm/<corner_file>.cir"`:
  - **TT (Typical NMOS, Typical PMOS)**: `.include "/modelfile_65nm/typNtypP.cir"` (or `typNtypP_new.cir`)
  - **SS (Slow NMOS, Slow PMOS)**: `.include "/modelfile_65nm/minNminP.cir"`
  - **FF (Fast NMOS, Fast PMOS)**: `.include "/modelfile_65nm/maxNmaxP.cir"`
  - **FS (Fast NMOS, Slow PMOS)**: `.include "/modelfile_65nm/maxNminP.cir"`
  - **SF (Slow NMOS, Fast PMOS)**: `.include "/modelfile_65nm/minNmaxP.cir"`
  - **Auxiliary Decks**: `/modelfile_65nm/diode_typ.cir` (diode typical), `/modelfile_65nm/diode_fast.cir`, `/modelfile_65nm/diode_slow.cir`, `/modelfile_65nm/resistor.cir` (resistors), `/modelfile_65nm/no_mismatch.cir` (no mismatch).
  Select exactly one transistor process corner for a simulation unless the experiment explicitly requires multiple corners. Including a corner file is necessary but not sufficient: verify its device interface before calling the result PDK-accurate.

---

## 2. Standard 2-File Architecture

Eldo simulation in EDA-MCP is structured around two distinct files:

```text
┌────────────────────────────────────────────────────────────────────────────────┐
│ 1. Structural Netlist (<cellName>.net)                                         │
│    Exported directly from Cadence Virtuoso schematic via transCdlOutForm.      │
│    Contains: .SUBCKT <cellName> ... transistor interconnects ... .ENDS         │
│    Status: IMMUTABLE (do not alter parameters or hand-edit).                   │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │ .INCLUDE "<cellName>.net"
┌──────────────────────────────────────▼─────────────────────────────────────────┐
│ 2. Simulation Configuration Deck (<cellName>.cir)                              │
│    Authored locally in WorkBoard by agent.                                     │
│    Contains: Model subcircuits, .INCLUDE, X1 instantiation, supplies, analysis.│
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Reference Sample Files

### Sample A: Raw Cadence Virtuoso Netlist (`inverter.net`)
```spice
************************************************************************
* auCdl Netlist:
* Library Name:  MCP
* Top Cell Name: inverter
* View Name:     schematic
* Netlisted on:  Aug 22 15:44:47 2026
************************************************************************
.PARAM

************************************************************************
* Library Name: MCP
* Cell Name:    inverter
* View Name:    schematic
************************************************************************
.SUBCKT inverter IN OUT VDD VSS
*.PININFO IN:I OUT:O VDD:B VSS:B
XM0 OUT IN VDD VDD psvtgp w=2.0 l=0.065 nfing=1 sense=0 ngcon=1 m=1 
+ accurateFlow=0
XM1 OUT IN VSS VSS nsvtgp w=1.0 l=0.065 nfing=1 sense=0 ngcon=1 m=1 
+ accurateFlow=0
.ENDS
```

### Sample B: Level-1 Syntax Smoke-Test Deck (`tb_inverter_smoke.cir`)
```spice
* Inverter syntax smoke test — NOT PDK-accurate
.OPTION POST=1
.OPTION ASCII=1
.OPTION SPI3ASC=1

* 1. Approximate wrappers; do not combine with a same-named PDK wrapper/model.
.SUBCKT psvtgp d g s b w=2.0 l=0.065 nfing=1 sense=0 ngcon=1 m=1 accurateFlow=0
M0 d g s b psvtgp_core W='w*1u' L='l*1u' M='m'
.ENDS

.SUBCKT nsvtgp d g s b w=1.0 l=0.065 nfing=1 sense=0 ngcon=1 m=1 accurateFlow=0
M0 d g s b nsvtgp_core W='w*1u' L='l*1u' M='m'
.ENDS

.MODEL psvtgp_core PMOS (LEVEL=1 VTO=-0.36 KP=50u TOX=1.85n)
.MODEL nsvtgp_core NMOS (LEVEL=1 VTO=0.38 KP=150u TOX=1.85n)

* 2. Include Structural Netlist from Virtuoso
.INCLUDE "inverter.net"

* 3. Instantiate Subcircuit under Test (X1)
X1 IN OUT VDD VSS inverter

* 4. Power Supplies & Input Stimulus
VVDD VDD 0 DC 1.2
VVSS VSS 0 DC 0.0
VIN  IN  0 PULSE(0.0 1.2 0.5n 0.05n 0.05n 1.0n 2.0n)
CL   OUT 0 10fF

* 5. Simulation Analysis
.TRAN 0.005n 4.0n

* 6. Minimal Signal Output Probes
.PRINT TRAN V(IN) V(OUT)
.PLOT TRAN V(IN) V(OUT)
.PROBE TRAN V(IN) V(OUT)
.END
```

### PDK-Corner Deck Template (`tb_inverter_tt.cir`)

Use this structure only after inspecting the selected corner deck and identifying its compatible device wrapper/model interface. `<verified-pdk-wrapper-or-model-include>` is intentionally a placeholder; do not replace it with the Level-1 definitions above.

```spice
* Inverter TT-corner deck — complete only after verifying PDK device interface
.INCLUDE "/modelfile_65nm/typNtypP.cir"
.INCLUDE "<verified-pdk-wrapper-or-model-include>"
.INCLUDE "inverter.net"
X1 IN OUT VDD VSS inverter
VVDD VDD 0 DC 1.2
VVSS VSS 0 DC 0
VIN IN 0 PULSE(0 1.2 0.5n 0.05n 0.05n 1n 2n)
CL OUT 0 10f
.TRAN 0.005n 4n
.PRINT TRAN V(IN) V(OUT)
.END
```

For VTC, create a separate `tb_inverter_vtc.cir` with the same **verified** model/wrapper, structural-netlist, and supply sections. Replace the input and the complete transient analysis/output block with:

```spice
VIN IN 0 DC 0
.DC VIN 0 1.2 0.01
.PRINT DC V(IN) V(OUT)
```

Use broad probes such as `.PROBE V(*)`, `.PROBE V(X1.*)`, or `.PROBE I(*)` only for a focused debug run: they can create unnecessarily large output files.

### Sample C: Annotated Eldo Output Listing (`inverter.chi`)
```text
  Run on edatools-server2.iiitd.edu.in (Linux 2.6.32-754.35.1.el6.x86_64)

/mentor/AMS/aol/bin/eldo_64.exe -i tb_inverter_smoke.cir

***** PRE-PROCESSING ...
***** ANALYSIS ....
***** 0  error(s). 0  warning(s). 

***** GENERATION ...
***** 0  error(s). 0  warning(s). 

INFORMATION ABOUT COMPILATION
Memory space allocated (MB):    242
5 elements
4 nodes
3 input signals

Eldo VERSION : ELDO 12.2 (64 bits)
*** TITLE: * Inverter syntax smoke test — NOT PDK-accurate
TEMPERATURE : 27.000000 degrees C

Performing DC analysis...
   TOTAL POWER DISSIPATION:  3.2112E-08 WATTS

Compute from 0.000000 Nano to 4.000000 Nano
Simulation progress                : 100% (t = 4.0000 N)
***> Current simulation completed

SIMULATION INFORMATION 
memory size allocated in Mbytes  245.2
nb of components: 6
nb of nodes: 4
Number of steps computed: 74

***> CPU TIME 0s 020ms <***
***> MESSAGE SUMMARY: 0 errors, 0 warnings
***> GLOBAL ELAPSED TIME 2s <***
```

---

## 4. Execution Modes

### Mode 1: Interactive REPL Simulation (`start_interactive` & `run_interactive`)
- Starts from the completed `tb_<cell>.cir` testbench, which includes the exported `<cellName>.net` structural netlist.
- The agent sends interactive commands directly into the REPL terminal (`run`, `step`, parameter sweeps, print commands) to observe real-time simulation output.

### Mode 2: Batch Script Simulation (`run_script` / `run_terminal_command`)
- Authored locally inside WorkBoard, reviewed, exported to server, and executed via:
  ```json
  {
    "tool": "eldo",
    "arguments": {
      "action": "run_script",
      "command": "tb_inverter_smoke.cir",
      "work_dir": "~/Desktop/eldo"
    }
  }
  ```

---

## 5. Post-Simulation Output Retrieval & Analysis

1. **Download Output Files via WorkBoard**:
   - Use `workboard(action="add", remote_path="~/Desktop/eldo/<cellName>.chi")` or `workboard(action="add", remote_path="~/Desktop/eldo/<cellName>.spi3")`.
2. **Local Output Analysis**:
   - Parse `.chi` text output locally to calculate DC operating points, transient delays ($t_{pHL}, t_{pLH}$), switching threshold ($V_M$), noise margins ($NM_L, NM_H$), and small-signal gain without running remote shell probes.

---

## 6. Waveform Visualization (`visualize_waveforms`)

To render simulation results in an interactive oscilloscope window for the user, invoke `eldo(action="visualize_waveforms", ...)` on the `.raw` or `.spi3` simulation output file.

```json
{
  "tool": "eldo",
  "arguments": {
    "action": "visualize_waveforms",
    "file_path": "<workboard-root>/inverter_tran.spi3",
    "layout": [
      {
        "pane_title": "Logic Waveforms",
        "signals": ["V(IN)", "V(OUT)"]
      }
    ]
  }
}
```

Replace `<workboard-root>` with the local path returned by the WorkBoard operation; never copy a path from another agent host.
