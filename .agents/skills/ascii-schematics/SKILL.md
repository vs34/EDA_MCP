---
name: ascii-schematics
description: Rules for printing clean, aligned, unbroken ASCII/Unicode circuit schematics and tables in text output.
---
> Do not create ASCII diagrams using Python. Trust yourself and direct output straight to chat.

# ASCII & Unicode Schematic Drawing Rules

## 1. Fixed Grid & Large Canvas Layout
* Always wrap text schematics inside ```text code blocks.
* **Simple Circuit Schematics:** Draw simple schematics using inline ASCII box diagrams.
* **Normal Canvas Layout:** Use a good grid width (e.g., 40–60 characters wide if needed) to spread out circuit branches, active loads, differential pairs, and bias networks clearly without crowding.
* **Equal Line Widths:** Every row of a box or diagram section MUST have the exact same character count.
* **No Tabs:** Use explicit single spaces (` `), never Tab (`\t`).
* **Flat Text Only for Variables & Subscripts (No LaTeX, No Multi-Line Stacks):**
  * NEVER use LaTeX math delimiters (`$...$`) as inline LaTeX display is unsupported.
  * NEVER split variables or subscripts across multiple lines or multi-row character stacks.
  * ALWAYS write all variable names, parameters, and subscripts as **flat single-line text** (e.g., `C_c`, `R_z`, `V_bias`, `I_ref`, `V_out1`, `w_z = +g_m6 / C_c`).
  * ❌ **FORBIDDEN (Multi-line character stacks):**
    ```text
    C
     c

    R
     z

    ω  = +g  /C
     z     m6  c
    ```
  * ❌ **FORBIDDEN (LaTeX Math Syntax):**
    `$C_c$`, `$R_z$`, `$\omega_z = +g_{m6}/C_c$`
  * ✅ **REQUIRED (Flat Single-Line Text):**
    `C_c`, `R_z`, `w_z = +g_m6 / C_c`, `R_z = 1/g_m6`, `V_out1`, `A_v1`, `V_bias`

## 2. Standard Unicode Box Palette & Wire Rules
* **Wires (ALWAYS Single Line):**
  * **Interconnect Wires MUST ALWAYS be single-line**, never double-line.
  * **Lines:** `│` (vertical wire), `─` (horizontal wire)
  * **Corners:** `┌` (top-left), `┐` (top-right), `└` (bottom-left), `┘` (bottom-right)
  * **Junctions:** `┬` (top T-tap), `┴` (bottom T-tap), `├` (left T), `┤` (right T), `┼` (cross)
* **NMOS Box (Single Line):**
  * Uses single-line borders (`┌...┐`, `│...│`, `└...┘`).
* **PMOS Box (Double Line Box Body):**
  * Uses double-line borders (`╔...╗`, `║...║`, `╚...╝`) exclusively for the device box body to distinguish PMOS from NMOS.
  * **Single Wire Taps into PMOS Double Borders:**
    * Single wire going UP from double top border: Use `╧` (`╔═════╧═════╗`)
    * Single wire going DOWN from double bottom border: Use `╤` (`╚═════╤═════╝`)
    * Single wire going LEFT/RIGHT into double side walls: Use `╢` / `╟`

## 3. Component Box Templates (13 Chars Wide)

### NMOS Box Template (Single Line Box + Single Line Wire)
```text
       │              <-- Single-line center wire at Column 7
 ┌─────┴─────┐        <-- 1 corner + 5 bars + ┴ + 5 bars + 1 corner = 13
 │ M5 {NMOS} │        <-- 1 wall + 11 centered chars + 1 wall       = 13
 │Tail Source│        <-- 1 wall + 11 centered chars + 1 wall       = 13
 └─────┬─────┘        <-- 1 corner + 5 bars + ┬ + 5 bars + 1 corner = 13
       │              <-- Single-line center wire at Column 7
```

### PMOS Box Template (Double Line Box Body + Single Line Wire Taps `╧` / `╤`)
```text
       │              <-- Single-line center wire at Column 7
 ╔═════╧═════╗        <-- 1 double corner + 5 double bars + ╧ + 5 double bars + 1 double corner = 13
 ║ M1 {PMOS} ║        <-- 1 double wall + 11 centered chars + 1 double wall                  = 13
 ║Active Load║        <-- 1 double wall + 11 centered chars + 1 double wall                  = 13
 ╚═════╤═════╝        <-- 1 double corner + 5 double bars + ╤ + 5 double bars + 1 double corner = 13
       │              <-- Single-line center wire at Column 7
```

## 4. Large Circuit Schematic Structure Example
```text
  VDD ─────────────────┬───────────────────────────────┬───────────────── VDD
                       │                               │
                 ╔═════╧═════╗                   ╔═════╧═════╗
                 ║ M1 {PMOS} ║                   ║ M2 {PMOS} ║
                 ║Active Load║                   ║Active Load║
                 ╚═════╤═════╝                   ╚═════╤═════╝
                       ├───────────────┬───────────────┤
                       │               │               │
                 ┌─────┴─────┐         │         ┌─────┴─────┐
       Vin+ ─────┤ M3 {NMOS} │         │         │ M4 {NMOS} ├───── Vin-
                 │ Input Diff│         │         │ Input Diff│
                 └─────┬─────┘         │         └─────┬─────┘
                       │               │               │
                       └───────────────┼───────────────┘
                                       │
                                 ┌─────┴─────┐
                      V_bias ────┤ M5 {NMOS} │
                                 │Tail Source│
                                 └─────┬─────┘
                                       │
  VSS ─────────────────────────────────┴───────────────────────────────── VSS
```

## 5. ASCII & Unicode Tables Rule
* **Use ASCII/Unicode Tables Instead of Markdown Tables:** Whenever presenting tabular data, ALWAYS use clean Unicode/ASCII box-drawing tables inside ```text code blocks instead of standard Markdown tables (`|---|---|`).
* **Direct Text Output (No Script Required):** Generate and format tables **directly in plain text output**. Running or creating external Python/shell scripts to output tables is **NOT required**.
* **Table Alignment:** Align headers and cell values with consistent padding, ensuring all border intersections (`┬`, `┼`, `┴`, `│`) align vertically across every row.

### Unicode Table Example
```text
┌──────────┬──────────┬──────────┐
│ Device   │ Type     │ Size (W) │
├──────────┼──────────┼──────────┤
│ M1       │ PMOS     │ 10.0 µm  │
│ M2       │ NMOS     │  5.0 µm  │
└──────────┴──────────┴──────────┘
```
