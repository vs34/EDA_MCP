import os
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
        self.interactive_active = False
        self.interactive_workdir = None

    def start_standalone(self, work_dir: str = "~/Desktop/cmos65") -> str:
        """
        Navigates to work_dir in the dedicated standalone terminal session.
        """
        self.session.connect()
        target_dir = work_dir.strip() if work_dir and work_dir.strip() else "~/Desktop/cmos65"
        self.interactive_workdir = target_dir
        
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        cmd = f"cd {safe_dir}"
        exit_code, stdout, stderr = self.session.execute_command(cmd)
        
        if exit_code != 0:
            return f"Failed to navigate to standalone workspace {target_dir}: {stderr or stdout}"

        self.interactive_active = True
        return f"Virtuoso standalone terminal session initialized in {target_dir}."

    def start_interactive(self, work_dir: str = "~/Desktop/cmos65") -> str:
        return self.start_standalone(work_dir=work_dir)

    def run_standalone(self, command: str = "", work_dir: str = "") -> str:
        """
        Executes a command directly on the dedicated standalone terminal session using execute_command.
        """
        self.session.connect()
        
        target_dir = (work_dir.strip() if work_dir and work_dir.strip() else None) or self.interactive_workdir or "~/Desktop/cmos65"
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        self.session.execute_command(f"cd {safe_dir}")

        if not command.strip():
            return "Error: 'command' argument is required for action='standalone'."

        clean_skill = self._clean_skill_command(command)
        exit_code, stdout, stderr = self.session.execute_command(clean_skill)

        output = []
        output.append(f"[Standalone Terminal Execution]: {clean_skill}")
        output.append(f"Exit Status: {exit_code}")
        if stdout.strip():
            output.append(f"\n--- STDOUT ---\n{stdout}")
        if stderr.strip():
            output.append(f"\n--- STDERR ---\n{stderr}")

        return "\n".join(output)

    def run_interactive(self, command: str = "", work_dir: str = "") -> str:
        return self.run_standalone(command=command, work_dir=work_dir)

    def stop_standalone(self) -> str:
        """
        Stops and closes the standalone terminal session cleanly.
        """
        if not self.interactive_active:
            return "No standalone terminal session is currently active."

        self.interactive_active = False
        self.interactive_workdir = None
        return "Standalone terminal session closed."

    def stop_interactive(self) -> str:
        return self.stop_standalone()

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
        
        safe_dir = f"$HOME{work_dir[1:]}" if work_dir.startswith("~") else shlex.quote(work_dir)
        cmd = f"cd {safe_dir}"
        exit_code, stdout, stderr = self.session.execute_command(cmd)
        
        if exit_code != 0:
            return f"Failed to initialize Virtuoso (Exit code {exit_code}): {stdout}"

        return f"Virtuoso initialization complete in {work_dir}."

    def assisted_run(self, skill_code: str, timeout: float = 10.0) -> str:
        """
        Executes a SKILL command in Human+AI assisted mode via IPC pipe and polls mcp_output.txt for output.
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
            
        # Polling loop: wait for RESULT: marker in mcp_output.txt
        start_time = time.time()
        poll_interval = 0.3
        
        while time.time() - start_time < timeout:
            try:
                content = self.session.read_file(output_file)
                if content and "RESULT:" in content:
                    return content
            except Exception:
                pass
            time.sleep(poll_interval)
            
        # If timeout reached, return whatever is in mcp_output.txt or a timeout notice
        try:
            current_content = self.session.read_file(output_file)
            if current_content.strip():
                return f"[Timeout Warning: RESULT marker not detected within {timeout}s]\n{current_content}"
        except Exception:
            pass
            
        return f"Execution timed out ({timeout}s). No response received from Virtuoso in {output_file}."

    def run(self, skill_code: str, timeout: float = 10.0) -> str:
        return self.assisted_run(skill_code=skill_code, timeout=timeout)

    def exit(self) -> str:
        """
        Gracefully terminates Virtuoso session by sending SKILL exit command first,
        falling back to kill -9 <PID> if necessary.
        """
        self.session.connect()
        if self.workdir:
            safe_dir = f"$HOME{self.workdir[1:]}" if self.workdir.startswith("~") else shlex.quote(self.workdir)
            self.session.execute_command(f"cd {safe_dir}")
            
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
