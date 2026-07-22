#!/bin/csh
# Create FIFO pipe if it doesn't exist
if ( ! -e MCP.command ) then
    mkfifo MCP.command
    echo "Created FIFO pipe: MCP.command"
else
    echo "FIFO pipe MCP.command already exists."
endif

# Source Cadence CMOS 65nm environment setup script
if ( -e .cshrc_cmos065 ) then
    source .cshrc_cmos065
endif

# Set DISPLAY if not already set (default to :0 for local display/VNC)
if ( ! $?DISPLAY ) then
    setenv DISPLAY :0
endif

(virtuoso < /dev/null >& /dev/null &)
