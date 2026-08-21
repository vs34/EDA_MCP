# Analog Schematic Design — Quick Step-by-Step Guide

A structured, end-to-end procedure for building analog schematics via SKILL / `eda-mcp` and running simulations. Follow these steps in strict sequential order.

---

## Step 1: Determine Execution Mode (Assisted Run vs. Script Mode)

Before running any commands, determine the Virtuoso execution mode:
- **Assisted Run Mode (`assisted_run`):** Executes SKILL commands against the active Cadence Virtuoso editor session for visual GUI interaction and live window display (`geOpen`).
- **Batch Script Mode (`run_script`):** Executes standalone SKILL scripts headlessly (`virtuoso -nograph`) for batch processing, netlist extraction, and automated checks.

*(The agent manages Virtuoso session initialization automatically via `server.py`.)*

---

## Step 2: Draw ASCII Schematic & Seek User Confirmation (`ask_question`)

**DO NOT execute MCP commands yet.** First, design the circuit and present it visually inside the `ask_question` modal and chat response.

1. **Size Devices & Plan Architecture:** Determine device counts, $W/L$ dimensions, overdrive voltages ($V_{OV}$), and net connections.
2. **Render ASCII Schematic:** Use the `ascii-schematics` skill to render the complete circuit diagram.
3. **Output Diagram in Response & Invoke `ask_question`:**
   - Print the ASCII schematic and sizing table in your main response text.
   - **CRITICAL**: Include the **full ASCII schematic diagram, net list, and device sizing table directly inside the `question` string** of `ask_question` so the user can see the schematic right inside the modal popup window!

   ```json
   {
     "questions": [
       {
         "question": "### Proposed Schematic & Topology:\n\n```text\n      VDD (1.2V)\n       │\n     ┌─┴─┐\n     │M1 │ PMOS (W=2.0u, L=0.065u)\n     └─┬─┘\n  VIN ─┼────── VOUT\n     ┌─┴─┐\n     │M2 │ NMOS (W=1.0u, L=0.065u)\n     └─┬─┘\n       │\n      GND\n```\n\n**Device Sizing & Nets:**\n- M1 (PMOS): W=2.0u, L=0.065u (Bulk -> VDD, Drain -> VOUT)\n- M2 (NMOS): W=1.0u, L=0.065u (Bulk -> GND, Drain -> VOUT)\n\nIs this the circuit topology, sizing, and schematic structure you want me to create in Virtuoso?",
         "options": [
           "(Recommended) Proceed with creating this schematic in Virtuoso",
           "Modify transistor sizing or dimensions",
           "Change circuit topology or net connections"
         ],
         "is_multi_select": false
       }
     ],
     "toolAction": "Asking confirmation for schematic structure",
     "toolSummary": "Schematic topology confirmation"
   }
   ```
4. **Wait for User Response:** Execution blocks until the user selects an option or submits write-in feedback in the modal. Do not proceed to Step 3 until confirmed.

---

## Step 3: Programmatically Create Schematic via MCP (`eda-mcp`)

**ONLY proceed after receiving explicit user confirmation in Step 2.**

### A. Place & Size Components
- Open or create the schematic cellview in the **`MCP`** library:
  ```lisp
  cv = dbOpenCellViewByType("MCP" "<cellName>" "schematic" "schematic" "a")
  ```
- Place transistor instances with descriptive names (`M1_ref`, `M2_mirror`, etc.):
  ```lisp
  inst = dbCreateInstByMasterName(cv "cmos065" "nsvtgp" "symbol" "M1" list(1.0 1.0) "R0")
  ```
- **Transistor Sizing & CDF Lifecycle (`cmos065`):**
  Use `initMosTransistor` (or CDF property assignment) with width and length expressed in **Microns ($\mu\text{m}$)** (e.g., `"2.0"` for $2.0\mu\text{m}$, `"0.065"` for $65\text{nm}$):
  ```lisp
  initMosTransistor(inst "2.0" "0.065")
  ```
- Place input (`ipin`), output (`opin`), and power (`iopin`) pins from the `basic` library using `schCreatePin`.

### B. Wire Nets & Bulk Connections
- Create nets (`dbMakeNet`) and connect terminals (`dbCreateConnByName`).
- **Wire ALL Terminals (Gates, Drains, Sources, Bulks):**
  - **Gates (`g`):** EVERY gate terminal MUST be explicitly connected to an input pin, signal net, or bias voltage net. **Floating gates are strictly forbidden.**
  - **Bulks (`b`):** PMOS bulk ($b$) $\rightarrow$ `VDD`, NMOS bulk ($b$) $\rightarrow$ `VSS`.
  - **Drains (`d`) & Sources (`s`):** Connect to output pins, internal nodes, or supply rails according to circuit topology.
