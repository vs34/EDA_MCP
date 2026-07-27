import shlex
import time
import logging
from ssh_client import RemoteSession

logger = logging.getLogger("eda_mcp.eldo_client")

class EldoClient:
    """
    High-level client for managing and executing Mentor Graphics/Siemens Eldo simulations
    over a RemoteSession SSH transport.
    """
    def __init__(self, session: RemoteSession):
        self.session = session
        self.workdir = None

    def run_script(self, script_path: str = "", work_dir: str = "~") -> str:
        """
        Runs Eldo simulation on a batch script or netlist file.
        """
        self.session.connect()
        target_dir = work_dir or self.workdir or "~"
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        self.session.execute_command(f"cd {safe_dir}")

        if not script_path.strip():
            return "Error: 'command' argument specifying script/netlist path is required for action='run_script'."

        cmd = f"eldo {shlex.quote(script_path.strip())}"
        exit_code, stdout, stderr = self.session.execute_command(cmd)
        output = []
        output.append(f"[Eldo Batch Script Run]: {cmd}")
        output.append(f"Exit Status: {exit_code}")
        if stdout.strip():
            output.append(f"\n--- STDOUT ---\n{stdout}")
        if stderr.strip():
            output.append(f"\n--- STDERR ---\n{stderr}")
        return "\n".join(output)

    def run_interactive(self, command: str = "", work_dir: str = "~") -> str:
        """
        Executes interactive Eldo command.
        """
        self.session.connect()
        target_dir = work_dir or self.workdir or "~"
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        self.session.execute_command(f"cd {safe_dir}")

        if not command.strip():
            return "Eldo interactive execution placeholder. Pass an Eldo command to execute."

        exit_code, stdout, stderr = self.session.execute_command(command)
        output = []
        output.append(f"Exit Status: {exit_code}")
        if stdout.strip():
            output.append(f"\n--- STDOUT ---\n{stdout}")
        if stderr.strip():
            output.append(f"\n--- STDERR ---\n{stderr}")
        return "\n".join(output)
