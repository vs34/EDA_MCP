---
name: analog-schematic-quick
description: >-
  Compact procedural checklist for creating analog schematics in Cadence
  Virtuoso. A lightweight guide for the agent — covers the essential steps
  without over-explaining. Suitable for simple to moderate circuits.
---

# Analog Schematic Design — Quick Checklist

A lean procedure for building analog schematics via SKILL / `eda-mcp`. Follow the phases in order. Use your own judgment for design decisions — this checklist just makes sure you don't skip anything critical.

---

## 1. Understand What You're Building

- Know the circuit type, key specs, and supply voltage.
- Identify how many NMOS (`nsvtgp`) and PMOS (`psvtgp`) devices you need.
- List the external pins (inputs, outputs, power).
- If something is unclear, ask the user or state your assumptions.

---

## 2. Size Every Device

- Reason about W/L from design intent — don't leave anything at defaults.
- Consider operating region (saturation vs. linear), overdrive voltage, and current budget.
- Matched devices (e.g., mirror pairs) must share identical W and L.
- PMOS needs ~3× wider W than NMOS for the same current (lower mobility).
- Set parameters via CDF after placement:
  ```lisp
  dbSetInstCDFparamValue(inst "w" "string" "<width>")
  dbSetInstCDFparamValue(inst "l" "string" "<length>")
  ```

---

## 3. Build the Schematic

### Place
- Open/create the cellview in the `MCP` library.
- Place all transistor instances with **meaningful names** (e.g., `"M1_ref"`, `"M2_mirror"`).
- Place pins: `ipin` (input), `opin` (output), `iopin` (power/bidir) from `basic` library.
- Space things logically — VDD top, VSS bottom, signal flow left→right.

### Wire
- Create nets with `dbMakeNet`, connect terminals with `dbCreateConnByName`.
- **Connect every bulk terminal:**
  - PMOS `b` → VDD
  - NMOS `b` → VSS
- Verify every gate, drain, source, and bulk is connected to the right net.
- No floating nets. No accidental shorts between supply rails.

### Verify
- Run `schCheck(cv)` — read and fix every error/warning.
- `dbSave(cv)`.

---

## Keep in Mind

- **Every connection must be intentional.** If you can't explain it, investigate.
- **Trace DC current paths** from VDD → through devices → to VSS. Every branch should make sense.
- **Un-sized devices are bugs.** Always set W and L explicitly.
- **Clear naming is free documentation.** Use descriptive net and instance names.
- **Don't forget biasing.** Signal paths need proper bias to function.
- **When unsure, be conservative** — use longer L for better matching, lower overdrive for efficiency.

---

*Follow the steps, trust your reasoning, verify the result.*
