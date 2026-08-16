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

if( boundp('MCP) && ipcIsAliveProcess(MCP) ipcKillProcess(MCP) )
MCP = ipcBeginProcess("python -u MCP_sockit.py" "" "MCP_DataHandler")