- Verify no floating terminals, unattached gates, or unintended short circuits exist.

### C. Check, Save & Display Cellview (Zero-Tolerance for Warnings)
- Execute schematic check:
  ```lisp
  schCheck(cv)
  ```
- **CRITICAL: DO NOT IGNORE WARNINGS!** Virtuoso `schCheck` often reports floating gates, unattached terminals, or unconnected nets as *Warnings* (e.g., "0 errors, 15 warnings").
- **Audit & Resolution Requirement:**
  1. Inspect the full `schCheck` log for both **errors AND warnings**.
  2. **NEVER** ignore warnings about floating gates, unattached terminals, or unconnected nets.
  3. If any warnings/errors exist regarding floating/unconnected nodes, **STOP**. Fix the SKILL wiring code immediately to connect every floating terminal.
  4. Re-run `schCheck(cv)` until **0 errors AND 0 warnings** regarding floating/unconnected nodes remain.
- Save cellview only after verifying clean check:
  ```lisp
  dbSave(cv)
  ```
- **GUI Window Display (`assisted_run`):** Open the cellview if not already open (guarded to prevent duplicate window spawns) and **DO NOT call `dbClose(cv)`**:
  ```lisp
  unless( geGetCellViewWindow(cv)
      geOpen(?lib "MCP" ?cell "<cellName>" ?view "schematic" ?viewType "schematic" ?mode "a")
  )
  ```

---

## Step 4: Ask User to Run Eldo Simulation

*(Refer to [`context/designer/eldo_simulation_guide.md`](eldo_simulation_guide.md) for full Eldo simulation execution rules, netlist syntax, and REPL directives.)*

**ONLY proceed after `schCheck` passes with zero errors and zero warnings regarding floating nodes.**

- Inform the user that the schematic cellview is created and verified with zero errors/warnings in the `MCP` library.
- Invoke the interactive `ask_question` tool:
  ```json
  {
    "questions": [
      {
        "question": "The schematic has been created and verified with 0 errors and 0 warnings. Would you like me to run Eldo simulations on this netlist?",
        "options": [
          "(Recommended) Proceed with Eldo simulation sweep",
          "Skip simulation for now"
        ],
        "is_multi_select": false
      }
    ],
    "toolAction": "Asking confirmation for Eldo simulation",
    "toolSummary": "Eldo simulation confirmation"
  }
  ```
- Wait for user response via `ask_question` before initiating simulation.

---

## Step 5: Execute Eldo Simulation & Present Summary

If the user agrees to run simulations:

1. **Export Virtuoso Netlist (`<cellName>.net`)**:
   - **DO NOT hand-write transistor netlists by hand.** Programmatically export the structural subcircuit netlist (`<cellName>.net` or `.cdl`) directly from the Virtuoso schematic cellview (`MCP` library) via CDL SKILL commands, saving to `~/Desktop/eldo/<cellName>.net`.

2. **Select Eldo Simulation Mode**:
   - **Mode 1: Interactive REPL Mode (`eldo(action="start_interactive")` & `run_interactive`)**:
     - Uses the exported `<cellName>.net` structural netlist file.
     - Write interactive commands directly to the REPL terminal (`run`, `step`, parameter sweeps, print commands) to observe real-time simulation output.
   - **Mode 2: Batch Script Mode (`eldo(action="run_script")`)**:
     - Requires 2 files:
       1. **Structural Netlist (`<cellName>.net`)**: Saved in `~/Desktop/eldo/<cellName>.net`.
       2. **Simulation Configuration Deck (`<cellName>.cir`)**: Created **locally** by the agent (specifying `.include "<cellName>.net"`, `.include "cmos065.mod"`, subcircuit instantiation `X1`, pin voltage sources, simulation controls, and `.OPTION SPI3` / waveform output directives so `.spi3` waveform files are produced alongside `.chi` files), and then **exported to the server using WorkBoard (`workboard`)**.
     - Execute batch simulation: `eldo(action="run_script", command="<cellName>.cir", work_dir="~/Desktop/eldo")`.

3. **Download Output Files & Waveform Visualization**:
   - After simulation completes, download output files (**`.spi3` waveform file** and **`.chi` summary file**, plus log files) from the remote server to the local workspace using **`workboard(action="add")`** or `workboard` sync.
   - Analyze `.chi` output files locally for DC operating points, transient delays, AC gain/bandwidth, and circuit bug analysis.
   - Launch waveform plotting using **`eldo(action="visualize_waveforms", file_path="<cellName>.spi3")`** to display interactive multi-pane signal plots for the user.

---

*Follow the 5 steps in strict sequence. Always confirm with the user after Step 2 and Step 4.*
