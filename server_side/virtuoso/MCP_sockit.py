import sys

FIFO_PATH = "MCP.command"

# Open FIFO in 'r+' mode so it stays open permanently across writes
f_fifo = open(FIFO_PATH, "r+")

while True:
    # Read line from FIFO (blocks until a command is written)
    command = f_fifo.readline()

    if not command or not command.strip():
        continue

    # Send command to Virtuoso
    sys.stdout.write(command)
    sys.stdout.flush()
