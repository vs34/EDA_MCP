#!/bin/bash
# Create FIFO pipe if it doesn't exist
if [ ! -p MCP.command ]; then
    mkfifo MCP.command
    echo "Created FIFO pipe: MCP.command"
else
    echo "FIFO pipe MCP.command already exists."
fi
# Set DISPLAY if not already set (default to :0 for local display/VNC)
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

nohup virtuoso > /dev/null 2>&1 &
