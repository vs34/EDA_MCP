#!/bin/bash
# Create FIFO pipe if it doesn't exist
if [ ! -p MCP.command ]; then
    mkfifo MCP.command
    echo "Created FIFO pipe: MCP.command"
else
    echo "FIFO pipe MCP.command already exists."
fi
virtuoso &
