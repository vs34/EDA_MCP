import shlex
import time
import logging
from ssh_client import RemoteSession

logger = logging.getLogger("eda_mcp.virtuoso_client")

class VirtuosoClient:
    """
    High-level client for managing and executing SKILL commands in Cadence Virtuoso
    over a RemoteSession SSH transport.
    """
    def __init__(self, session: RemoteSession):
        self.session = session
        self.pid = None
        self.workdir = None

    def _clean_skill_command(self, cmd_str: str) -> str:
        """
        Strips ';;' comments and converts multi-line SKILL statements into a single line string.
        """
        clean_lines = []
        for line in cmd_str.splitlines():
            if ";;" in line:
                comment_idx = line.find(";;")
                line = line[:comment_idx]
            stripped = line.strip()
            if stripped:
                clean_lines.append(stripped)
        return " ".join(clean_lines)

    def initialize(self, work_dir: str = "~/Desktop/cmos65") -> str:
        """
        Navigates to work_dir, executes MCP_initalize.sh, and tracks the Virtuoso PID.
        """
        self.session.connect()
        self.workdir = work_dir
        
        # Future development: This will handle full agentic flow (e.g., virtuoso -nograph and automated code development later on)
        safe_dir = f"$HOME{work_dir[1:]}" if work_dir.startswith("~") else shlex.quote(work_dir)
        cmd = f"cd {safe_dir}"
        exit_code, stdout, stderr = self.session.execute_command(cmd)
        
        if exit_code != 0:
            return f"Failed to initialize Virtuoso (Exit code {exit_code}): {stdout}"

        return f"Virtuoso initialization complete in {work_dir}."

    def run(self, skill_code: str, timeout: float = 10.0) -> str:
        """
        Executes a SKILL command in Virtuoso via FIFO pipe and polls mcp_output.txt for output.
        """
        self.session.connect()
        if self.workdir:
            safe_dir = f"$HOME{self.workdir[1:]}" if self.workdir.startswith("~") else shlex.quote(self.workdir)
            self.session.execute_command(f"cd {safe_dir}")
            
        clean_skill = self._clean_skill_command(skill_code)
        if not clean_skill:
            return "Error: Empty SKILL command after removing comments."
            
        output_file = "mcp_output.txt"
        
        # Clear mcp_output.txt before sending command
        self.session.execute_command(f"rm -f {output_file} && touch {output_file}")
        
        # Write command directly to FIFO pipe MCP.command
        fifo_write_cmd = f"echo {shlex.quote(clean_skill)} > MCP.command"
        exit_code, out, _ = self.session.execute_command(fifo_write_cmd)
        if exit_code != 0:
            return f"Failed to send command to Virtuoso FIFO pipe: {out}"
            
        try:
            return self.session.read_file(output_file)
        except Exception as e:
            return f"Command sent to MCP.command (Error reading output file: {e})"

    def exit(self) -> str:
        """
        Gracefully terminates Virtuoso session by sending SKILL exit command first,
        falling back to kill -9 <PID> if necessary.
        """
        self.session.connect()
        if self.workdir:
            self.session.execute_command(f"cd {shlex.quote(self.workdir)}")
            
        output = []
        try:
            self.session.execute_command("echo 'exit()' > MCP.command")
            output.append("Sent exit() to Virtuoso FIFO pipe.")
        except Exception as e:
            output.append(f"Failed to send exit() command: {e}")
            
        time.sleep(2)
        
        # if self.pid:
        #     check_cmd = f"ps -p {self.pid}"
        #     exit_code, out, _ = self.session.execute_command(check_cmd)
        #     if exit_code == 0 and str(self.pid) in out:
        #         output.append(f"Virtuoso (PID {self.pid}) is still alive. Sending kill -9...")
        #         self.session.execute_command(f"kill -9 {self.pid}")
        #         output.append(f"Killed Virtuoso PID {self.pid}.")
        #     else:
        #         output.append(f"Virtuoso (PID {self.pid}) has cleanly exited.")
        #     self.pid = None
        # else:
        #     output.append("No recorded Virtuoso PID to kill.")
            
        return "\n".join(output)
