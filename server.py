import os
import sys
import time
import shlex
import logging
from mcp.server.fastmcp import FastMCP
from ssh_client import RemoteSession
from virtuoso_client import VirtuosoClient
from eldo_client import EldoClient
from workboard_client import WorkBoardClient
from issue_reporter import IssueReporter

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

# Get tool-specific config paths inside config/ directory
config_dir = os.path.join(base_dir, "config")
remote_control_config = os.path.join(config_dir, "config_remote_control.json")
virtuoso_config = os.path.join(config_dir, "config_virtuoso.json")
eldo_config = os.path.join(config_dir, "config_eldo.json")

# Dedicated SSH sessions per tool
remote_session = RemoteSession(config_path=remote_control_config)
virtuoso_session = RemoteSession(config_path=virtuoso_config)
virtuoso_interactive_session = RemoteSession(config_path=virtuoso_config)
eldo_session = RemoteSession(config_path=eldo_config)

virtuoso_client = VirtuosoClient(session=virtuoso_session)
virtuoso_interactive_client = VirtuosoClient(session=virtuoso_interactive_session)
eldo_client = EldoClient(session=eldo_session)
def _format_result_summary(res: str, max_len: int = 300) -> str:
    """Formats tool return result on a single line for clean, full lifecycle logging."""
    if not res:
        return "<empty>"
    lines = [line.strip() for line in res.strip().splitlines() if line.strip()]
    clean = " || ".join(lines)
    if len(clean) > max_len:
        return f"{clean[:max_len]}... [{len(res)} bytes total]"
    return clean

@mcp.tool()
def remote_control(action: str, command: str = "", path: str = "", content: str = "", timeout: float = 60.0) -> str:
    """
    Execute shell commands and perform file operations on the remote EDA server.
    
    Args:
        action: The operation to perform ('run_command', 'read_file', or 'write_file')
        command: Shell command to execute when action='run_command'
        path: Remote file path when action='read_file' or action='write_file'
        content: Text content to write when action='write_file'
        timeout: Maximum wait time in seconds for execution (default: 60.0)
    """
    logger.info(f"[TOOL CALL] remote_control: action={action!r}, command={command!r}, path={path!r}, content_len={len(content)}, timeout={timeout}")
    start_time = time.time()
    act = action.lower().strip()
    
    try:
        if act in ("run_command", "run_remote_command", "run", "exec", "execute"):
            if not command.strip():
                return "Error: 'command' argument is required when action='run_command'."
            exit_code, stdout, stderr = remote_session.execute_command(command, timeout=timeout)
            output = []
            output.append(f"Exit Status: {exit_code}")
            if stdout.strip():
                output.append(f"\n--- STDOUT ---\n{stdout}")
            if stderr.strip():
                output.append(f"\n--- STDERR ---\n{stderr}")
            res = "\n".join(output)
            
        elif act in ("read_file", "read_remote_file", "read"):
            if not path.strip():
                return "Error: 'path' argument is required when action='read_file'."
            res = remote_session.read_file(path, timeout=timeout)
            
        elif act in ("write_file", "write_remote_file", "write"):
            if not path.strip():
                return "Error: 'path' argument is required when action='write_file'."
            write_res = remote_session.write_file(path, content, timeout=timeout)
            res = write_res or f"Successfully wrote {len(content)} bytes to remote file '{path}'."
            
        else:
            res = f"Error: Unknown action '{action}'. Valid actions are 'run_command', 'read_file', 'write_file'."
            
        duration = time.time() - start_time
        logger.info(f"[TOOL RESULT] remote_control (action={act}) finished in {duration:.2f}s | Result: {_format_result_summary(res)}")
        return res
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[TOOL ERROR] remote_control (action={action}) failed in {duration:.2f}s: {e}")
        return f"Error in remote_control tool: {str(e)}"

