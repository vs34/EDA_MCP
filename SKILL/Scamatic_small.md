---
name: analog-schematic-quick
description: >-
  Compact procedural checklist for creating analog schematics in Cadence
  Virtuoso. Covers execution mode selection, ASCII schematic preview confirmation,
  MCP-based SKILL creation, optional Eldo simulation, and summary reporting.
---

# Analog Schematic Design — Quick Step-by-Step Guide

A structured, end-to-end procedure for building analog schematics via SKILL / `eda-mcp` and running simulations. Follow these steps in strict sequential order.

---

## Step 1: Determine Execution Mode (Standalone vs. Assisted Virtuoso)

Before running any commands, determine the Virtuoso execution mode:
- **Standalone Mode (`start_standalone` / `standalone`):** Runs non-graphical Virtuoso (`virtuoso -nograph`). **(Recommended)** Ideal for headless SKILL scripting, CDF updates, and netlist extraction without GUI timeouts.
- **Assisted Run Mode (`assisted_run`):** Connects to an active graphical Cadence Virtuoso editor session for visual GUI interaction.

*(The agent manages Virtuoso session initialization automatically.)*

---

## Step 2: Draw ASCII Schematic & Seek User Confirmation

**DO NOT execute MCP commands yet.** First, design the circuit and present it visually to the user.

1. **Size Devices & Plan Architecture:** Determine device counts, $W/L$ dimensions, overdrive voltages ($V_{OV}$), and net connections.
2. **Render ASCII Schematic:** Use the `ascii-schematics` skill to render the circuit diagram.
3. **Ask User for Confirmation:** Present the ASCII schematic, sizing specs, and net topology, then explicitly ask the user:
   > *"Is this the circuit topology, sizing, and schematic structure you want me to create?"*
4. **Wait for User Response:** Do not proceed to Step 3 until the user confirms or provides modifications.

---

## Step 3: Programmatically Create Schematic via MCP (`eda-mcp`)

**ONLY proceed after receiving explicit user confirmation in Step 2.**

### A. Place & Size Components
- Open or create the schematic cellview in the **`MCP`** library:
  ```lisp
  cv = dbOpenCellViewByType("MCP" "<cellName>" "schematic" "schematic" "a")
  ```
- Place transistor instances with descriptive names (`M1_ref`, `M2_mirror`, etc.).
- Explicitly set $W$ and $L$ CDF parameters for every device:
  ```lisp
  dbSetInstCDFparamValue(inst "w" "string" "<width>")
  dbSetInstCDFparamValue(inst "l" "string" "<length>")
  ```
- Place input (`ipin`), output (`opin`), and power (`iopin`) pins from the `basic` library using `schCreatePin`.

### B. Wire Nets & Bulk Connections
- Create nets (`dbMakeNet`) and connect terminals (`dbCreateConnByName`).
- **Wire ALL Terminals (Gates, Drains, Sources, Bulks):**
  - **Gates (`g`):** EVERY gate terminal MUST be explicitly connected to an input pin, signal net, or bias voltage net. **Floating gates are strictly forbidden.**
  - **Bulks (`b`):** PMOS bulk ($b$) $\rightarrow$ `VDD`, NMOS bulk ($b$) $\rightarrow$ `VSS`.
  - **Drains (`d`) & Sources (`s`):** Connect to output pins, internal nodes, or supply rails according to circuit topology.
- Verify no floating terminals, unattached gates, or unintended short circuits exist.

### C. Check & Save Cellview (Zero-Tolerance for Warnings)
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

---

## Step 4: Ask User to Run Eldo Simulation

**ONLY proceed after `schCheck` passes with zero errors and zero warnings regarding floating nodes.**

- Inform the user that the schematic cellview is created and verified with zero errors/warnings in the `MCP` library.
- Explicitly ask the user:
  > *"The schematic has been created and verified with 0 errors and 0 warnings. Would you like me to run Eldo simulations on this netlist?"*
- Wait for user confirmation before initiating simulation.


---

## Step 5: Execute Eldo Simulation & Present Summary

If the user agrees to run simulations:

1. **Extract / Prepare Netlist:**
   - Generate netlist (`.cir`) with a valid Title Line on Line 1.
   - Flush file stream using `drain(fileId)` before `close(fileId)`.
   - Ensure compatible model cards (`nsvtgp`, `psvtgp`) and simulation controls (`.dc`, `.tran`, `.ac`, `.option`) are present.
2. **Run Simulation:**
   - Initialize `eldo` session and execute interactive or batch simulation sweep.
3. **Present Summary:**
   - Output a clean text summary of DC operating points, transient delay/rise times, AC gain/bandwidth, and key performance metrics. Do not render visual waveforms.

*Note: You may use WorkBoard (`workboard`) for file syncing across the local machine and remote server (e.g., pulling/pushing netlists, model cards, or simulation results).*

---

*Follow the 5 steps in strict sequence. Always confirm with the user after Step 2 and Step 4.*


