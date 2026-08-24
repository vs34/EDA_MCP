# Analog Schematic Design Workflow

Use this as a decision workflow, not a mandatory conversation script. The agent owns routine engineering choices; request user input only for missing requirements or meaningful side effects.

## 1. Establish intent and execution mode

- Extract supplied function, interfaces, supplies, process assumptions, targets, loads, and required analyses.
- Reuse an existing cell only after inspecting its library, view, and overwrite risk.
- Use `virtuoso(action="assisted_run")` when the user needs live GUI work or a displayed result. Use `virtuoso(action="standalone")` for headless work. `run_script` is an Eldo action, not a Virtuoso action.
- Present an ASCII diagram, net list, or sizing table when it helps resolve an architectural choice or the user requests a review. Do not make it a prerequisite for implementing a fully specified request.

## 2. Plan with evidence

Choose the smallest circuit and simulation set that can answer the user’s question. Derive initial dimensions from supplied constraints or stated assumptions, then validate them with simulation. Identify uncertainties rather than silently inventing a load, model corner, voltage, or temperature.

## 3. Create a physically valid schematic

1. Open/create `MCP/<cell>/schematic` unless the user names another library.
2. Instantiate `cmos065/psvtgp` and `cmos065/nsvtgp`, then initialize each MOS with string micron dimensions:

   ```lisp
   initMosTransistor(inst "2.0" "0.065")
   ```

3. Create named pins and nets. Connect all `g`, `d`, `s`, and `b` terminals; PMOS bulk normally joins the highest supply and NMOS bulk the lowest supply unless the topology requires otherwise.
4. Create physical `schCreateWire` geometry from the actual terminal connection points. `dbCreateConnByName` establishes logical connectivity but does not, by itself, satisfy this PDK’s schematic checker.
5. For `R0` instances in the reported `cmos065` version, the verified terminal offsets from instance origin `(x, y)` are:

   | Terminal | `psvtgp` | `nsvtgp` |
   | --- | --- | --- |
   | `g` | `(x, y)` | `(x, y)` |
   | `d` | `(x + 0.25, y - 0.1875)` | `(x + 0.25, y + 0.1875)` |
   | `s` | `(x + 0.25, y + 0.1875)` | `(x + 0.25, y - 0.1875)` |
   | `b` | `(x + 0.21875, y + 0.0625)` | `(x + 0.21875, y - 0.0625)` |

   Treat this table as PDK-version and orientation-specific. For another orientation, master, or PDK release, inspect the actual terminal geometry rather than extrapolating offsets. Pin connection points created with `schCreatePin(... list(x y) "R0")` are `(x, y)`.
6. Avoid four-way wire crossings. Route branches as staggered three-way T-junctions so `schCheck` does not create crossover/solder-dot warnings.

## 4. Open Window First, Construct Live, and Validate

- In assisted GUI mode, **ALWAYS open the Virtuoso schematic window FIRST** so all operations occur live in the visible window:

  ```lisp
  win = geOpen(?lib "MCP" ?cell "<cellName>" ?view "schematic" ?viewType "schematic" ?mode "a")
  cv = geGetWindowCellView(win)
  ```

- Perform all schematic construction (placing instances, drawing physical wires, creating pins, initializing CDF parameters) directly on `cv` while visible in the open window.
- Run `schCheck(cv)`, inspect its returned log, correct every warning and error, and rerun until the observed result is `(0 0)`.
- Save the design with `dbSave(cv)`. Do not close the window (`dbClose(cv)`).

- If a modal GUI dialog blocks the assisted session, tell the user exactly what needs attention. Do not assume a timeout means the design failed.

## 5. Simulate when it answers the objective

Use the documented structural-netlist workflow in [`eldo_simulation_guide.md`](eldo_simulation_guide.md). Simulation is appropriate when it is requested or needed to validate a design target; ask before running only when the user has reserved that decision or the stimulus/corner criteria are material and unspecified.