@mcp.tool()
def virtuoso(action: str, command: str = "", work_dir: str = "~/Desktop/cmos65", timeout: float = 30.0) -> str:
    """
    Control and interact with Cadence Virtuoso.
    
    Args:
        action: The operation to perform ('initialize', 'assisted_run', 'standalone', 'start_standalone', 'stop_standalone', 'run_terminal_command', 'exit')
        command: SKILL code when action='assisted_run'/'standalone', or shell command when action='run_terminal_command'
        work_dir: Working directory when action='initialize', 'start_standalone', or 'run_terminal_command'
        timeout: Maximum wait time in seconds for execution/response (default: 30.0)
    """
    logger.info(f"[TOOL CALL] virtuoso: action={action!r}, command={command!r}, work_dir={work_dir!r}, timeout={timeout}")
    start_time = time.time()
    try:
        act = action.lower().strip()
        if act == "initialize":
            res = virtuoso_client.initialize(work_dir=work_dir)
        elif act in ("assisted_run", "assisted", "run"):
            if not command.strip():
                res = "Error: 'command' argument is required when action='assisted_run'."
            else:
                res = virtuoso_client.assisted_run(skill_code=command, timeout=timeout)
        elif act in ("standalone", "run_standalone", "run_interactive", "run_inter", "interactive", "inter"):
            res = virtuoso_interactive_client.run_standalone(command=command, work_dir=work_dir, timeout=timeout)
        elif act in ("start_standalone", "start_interactive", "start_inter", "start"):
            res = virtuoso_interactive_client.start_standalone(work_dir=work_dir)
        elif act in ("stop_standalone", "stop_interactive", "stop_inter", "stop", "exit_interactive"):
            res = virtuoso_interactive_client.stop_standalone()
        elif act in ("run_terminal_command", "terminal_command", "run_terminal", "terminal", "cmd", "shell"):
            if not command.strip():
                res = "Error: 'command' argument is required when action='run_terminal_command'."
            else:
                res = virtuoso_client.run_terminal_command(command=command, work_dir=work_dir, timeout=timeout)
        elif act == "exit":
            res = virtuoso_client.exit()
        else:
            res = f"Error: Unknown action '{action}'. Valid actions are 'initialize', 'assisted_run', 'standalone', 'start_standalone', 'stop_standalone', 'run_terminal_command', 'exit'."
        
        duration = time.time() - start_time
        logger.info(f"[TOOL RESULT] virtuoso (action={act}) finished in {duration:.2f}s | Result: {_format_result_summary(res)}")
        return res
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[TOOL ERROR] virtuoso (action={action}) failed in {duration:.2f}s: {e}")
        return f"Error in virtuoso tool: {str(e)}"

@mcp.tool()
def eldo(action: str = "run_terminal_command", command: str = "", work_dir: str = "~/Desktop/eldo", timeout: float = 30.0) -> str:
    """
    Control and interact with Siemens/Mentor Graphics Eldo simulator.
    
    Args:
        action: The operation to perform ('run_terminal_command', 'initialize', 'start_interactive', 'run_interactive', 'stop_interactive', 'run_script', or 'read_extract')
        command: Netlist/script path when action='run_script'/'start_interactive', REPL command when action='run_interactive', or shell command when action='run_terminal_command'
        work_dir: Working directory for simulation execution (defaults to ~/Desktop/eldo if not specified)
        timeout: Maximum wait time in seconds for execution/response (default: 30.0)
    """
    logger.info(f"[TOOL CALL] eldo: action={action!r}, command={command!r}, work_dir={work_dir!r}, timeout={timeout}")
    start_time = time.time()
    try:
        act = action.lower().strip()
        if act == "initialize":
            res = eldo_client.initialize(work_dir=work_dir)
        elif act in ("start_interactive", "start_inter", "start"):
            res = eldo_client.start_interactive(netlist_file=command, work_dir=work_dir)
        elif act in ("run_interactive", "run_inter", "interactive", "inter"):
            res = eldo_client.run_interactive(command=command, work_dir=work_dir, timeout=timeout)
        elif act in ("stop_interactive", "stop_inter", "stop", "exit_interactive", "exit"):
            res = eldo_client.stop_interactive(work_dir=work_dir)
        elif act in ("run_script", "script"):
            res = eldo_client.run_script(script_path=command, work_dir=work_dir)
        elif act in ("read_extract", "extract"):
            res = eldo_client.read_extract(work_dir=work_dir)
        elif act in ("run_terminal_command", "terminal_command", "run_terminal", "terminal", "cmd", "shell"):
            if not command.strip():
                res = "Error: 'command' argument is required when action='run_terminal_command'."
            else:
                res = eldo_client.run_terminal_command(command=command, work_dir=work_dir, timeout=timeout)
        else:
            res = f"Error: Unknown action '{action}'. Valid actions are 'initialize', 'start_interactive', 'run_interactive', 'stop_interactive', 'run_script', 'read_extract', 'run_terminal_command'."
        
        duration = time.time() - start_time
        logger.info(f"[TOOL RESULT] eldo (action={act}) finished in {duration:.2f}s | Result: {_format_result_summary(res)}")
        return res
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[TOOL ERROR] eldo (action={action}) failed in {duration:.2f}s: {e}")
        return f"Error in eldo tool: {str(e)}"

