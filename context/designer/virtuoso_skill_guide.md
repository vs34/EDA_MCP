# Virtuoso SKILL Guide for EDA-MCP Agents

## Technology and cellview assumptions

- Default design library: `MCP`.
- Technology library: `cmos065`; SVT PMOS: `psvtgp`; SVT NMOS: `nsvtgp`.
- Pin masters: `basic/ipin`, `basic/opin`, and `basic/iopin`.
- These names describe the installed environment, not a portable PDK abstraction. Verify a master or parameter when the live environment disagrees.

## Safe construction pattern

```lisp
;; 1. Standard Pin Creation Helper
procedure(createPin(cv name dir pt)
  let((pinMaster pinInst)
    pinMaster = case(dir
      ("input"  dbOpenCellViewByType("basic" "ipin"  "symbol" nil "r"))
      ("output" dbOpenCellViewByType("basic" "opin"  "symbol" nil "r"))
      (t        dbOpenCellViewByType("basic" "iopin" "symbol" nil "r"))
    )
    pinInst = schCreatePin(cv pinMaster name dir nil pt "R0")
    dbClose(pinMaster)
    pinInst
  )
)

;; 2. Standard Cellview Construction
;; Use a new, unique cell name. Do not use mode "w" as a generic default: it can
;; overwrite an existing view. Inspect an existing cell and obtain authorization first.
cv = dbOpenCellViewByType("MCP" "<newCellName>" "schematic" "schematic" "a")

p = dbCreateInstByMasterName(cv "cmos065" "psvtgp" "symbol" "MP1" list(1.0 1.5) "R0")
n = dbCreateInstByMasterName(cv "cmos065" "nsvtgp" "symbol" "MN1" list(1.0 0.5) "R0")
initMosTransistor(p "2.0" "0.065")
initMosTransistor(n "1.0" "0.065")

createPin(cv "IN" "input" list(0.0 1.0))
createPin(cv "OUT" "output" list(2.0 1.0))
createPin(cv "VDD" "inputOutput" list(1.25 2.0))
createPin(cv "VSS" "inputOutput" list(1.25 0.0))

;; 3. DUAL BINDING RULE: Always bind logical net AND draw physical wire
;; Both dbCreateConnByName AND schCreateWire are strictly required for schCheck (0 0).
netIn = dbCreateNet(cv "IN")
dbCreateConnByName(netIn p "g")
dbCreateConnByName(netIn n "g")
```

Use CDF callbacks (`initMosTransistor`); do not assign meter-valued raw properties. Build logical nets (`dbCreateConnByName`) and physical wires (`schCreateWire`).

## Assisted Run SKILL Formatting Guarantee

The MCP server removes `;;` SKILL comments and normalizes newlines before sending commands to Virtuoso. Use `;;` comments only; do not rely on a single `;` comment being removed. Agents can write formatted, multi-line SKILL blocks directly in `virtuoso(action="assisted_run", command="...")`. Do **NOT** write temporary `.il` files to disk.

## Physical wiring and validation

- Determine terminal endpoints from the verified offset table in [`schematic_flow.md`](schematic_flow.md) only for the stated PDK release and `R0`; otherwise inspect the instance geometry.
- Create wires that end on the actual terminal/pin connection points. Use jogs and T-junctions rather than four-way crossings.
- Helper for creating wire segments:

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

`hnlInit`, `hnlNetlist`, and `hnlEnd` are obsolete for this deployed Virtuoso environment and MUST NOT be used.

### Primary Verified Flow: GUI Form with `"test"` Template
The fastest and most reliable way to export structural CDL netlists is using `transCdlOutForm` loaded with the pre-configured `"test"` template:

```lisp
prog(()
  transCdlOutDisplay()
  hiiSetCurrentForm('transCdlOutForm)
  transCdlOutForm->cdlOTemplateFile->value = "test"
  transCdlOutForm->cdlOLibName->value = "MCP"
  transCdlOutForm->cdlOTopCell->value = "<cellName>"
  transCdlOutForm->cdlOViewName->value = "schematic"
  transCdlOutForm->cdlONetlistFile->value = "<cellName>.net"
  transCdlOutForm->cdlORunDir->value = "<ELDO_WORKDIR>"
  hiFormDone(transCdlOutForm)
  when(boundp('simSaveAllForm) && hiIsFormDisplayed(simSaveAllForm) hiFormDone(simSaveAllForm))
  when(boundp('simNetNoOp6) hiDBoxOK(simNetNoOp6))
  return(t)
)
```

After export, verify that `<ELDO_WORKDIR>/<cellName>.net` exists and inspect its `.SUBCKT` pin order before building a testbench. The form names in the example are environment-specific recovery details, not commands to invoke blindly.

### Alternative Batch Flow: Cadence `si.env` Netlister
Use this fallback only when a headless workflow is required and the GUI form flow is unavailable:
1. Write `si.env` in Virtuoso workspace (`~/Desktop/cmos65/si.env`):
   ```lisp
   let((fp)
     fp = outfile("si.env" "w")
     fprintf(fp "simLibName = \"MCP\"\n")
     fprintf(fp "simCellName = \"%s\"\n" "<cellName>")
     fprintf(fp "simViewName = \"schematic\"\n")
     fprintf(fp "simSimulator = \"auCdl\"\n")
     fprintf(fp "simNotIncremental = 't\nsimReNetlistAll = 't\n")
     fprintf(fp "simViewList = '(\"auCdl\" \"auSchematic\" \"auGate_sch\" \"auGate_cdl\" \"auCmos_sch\" \"schematic\" \"gate_sch\" \"cmos_sch\" \"symbol\")\n")
     fprintf(fp "simStopList = '(\"auCdl\")\n")
     fprintf(fp "simNetlistHier = t\n")
     fprintf(fp "hnlNetlistFileName = \"%s.net\"\n" "<cellName>")
     fprintf(fp "auCdlDefNetlistProc = \"ansCdlSubcktCall\"\n")
     drain(fp) close(fp)
   )
   ```
2. Execute via `virtuoso(action="run_terminal_command")` and copy the result to `<ELDO_WORKDIR>`.

## Error handling

Keep `assisted_run` commands focused and require a returned `RESULT:` marker after each mutating phase: open/create, placement, wiring, validation, and save/display. If a call times out, the database state is unknown: do **not** resend the mutating command. Inspect the GUI/cellview, dismiss any modal dialog, run a tiny read-only `printf` health probe, then continue from the observed state. `simSaveAllForm` and `simNetNoOp6` are environment-specific examples; use `hiFormDone(...)` or `hiDBoxOK(...)` only after confirming that form/dialog is present.
