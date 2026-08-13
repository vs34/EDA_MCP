---
name: analog-schematic-design
description: >-
  Procedural checklist and reasoning guide for creating analog schematics
  in Cadence Virtuoso. Covers the full flow from specification analysis
  through transistor sizing, instance placement, wiring, and validation.
  Designed to strengthen the agent's baseline schematic-building ability
  without micromanaging individual design choices.
---

# Analog Schematic Design — Agent Procedure & Checklist

You are designing an analog schematic in Cadence Virtuoso using SKILL automation via the `eda-mcp` MCP server. This document gives you a structured workflow so you don't miss critical steps, while leaving you full freedom to reason about topology choices, sizing trade-offs, and circuit-level decisions. **Think like a careful analog designer — use first-principles reasoning at every step.**

> **Guiding principle:** A correct schematic is one where every net has a purpose, every device is intentionally sized, and the design can be explained from specification to topology to implementation.

---

## Phase 0 — Understand the Specification

Before touching any tool, make sure you deeply understand what you're building.

- [ ] **Identify the target circuit** (e.g., common-source amplifier, differential pair, current mirror, OTA, bandgap reference, LDO, comparator, etc.).
- [ ] **Extract key specifications** from the user's request: gain, bandwidth, power budget, supply voltage, load conditions, input/output swing, noise, CMRR/PSRR, slew rate — whatever is relevant.
- [ ] **Note the process and device context.** You are working in the `cmos065` 65 nm LP/GP process. Standard-Vt transistors are `nsvtgp` (NMOS) and `psvtgp` (PMOS) from the `cmos065` library. Know their approximate threshold voltages (~0.38 V for NMOS, ~−0.36 V for PMOS) and use that knowledge when reasoning about headroom and operating regions.
- [ ] **Clarify ambiguities** with the user before you start. If the spec is under-constrained, state your assumptions explicitly and proceed.

> **Why this matters:** Jumping into placement without understanding the spec leads to re-work. Take an extra minute here to save twenty later.

---

## Phase 1 — Topology Selection & Architecture

Choose (or confirm) the circuit topology before you begin implementing.

- [ ] **Select a topology** that meets the specifications. Reason about *why* this topology is appropriate — don't just pick one. Consider:
  - Single-ended vs. differential
  - Single-stage vs. multi-stage (and compensation needs)
  - Cascode vs. non-cascode (headroom vs. gain trade-off)
  - Current mirror architecture (simple, cascode, wide-swing)
- [ ] **Sketch the architecture mentally.** Identify the distinct functional blocks (bias network, input stage, output stage, load, feedback path, etc.) and how they connect.
- [ ] **Count the devices and pins.** Determine:
  - How many NMOS and PMOS instances you need
  - Which external pins (I/O, power, bias) are required
  - Which internal nets exist
- [ ] **Identify matching requirements.** Devices that must match (e.g., differential pair transistors, current mirror transistors) should be noted — they will share sizing and should be placed with awareness of symmetry.

> **Think first, code second.** A clear architecture in your head translates to clean SKILL code and a correct schematic on the first attempt.

---

## Phase 2 — Device Sizing

Size every transistor deliberately. This is where analog design judgment matters most.

- [ ] **Start from design equations and constraints**, not arbitrary numbers. For each device or device group, reason about:
  - **Operating region:** Saturation for gain devices, linear for switches. Ensure $V_{DS} > V_{GS} - V_{TH}$ (saturation) or $V_{DS} < V_{GS} - V_{TH}$ (linear) as needed.
  - **Overdrive voltage** ($V_{OV} = V_{GS} - V_{TH}$): Trade-off between $g_m/I_D$ efficiency (low $V_{OV}$) and speed/headroom (higher $V_{OV}$). Typical range: 50 mV – 300 mV.
  - **Current budget:** Distribute the total power budget across branches.
  - **W/L ratio:** Use $I_D = \frac{1}{2} \mu C_{ox} \frac{W}{L} V_{OV}^2$ as a starting estimate for saturation devices. Refine as needed.
- [ ] **Respect minimum and practical dimensions.** In cmos065:
  - Minimum gate length is process-defined (typically ~60 nm drawn). Use longer L for better matching and output resistance where needed.
  - Width should be a reasonable value — avoid absurdly large or small widths. Use multiples and fingering for large devices.
- [ ] **Set W and L for every transistor.** No device should be left at default/unset dimensions. Explicitly assign the `w` and `l` CDF parameters.
- [ ] **Use consistent units.** Express all dimensions in standard units: meters, microns, or nanometers — but be consistent within a schematic. The SKILL CDF interface typically expects SI values (e.g., `200n` for 200 nm, `5u` for 5 µm).
- [ ] **Document your sizing rationale.** Even if briefly — state *why* you chose the W/L for each device so the user (and your future self) can follow the reasoning.

