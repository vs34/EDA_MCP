procedure( MCP_DataHandler(ipcId data)
    let((p oldWo oldPo res errSuccess)
        printf("[RUNNING]: %s\n" data)

        p = outfile("mcp_output.txt" "a")
        oldWo = woport  oldPo = poport
        woport = p      poport = p

        unwindProtect(
            progn(
                errSuccess = errset(res = evalstring(data) t)
                if( errSuccess then
                    fprintf(p "RESULT: %L\n\n" res)
                else
                    fprintf(p "RESULT: ERROR (SKILL evaluation failed)\n\n")
                )
            )
            progn(
                close(p)
                woport = oldWo  poport = oldPo
            )
        )
    )
)

procedure( initPdkLibrary(libName)
    let((libObj libInitFile libFile piport)
        libObj = ddGetObj(libName)
        when(libObj
            libInitFile = strcat(libObj~>readPath "/libInit.il")
            when(isFile(libInitFile)
                let((piport)
                    piport = infile(libInitFile)
                    when(piport loadi(libInitFile) close(piport))
                )
            )
            libFile = strcat(libObj~>readPath "/library.il")
            when(isFile(libFile) load(libFile))

            unless(boundp('senseChoices)
                senseChoices = list("0" "1" "2" "3" "4" "5" "6" "7")
            )
        )
        t
    )
)

procedure( initMosTransistor(inst wMicrons lMicrons)
    let((cdfgData)
        cdfgData = cdfGetInstCDF(inst)
        when(cdfgData
            when(isCallable('DK_mosInit) DK_mosInit(cdfgData))

            cdfgData~>w~>value = wMicrons
            when(isCallable('DK_CBmos) DK_CBmos('w))

            cdfgData~>l~>value = lMicrons
            when(isCallable('DK_CBmos) DK_CBmos('l))

            when(isCallable('DK_mosDone) DK_mosDone(inst))
        )
        t
    )
)

initPdkLibrary("cmos065")

if( boundp('MCP) && ipcIsAliveProcess(MCP) ipcKillProcess(MCP) )
MCP = ipcBeginProcess("python -u MCP_sockit.py" "" "MCP_DataHandler")

