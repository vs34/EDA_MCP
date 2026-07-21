procedure( MCP_DataHandler(ipcId data)
    let((p oldWo oldPo res)
        ;; Prints debug info to Virtuoso CIW
        printf("[RUNNING]: %s\n" data)

        ;; Redirects command output to file
        p = outfile("mcp_output.txt" "a")
        oldWo = woport  oldPo = poport
        woport = p      poport = p

        res = evalstring(data)
        fprintf(p "RESULT: %L\n\n" res)

        close(p)
        woport = oldWo  poport = oldPo
    )
)

if( boundp('MCP) && ipcIsAliveProcess(MCP) ipcKillProcess(MCP) )
MCP = ipcBeginProcess("python -u MCP_sockit.py" "" "MCP_DataHandler")
