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
def remote_control(action: str, command: str = "", path: str = "", content: str = "") -> str:
    """
    Execute shell commands and perform file operations on the remote EDA server.
    
    Args:
        action: The operation to perform ('run_command', 'read_file', or 'write_file')
        command: Shell command to execute when action='run_command'
        path: Remote file path when action='read_file' or action='write_file'
        content: Text content to write when action='write_file'
    """
    logger.info(f"[TOOL CALL] remote_control: action={action!r}, command={command!r}, path={path!r}, content_len={len(content)}")
    start_time = time.time()
    act = action.lower().strip()
    
    try:
        if act in ("run_command", "run_remote_command", "run", "exec", "execute"):
            if not command.strip():
                return "Error: 'command' argument is required when action='run_command'."
            exit_code, stdout, stderr = session.execute_command(command)
            output = []
            output.append(f"Exit Status: {exit_code}")
            if stdout.strip():
                output.append(f"\n--- STDOUT ---\n{stdout}")
            if stderr.strip():
                output.append(f"\n--- STDERR ---\n{stderr}")
            res_str = "\n".join(output)
            duration = time.time() - start_time
            logger.info(f"[TOOL RESULT] remote_control (action={act}) finished in {duration:.2f}s (exit_code={exit_code})")
            return res_str
            
        elif act in ("read_file", "read_remote_file", "read"):
            if not path.strip():
                return "Error: 'path' argument is required when action='read_file'."
            res = session.read_file(path)
            duration = time.time() - start_time
            logger.info(f"[TOOL RESULT] remote_control (action={act}) finished in {duration:.2f}s (read {len(res)} chars)")
            return res
            
        elif act in ("write_file", "write_remote_file", "write"):
            if not path.strip():
                return "Error: 'path' argument is required when action='write_file'."
            session.write_file(path, content)
            duration = time.time() - start_time
            logger.info(f"[TOOL RESULT] remote_control (action={act}) finished in {duration:.2f}s")
            return f"Successfully wrote file to remote path: {path}"
            
        else:
            return f"Error: Unknown action '{action}'. Valid actions are 'run_command', 'read_file', 'write_file'."
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[TOOL ERROR] remote_control (action={action}) failed in {duration:.2f}s: {e}")
        return f"Error in remote_control tool: {str(e)}"

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
