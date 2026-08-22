# Virtuoso SKILL Guide for EDA-MCP Agents

## Technology and cellview assumptions

- Default design library: `MCP`.
- Technology library: `cmos065`; SVT PMOS: `psvtgp`; SVT NMOS: `nsvtgp`.
- Pin masters: `basic/ipin`, `basic/opin`, and `basic/iopin`.
- These names describe the installed environment, not a portable PDK abstraction. Verify a master or parameter when the live environment disagrees.

## Safe construction pattern

```lisp
cv = dbOpenCellViewByType("MCP" "<cellName>" "schematic" "schematic" "a")

p = dbCreateInstByMasterName(cv "cmos065" "psvtgp" "symbol" "MP1" list(1.0 1.5) "R0")
n = dbCreateInstByMasterName(cv "cmos065" "nsvtgp" "symbol" "MN1" list(1.0 0.5) "R0")
initMosTransistor(p "2.0" "0.065")
initMosTransistor(n "1.0" "0.065")
```

Use CDF callbacks; do not assign meter-valued raw properties. Build logical nets and physical wires. A net connection that is not represented by wire geometry can still fail `schCheck` in this PDK.

## Physical wiring and validation

- Determine terminal endpoints from the verified offset table in [`schematic_flow.md`](schematic_flow.md) only for the stated PDK release and `R0`; otherwise inspect the instance geometry.
- Create wires that end on the actual terminal/pin connection points. Use jogs and T-junctions rather than four-way crossings.
- For the documented schematic environment, this helper creates a single wire segment; compose L-jogs and T-junctions from multiple segments as needed:

  ```lisp
  procedure(schW(cv p1 p2)
    schCreateWire(cv "draw" "full" list(p1 p2) 0.0625 0.0625 0.0)
  )
  ```

- Run `schCheck(cv)`, inspect the complete output, and correct all warnings and errors. Save only after the observed result is `(0 0)`.
- Every `outfile` stream must run `drain(fp)` before `close(fp)`.

## GUI and headless ownership

For an assisted GUI operation, save and retain the database object while opening the view:

```lisp
schCheck(cv)
dbSave(cv)
unless(geGetCellViewWindow(cv)
  geOpen(?lib "MCP" ?cell "<cellName>" ?view "schematic" ?viewType "schematic" ?mode "a")
)
```

Do not call `dbClose(cv)` in that path. In a standalone/headless flow, save and close the view when its work is complete.

## Structural netlist export

`hnlInit`, `hnlNetlist`, and `hnlEnd` are obsolete for this deployed Virtuoso environment and MUST NOT be used. They can fail as unbound SKILL functions.

Preferred flow: use the installed Cadence `auCdl` exporter after verifying that its form/callback APIs are available in the current session. The required output is a structural CDL/SPICE netlist generated from `MCP/<cell>/schematic`, with an explicit output file and run directory. A known working form-based configuration is:

```lisp
transCdlOutForm~>cdlOLibName~>value     = "MCP"
transCdlOutForm~>cdlOTopCell~>value     = "<cellName>"
transCdlOutForm~>cdlOViewName~>value    = "schematic"
transCdlOutForm~>cdlONetlistFile~>value = "<cellName>.cdl"
transCdlOutForm~>cdlORunDir~>value      = "/home/vaibhav22555/Desktop/eldo"
transCdlOutForm~>cdlOSimViewList~>value = "auCdl schematic symbol"
transCdlOutForm~>cdlOSimStopList~>value = "auCdl"
transCdlOutForm~>cdlOBkgd~>value        = nil
cdlOutCallback()
```

Before relying on that form, verify the installed `auCdl` environment and output file. If it is unavailable, stop before simulation, report the missing capability to the user, and use another verified Virtuoso-native exporter only if available. Do not silently synthesize a transistor netlist from assumptions.

The simulation deck is separate: it is a locally authored test configuration that includes the exported structural netlist. It must not replicate the device connectivity.

## Error handling

Keep `assisted_run` commands small enough to diagnose. If a call times out, inspect its returned diagnostics and the GUI state; a modal dialog may need the user’s intervention. Use `errset` when it improves recovery or captures a specific SKILL failure.
