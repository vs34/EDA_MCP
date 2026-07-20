; --- mcp_setup.il ---

; 1. Define Data Handler
procedure( MCP_DataHandler(ipcId data)
    let( (p oldWoport oldPoport result outText)
        p = outstring()
        oldWoport = woport
        oldPoport = poport
        
        woport = p
        poport = p
        
        result = errset(evalstring(data))
        
        outText = getOutstring(p)
        close(p)
        woport = oldWoport
        poport = oldPoport
        
        ipcWriteProcess(ipcId sprintf(nil "__RESULT__:%L\n__STDOUT__:%s\n__END__\n" result outText))
    )
)

; 2. Define Error Handler
procedure( MCP_ErrHandler(ipcId err)
    printf("PYTHON ERROR: %s\n" err)
)

; 3. Start the process
MCP = ipcBeginProcess("python -u MCP_sockit.py" "" "MCP_DataHandler" "MCP_ErrHandler")
