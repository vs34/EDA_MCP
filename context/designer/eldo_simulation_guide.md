# ELDO_SIMULATION_SPEC

## 1. SPICE Netlist Syntax & Core Invariants

- **Rule 1 (Title Line)**: Line 1 of every `.cir` simulation deck is strictly treated as a title comment line. Always start line 1 with a descriptive comment (e.g. `* Inverter Transient Simulation Deck`).
- **Rule 2 (Model Fidelity and CDL Interface)**:
  Cadence CDL adds the MOS SPICE element prefix during export. Schematic instance naming does not control that prefix.
  - Inspect the exported netlist before writing the testbench: record the MOS line format, subcircuit pin order, and parameters present.
  - Preserve `<cellName>.net` as the original CDL export. For the Eldo wrapper flow, prepare a separate simulation copy whose MOS element prefix is transformed from `M` to `X`; the `X...` calls then use compatible testbench wrappers.
  - Transform only the leading element letter of MOS instance lines. Do not perform a global text replacement, and never overwrite the original export.
  - Example, run in the Eldo work directory after export:
    ```text
    sed 's/^M/X/' <cellName>.net > <cellName>_eldo.net
    ```
  - A process-corner include does not automatically create wrappers or make a raw export compatible with Eldo. Use the wrapper/model interface verified for the selected PDK corner.
- **Rule 3 (Immutable Netlist Principle)**:
  **Never overwrite or hand-edit the original structural netlist (`<cellName>.net`) exported from Virtuoso.**
  When a prefix transformation is required, create and track a derived simulation copy (`<cellName>_eldo.net`) with the exact leading-prefix transformation above. Keep wrapper definitions, model includes, and analyses in the simulation configuration deck (`<cellName>.cir`) or its model include files.
- **Rule 4 (SPICE Prefixes)**:
  - `X...`: A subcircuit call, used by the testbench to instantiate the exported cell, for example `X1 IN OUT VDD VSS inverter`.
  - `M...`: A native MOS primitive. Its prefix is assigned by the CDL exporter; it is not controlled by the Virtuoso schematic instance name.
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
│    Status: PRESERVE as the immutable original export.                          │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │ generate `<cellName>_eldo.net` if wrapper flow is required
┌──────────────────────────────────────▼─────────────────────────────────────────┐
│ 2. Simulation Configuration Deck (<cellName>.cir)                              │
│    Authored locally in WorkBoard by agent.                                     │
│    Contains: model wrappers, `.INCLUDE "<cellName>_eldo.net"`, X1, supplies,  │
│    and analysis.                                                               │
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
MMP0 OUT IN VDD VDD psvtgp w=2.0 l=0.065 nfing=1 sense=0 ngcon=1 m=1
+ accurateFlow=0
MMN0 OUT IN VSS VSS nsvtgp w=1.0 l=0.065 nfing=1 sense=0 ngcon=1 m=1
+ accurateFlow=0
.ENDS
```

### Sample B: PDK-Corner Testbench Template (`tb_inverter_tt.cir`)
```spice
* Inverter TT-corner testbench — complete after verifying PDK device interface
.OPTION POST=1
.OPTION ASCII=1
.OPTION SPI3ASC=1

* 1. Select one corner and the verified compatible PDK device/model interface.
.INCLUDE "/modelfile_65nm/typNtypP.cir"
.INCLUDE "<verified-pdk-device-interface>"

* 2. Include derived Eldo simulation copy; preserve inverter.net unchanged.
.INCLUDE "inverter_eldo.net"

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

For VTC, create a separate `tb_inverter_vtc.cir` with the same **verified PDK device interface**, structural-netlist, and supply sections. Replace the input and the complete transient analysis/output block with:

```spice
VIN IN 0 DC 0
.DC VIN 0 1.2 0.01
.PRINT DC V(IN) V(OUT)
```

Use broad probes such as `.PROBE V(*)`, `.PROBE V(X1.*)`, or `.PROBE I(*)` only for a focused debug run: they can create unnecessarily large output files.

### Sample C: Annotated Eldo Output Listing (`inverter.chi`)
```text
  Run on edatools-server2.iiitd.edu.in (Linux 2.6.32-754.35.1.el6.x86_64)

/mentor/AMS/aol/bin/eldo_64.exe -i tb_inverter_tt.cir

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
*** TITLE: * Inverter TT-corner testbench
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
      "command": "tb_inverter_tt.cir",
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
