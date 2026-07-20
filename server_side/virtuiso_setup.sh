#!/bin/bash
rm -f MCP.command
mkfifo MCP.command
virtuiso &
