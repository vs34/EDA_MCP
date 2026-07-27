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

    def initialize(self, work_dir: str = "~") -> str:
        """
        Navigates to work_dir and initializes the Eldo environment.
        """
        self.session.connect()
        self.workdir = work_dir
        
        safe_dir = f"$HOME{work_dir[1:]}" if work_dir.startswith("~") else shlex.quote(work_dir)
        cmd = f"cd {safe_dir}"
        exit_code, stdout, stderr = self.session.execute_command(cmd)
        
        if exit_code != 0:
            return f"Failed to initialize Eldo (Exit code {exit_code}): {stdout}"

        return f"Eldo initialization complete in {work_dir}."

    def run(self, command: str = "") -> str:
        """
        Executes Eldo simulation command.
        """
        self.session.connect()
        if self.workdir:
            safe_dir = f"$HOME{self.workdir[1:]}" if self.workdir.startswith("~") else shlex.quote(self.workdir)
            self.session.execute_command(f"cd {safe_dir}")
            
        if not command.strip():
            return "Eldo simulation placeholder. Pass an Eldo command or netlist path to execute."

        exit_code, stdout, stderr = self.session.execute_command(command)
        output = []
        output.append(f"Exit Status: {exit_code}")
        if stdout.strip():
            output.append(f"\n--- STDOUT ---\n{stdout}")
        if stderr.strip():
            output.append(f"\n--- STDERR ---\n{stderr}")
        return "\n".join(output)

    def exit(self) -> str:
        """
        Terminates the Eldo session.
        """
        return "Eldo session closed."
