import sys
import uuid
import time

FIFO_PATH = "MCP.command"

# Open FIFO in 'r+' mode so it stays open permanently across writes
f_fifo = open(FIFO_PATH, "r+")

while True:
    # Read line from FIFO (blocks until a command is written)
    command = f_fifo.readline()
    
    if not command or not command.strip():
        time.sleep(0.05)
        continue

    # Generate a unique end token for THIS specific command
    end_token = "__END_%s__" % uuid.uuid4().hex[:8]

    # Append a print statement in SKILL that outputs our unique token
    full_cmd = command.strip() + '\nprintf("%s\\n")\n' % end_token

    # Send command + token to Virtuoso
    sys.stdout.write(full_cmd)
    sys.stdout.flush()

    # Read from sys.stdin UNTIL we see our unique token
    ris = ""
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if end_token in line:
            break
        ris += line

    # Save output to log
    with open("MCP.log", "w") as f_log:
        f_log.write(ris)
