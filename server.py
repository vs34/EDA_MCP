import os
import sys
import time
import shlex
import logging
from mcp.server.fastmcp import FastMCP
from ssh_client import RemoteSession
from virtuoso_client import VirtuosoClient

# Get absolute path to base dir and setup temp logging folder
base_dir = os.path.dirname(os.path.abspath(__file__))
temp_dir = os.path.join(base_dir, "temp")
os.makedirs(temp_dir, exist_ok=True)

# Generate unique log file for each server instance (timestamp + PID)
session_timestamp = time.strftime("%Y%m%d_%H%M%S")
log_filename = f"eda_mcp_{session_timestamp}_{os.getpid()}.log"
log_filepath = os.path.join(temp_dir, log_filename)

# Configure logger
logger = logging.getLogger("EDA_MCP")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")

# File handler for saving logs in temp/
file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Attach file handler to eda_mcp module logger as well
logging.getLogger("eda_mcp").addHandler(file_handler)
logging.getLogger("eda_mcp").setLevel(logging.INFO)

# Stderr handler for stdio output
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(formatter)
logger.addHandler(stderr_handler)

logger.info(f"EDA_MCP Server logging initialized. Log file: {log_filepath}")

# Initialize FastMCP named EDA_MCP
mcp = FastMCP("EDA_MCP")

# Get absolute path to config.json
config_path = os.path.join(base_dir, "config.json")

# Global SSH session and tool clients
session = RemoteSession(config_path=config_path)
virtuoso_client = VirtuosoClient(session=session)

@mcp.tool()
def run_remote_command(command: str) -> str:
    """
    Executes a shell command on the remote EDA server.
    The Cadence tool environment (/cadence/cshrc) is automatically sourced.
    
    Args:
        command: The shell command to run (e.g., 'genus -version' or 'ls -la')
    """
    logger.info(f"[TOOL CALL] run_remote_command: command={command!r}")
    start_time = time.time()
    try:
        exit_code, stdout, stderr = session.execute_command(command)
        output = []
        output.append(f"Exit Status: {exit_code}")
        if stdout.strip():
            output.append(f"\n--- STDOUT ---\n{stdout}")
        if stderr.strip():
            output.append(f"\n--- STDERR ---\n{stderr}")
        res_str = "\n".join(output)
        duration = time.time() - start_time
        logger.info(f"[TOOL RESULT] run_remote_command finished in {duration:.2f}s (exit_code={exit_code})")
        return res_str
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[TOOL ERROR] run_remote_command failed in {duration:.2f}s: {e}")
        return f"Error executing command: {str(e)}"

@mcp.tool()
def read_remote_file(path: str) -> str:
    """
    Reads the content of a file from the remote EDA server.
    Useful for reading log files, timing reports, and script files.
    
    Args:
        path: Path to the remote file (e.g., 'workspace/genus.log' or '/tmp/report.txt')
    """
    logger.info(f"[TOOL CALL] read_remote_file: path={path!r}")
    start_time = time.time()
    try:
        res = session.read_file(path)
        duration = time.time() - start_time
        logger.info(f"[TOOL RESULT] read_remote_file finished in {duration:.2f}s (read {len(res)} chars)")
        return res
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[TOOL ERROR] read_remote_file failed in {duration:.2f}s: {e}")
        return f"Error reading file: {str(e)}"

@mcp.tool()
def write_remote_file(path: str, content: str) -> str:
    """
    Writes or overwrites content to a file on the remote EDA server.
    Useful for creating Tcl scripts or configuration files.
    
    Args:
        path: Path where the file should be saved on the remote server
        content: The text content to write into the file
    """
    logger.info(f"[TOOL CALL] write_remote_file: path={path!r}, content_length={len(content)}")
    start_time = time.time()
    try:
        session.write_file(path, content)
        duration = time.time() - start_time
        logger.info(f"[TOOL RESULT] write_remote_file finished in {duration:.2f}s")
        return f"Successfully wrote file to remote path: {path}"
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[TOOL ERROR] write_remote_file failed in {duration:.2f}s: {e}")
        return f"Error writing file: {str(e)}"

@mcp.tool()
def virtuoso(action: str, command: str = "", work_dir: str = "~/Desktop/cmos65") -> str:
    """
    Control and interact with Cadence Virtuoso.
    
    Args:
        action: The operation to perform ('initialize', 'run', or 'exit')
        command: SKILL code/command to execute when action='run'
        work_dir: Working directory containing MCP_initalize.sh when action='initialize'
    """
    logger.info(f"[TOOL CALL] virtuoso: action={action!r}, command={command!r}, work_dir={work_dir!r}")
    start_time = time.time()
    try:
        act = action.lower().strip()
        if act == "initialize":
            res = virtuoso_client.initialize(work_dir=work_dir)
        elif act == "run":
            if not command.strip():
                res = "Error: 'command' argument is required when action='run'."
            else:
                res = virtuoso_client.run(skill_code=command)
        elif act == "exit":
            res = virtuoso_client.exit()
        else:
            res = f"Error: Unknown action '{action}'. Valid actions are 'initialize', 'run', 'exit'."
        
        duration = time.time() - start_time
        logger.info(f"[TOOL RESULT] virtuoso (action={act}) finished in {duration:.2f}s")
        return res
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[TOOL ERROR] virtuoso (action={action}) failed in {duration:.2f}s: {e}")
        return f"Error in virtuoso tool: {str(e)}"

if __name__ == "__main__":
    # Start the server on stdio transport (default)
    mcp.run()