### Sizing Checklist Quick-Reference

| Parameter        | Typical Range (cmos065)      | Design Knob           |
| :--------------- | :--------------------------- | :-------------------- |
| $L$              | 60 nm – 1 µm+               | Matching, $r_o$, speed |
| $V_{OV}$         | 50 mV – 300 mV              | $g_m/I_D$, headroom   |
| $W$              | 200 nm – 100s of µm         | $g_m$, $I_D$, area    |
| Fingers (`nf`)   | 1 – 64+                     | Layout, parasitics    |

> **Don't guess sizes.** Even rough hand calculations produce far better starting points than arbitrary values. Show your work.

---

## Phase 3 — Schematic Entry (Instance Placement)

Now translate your architecture into a SKILL-scripted Virtuoso schematic.

- [ ] **Open (or create) the schematic cellview** in the `MCP` library.
  ```lisp
  cv = dbOpenCellViewByType("MCP" "<cellName>" "schematic" "schematic" "a")
  ```
- [ ] **Clear existing objects if building from scratch** (instances, shapes, nets, terminals) to avoid ghost connections from prior attempts.
- [ ] **Place every transistor instance** using `dbCreateInstByMasterName`. Give each instance a meaningful name (e.g., `"M1_inp"`, `"M3_load"`, `"M5_tail"`) — not just `"I0"`, `"I1"`.
  ```lisp
  dbCreateInstByMasterName(cv "cmos065" "nsvtgp" "symbol" "M1_inp" list(x y) "R0")
  ```
- [ ] **Place any additional components** — resistors, capacitors, current sources from `analogLib` if needed.
- [ ] **Place I/O and power pins** using `schCreatePin` with the correct pin masters from the `basic` library:
  - `ipin` for inputs
  - `opin` for outputs
  - `iopin` for bidirectional / power pins (VDD, VSS)
- [ ] **Think about placement coordinates.** Space instances logically so the schematic is readable:
  - Signal flow generally left-to-right or bottom-to-top
  - Power rails at top (VDD) and bottom (VSS/GND)
  - Matched devices at symmetric positions
  - Leave enough spacing for wires — don't stack instances on top of each other