@mcp.tool()
def workboard(
    action: str = "status",
    workboard_name: str = "",
    remote_path: str = "",
    local_path: str = "",
    message: str = "Agent sync",
    recursive: bool = False,
    overwrite: bool = False,
    timeout: float = 60.0
) -> str:
    """
    Git-backed WorkBoard tool for local-remote file synchronization and version control.
    
    Actions:
      - 'initialize': Create a new local WorkBoard workspace and initialize a local Git repository.
      - 'add': Fetch a file/folder from remote server path and add it to a specific WorkBoard at local_path.
      - 'export': Upload a local WorkBoard file/folder to a specified remote server location and register tracking.
      - 'pull': Re-fetch latest remote server version of an added file to update the local WorkBoard.
      - 'push': Upload local edits from WorkBoard back to mapped remote server location and commit locally.
      - 'diff': Display unified diff between local WorkBoard file and remote server version.
      - 'status': List all tracked files and their status for a specific WorkBoard.
      - 'history': Display local Git commit history for a specific file or workspace.
    """
    logger.info(f"[TOOL CALL] workboard: action={action!r}, workboard_name={workboard_name!r}, remote_path={remote_path!r}, local_path={local_path!r}")
    start_time = time.time()
    try:
        act = action.lower().strip()
        if act == "initialize":
            res = workboard_client.initialize(workboard_name=workboard_name or "default")
        elif act in ("add", "add_file"):
            res = workboard_client.add(remote_path=remote_path, local_path=local_path, workboard_name=workboard_name, timeout=timeout)
        elif act in ("export", "export_file"):
            if not local_path.strip():
                return "Error: 'local_path' is required for export action."

            # Check if remote file exists using remote_session.execute_command
            wb_name, _ = workboard_client._resolve_workboard_name(workboard_name)
            wb_dir = workboard_client._get_workboard_dir(wb_name)
            registry = workboard_client._load_registry(wb_dir, wb_name)
            target_remote = remote_path.strip() or registry.get("files", {}).get(local_path.strip(), {}).get("remote_path", "")

            if target_remote and not overwrite:
                quoted_remote = f"$HOME{shlex.quote(target_remote[1:])}" if target_remote.startswith("~") else shlex.quote(target_remote)
                check_cmd = f"test -e {quoted_remote}"
                exit_code, _, _ = remote_session.execute_command(check_cmd, timeout=timeout)
                if exit_code == 0:
                    return f"Error: File at remote path '{target_remote}' already exists on the server. Set overwrite=True to overwrite it."

            res = workboard_client.export(local_path=local_path, remote_path=remote_path, workboard_name=workboard_name, message=message, timeout=timeout)
        elif act == "pull":
            res = workboard_client.pull(local_path=local_path, workboard_name=workboard_name, timeout=timeout)
        elif act == "push":
            res = workboard_client.push(local_path=local_path, workboard_name=workboard_name, message=message, timeout=timeout)
        elif act == "diff":
            res = workboard_client.diff(local_path=local_path, workboard_name=workboard_name)
        elif act == "status":
            res = workboard_client.status(workboard_name=workboard_name)
        elif act in ("history", "log"):
            res = workboard_client.history(local_path=local_path, workboard_name=workboard_name)
        else:
            res = f"Error: Unknown action '{action}'. Valid actions are 'initialize', 'add', 'export', 'pull', 'push', 'diff', 'status', 'history'."

        duration = time.time() - start_time
        logger.info(f"[TOOL RESULT] workboard (action={act}) finished in {duration:.2f}s | Result: {_format_result_summary(res)}")
        return res
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[TOOL ERROR] workboard (action={action}) failed in {duration:.2f}s: {e}")
        return f"Error in workboard tool: {str(e)}"

@mcp.tool()
def report_issue(
    title: str,
    agent_name: str = "Antigravity",
    agent_model: str = "",
    session_id: str = "unknown",
    domain_intent: str = "",
    tool_name: str = "",
    tool_action: str = "",
    error_message: str = "",
    expected_behavior: str = "",
    label: str = "bug"
) -> str:
    """
    Report an issue, bug, or feature request directly to GitHub for Agent B to fix.
    
    Args:
        title: Concise title describing the problem or feature request.
        agent_name: Name of the reporting agent ('Antigravity', 'Claude', etc.).
        agent_model: Model name/version of the reporting agent (e.g. 'gemini-3.6-flash', 'claude-3-5-sonnet').
        session_id: The conversation/session ID of the current agent turn.
        domain_intent: High-level Chip Design task or context being performed.
        tool_name: The MCP tool that encountered an error or needs enhancement (e.g. 'eldo', 'virtuoso').
        tool_action: The action parameter invoked on the tool (e.g. 'run_script', 'pull').
        error_message: The raw error output or trace returned by the tool.
        expected_behavior: Optional expected behavior or user requirement.
        label: GitHub issue label ('bug', 'enhancement', 'documentation', etc.).
    """
    logger.info(f"[TOOL CALL] report_issue: title={title!r}, agent={agent_name!r}, model={agent_model!r}, tool={tool_name!r}, log_file={log_filename!r}, label={label!r}")
    return IssueReporter.create_issue(
        title=title,
        agent_name=agent_name,
        agent_model=agent_model,
        session_id=session_id,
        domain_intent=domain_intent,
        tool_name=tool_name,
        tool_action=tool_action,
        error_message=error_message,
        expected_behavior=expected_behavior,
        log_file=log_filename,
        label=label,
        cwd=base_dir
    )

if __name__ == "__main__":
    # Start the server on stdio transport (default)
    mcp.run()
