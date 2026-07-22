import os
import time
import shlex
import logging
from mcp.server.fastmcp import FastMCP
from ssh_client import RemoteSession
from virtuoso_client import VirtuosoClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EDA_MCP")

# Initialize FastMCP named EDA_MCP
mcp = FastMCP("EDA_MCP")

# Get absolute path to config.json
base_dir = os.path.dirname(os.path.abspath(__file__))
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
    try:
        exit_code, stdout, stderr = session.execute_command(command)
        output = []
        output.append(f"Exit Status: {exit_code}")
        if stdout.strip():
            output.append(f"\n--- STDOUT ---\n{stdout}")
        if stderr.strip():
            output.append(f"\n--- STDERR ---\n{stderr}")
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return f"Error executing command: {str(e)}"

@mcp.tool()
def read_remote_file(path: str) -> str:
    """
    Reads the content of a file from the remote EDA server.
    Useful for reading log files, timing reports, and script files.
    
    Args:
        path: Path to the remote file (e.g., 'workspace/genus.log' or '/tmp/report.txt')
    """
    try:
        return session.read_file(path)
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
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
    try:
        session.write_file(path, content)
        return f"Successfully wrote file to remote path: {path}"
    except Exception as e:
        logger.error(f"Error writing file {path}: {e}")
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
    try:
        act = action.lower().strip()
        if act == "initialize":
            return virtuoso_client.initialize(work_dir=work_dir)
        elif act == "run":
            if not command.strip():
                return "Error: 'command' argument is required when action='run'."
            return virtuoso_client.run(skill_code=command)
        elif act == "exit":
            return virtuoso_client.exit()
        else:
            return f"Error: Unknown action '{action}'. Valid actions are 'initialize', 'run', 'exit'."
    except Exception as e:
        logger.error(f"Error in virtuoso tool (action={action}): {e}")
        return f"Error in virtuoso tool: {str(e)}"

if __name__ == "__main__":
    # Start the server on stdio transport (default)
    mcp.run()