### Placement Sanity Checks
- Every transistor in your architecture is placed (don't forget bias transistors)
- Every required pin is created with the correct direction (input/output/inputOutput)
- Instance names are unique and meaningful

---

## Phase 4 — Wiring & Connectivity

Connect everything. This is where most schematic errors originate.

- [ ] **Create nets explicitly** using `dbMakeNet(cv "netName")` for every internal and external net.
- [ ] **Wire gate, drain, source, bulk** of every transistor to the correct net using `dbCreateConnByName(net inst "terminalName")`.
- [ ] **Use `schCreateWire`** for visual wires between pins and instances where needed for clarity.
- [ ] **Connect bulk terminals properly:**
  - PMOS bulk (`b`) → VDD (or appropriate N-well bias)
  - NMOS bulk (`b`) → VSS/GND (or appropriate P-well bias)
  - **Never leave a bulk terminal floating.** This is a common and critical mistake.
- [ ] **Connect power pins to supply nets.** Every VDD and VSS pin must be wired to the corresponding net.
- [ ] **Verify gate connections.** Every transistor gate must connect to its intended signal or bias net.
- [ ] **Check drain/source orientation.** In the `cmos065` symbol, make sure you know which terminal is drain and which is source — confusing them flips the device behavior.

### Connectivity Cross-Check (do this mentally or in a table)

For every transistor instance, verify:

| Instance | Gate Net | Drain Net | Source Net | Bulk Net |
| :------- | :------- | :-------- | :--------- | :------- |
| M1_xxx   | ?        | ?         | ?          | ?        |

- [ ] **No floating nets.** Every net should have at least two connections (one driver, one load) unless it's a pin.
- [ ] **No shorted supply rails.** Double-check that VDD and VSS are not accidentally connected.

> **The #1 schematic error is a missing or wrong connection.** Be methodical. Check every terminal of every device.

---

## Phase 5 — Set Device Parameters (CDF Properties)

After placement and wiring, ensure every device has correct electrical parameters.

- [ ] **Set W and L** on every transistor using CDF property modification:
  ```lisp
  dbSetInstCDFparamValue(inst "w" "string" "<width>")
  dbSetInstCDFparamValue(inst "l" "string" "<length>")
  ```
- [ ] **Set number of fingers** (`nf`) if your sizing requires multi-finger devices.
- [ ] **Set any other relevant CDF parameters** (multiplier `m`, etc.) as needed.
- [ ] **Verify parameters were applied** — read them back if unsure:
  ```lisp
  dbGetInstCDFparamValue(inst "w")
  dbGetInstCDFparamValue(inst "l")
  ```

> **A transistor with default sizing is almost never correct.** Treat un-sized devices as bugs.

---

## Phase 6 — Check & Save (Zero-Tolerance for Floating Nodes & Warnings)

Validate the schematic before declaring it done.

- [ ] **Run `schCheck(cv)`** to invoke the Virtuoso schematic checker. This catches:
  - Floating terminals / floating gates
  - Short circuits
  - Missing connections
  - Name conflicts
- [ ] **CRITICAL: NEVER IGNORE WARNINGS!** Virtuoso `schCheck` often reports floating gates, unattached terminals, or unconnected nets as *Warnings* (e.g., "0 errors, 15 warnings").
- [ ] **Audit & Resolve Warnings:**
  - Read both errors AND warnings from `schCheck` log output.
  - If any warnings exist regarding floating gates, unconnected terminals, or unattached pins:
    - **STOP.** Do NOT declare success or proceed to simulation.
    - Fix the SKILL wiring script to wire every single gate and terminal properly.
    - Re-run `schCheck(cv)` until **0 errors AND 0 warnings** regarding floating/unconnected nodes remain.
- [ ] **Save the cellview** with `dbSave(cv)` only after verifying clean check output.
- [ ] **Close the cellview** with `dbClose(cv)` when done (optional but clean).
- [ ] **Report the final schematic to the user**, confirming zero errors and zero floating node warnings.


---

## Phase 7 — Post-Entry Validation (Optional but Recommended)

If simulation infrastructure is available, validate the design electrically.

- [ ] **Create a testbench** schematic with stimulus sources and the DUT.
- [ ] **Run a DC operating-point simulation** to verify all transistors are in their intended operating regions.
- [ ] **Spot-check key metrics** (gain, current consumption, output swing) against the original specification.
- [ ] **Iterate if needed.** If results don't meet spec, revisit sizing (Phase 2) and adjust. This is normal — analog design is inherently iterative.

---

## Things to Keep in Mind Throughout

These are principles, not steps — apply them continuously.

1. **Every wire and every device must be intentional.** If you can't explain why a connection exists, it probably shouldn't.
2. **Think in terms of current paths.** Trace the DC current from VDD to VSS through every branch. If a path doesn't make sense, something is wrong.
3. **Headroom is everything in low-voltage design.** At 1.2 V supply, you have very little room. Stack carefully.
4. **Symmetry matters for differential circuits.** Matched devices should have identical W, L, and orientation.
5. **Don't forget biasing.** A perfectly designed signal path is useless without proper bias. Current mirrors, bias networks, and startup circuits are not optional.
6. **PMOS and NMOS are different.** PMOS has ~3× lower mobility — size accordingly. A PMOS current mirror carrying the same current as an NMOS mirror needs a ~3× wider W/L.
7. **Naming is documentation.** Clear instance names and net names make the schematic self-documenting. Use names like `vbias`, `net_tail`, `vout_p`, `vout_n` — not `net1`, `net2`.
8. **Modularity helps.** For complex circuits, consider building sub-blocks (bias generator, OTA core, output stage) as separate cellviews and instantiating them hierarchically.
9. **When in doubt, be conservative.** Use longer channel lengths for better matching and output resistance. Use lower overdrive for better $g_m/I_D$. Over-design initially — it's easier to relax margins than to fix a fundamentally broken topology.
10. **Trust the process, but verify.** Follow this checklist, but also engage your reasoning. If something feels wrong, investigate before proceeding.

---

## Quick Reference: Common SKILL Patterns

### Setting CDF Parameters on an Instance
```lisp
dbSetInstCDFparamValue(inst "w" "string" "5u")
dbSetInstCDFparamValue(inst "l" "string" "200n")
dbSetInstCDFparamValue(inst "nf" "string" "4")
```

### Creating a Wire Between Two Points
```lisp
schCreateWire(cv "draw" "full" list(x1:y1 x2:y2) 0.0625 0.0625 0.0)
```

### Connecting an Instance Terminal to a Named Net
```lisp
net = dbMakeNet(cv "myNetName")
dbCreateConnByName(net inst "terminalName")
```

### Creating a Pin
```lisp
pinMaster = dbOpenCellViewByType("basic" "ipin" "symbol")
schCreatePin(cv pinMaster "pinName" "input" nil list(x y) "R0")
```

---

*This procedure is your safety net, not your cage. Follow the phases, check the boxes, but bring your own analog intuition to every decision. Good schematic design is equal parts methodology and judgment.*
