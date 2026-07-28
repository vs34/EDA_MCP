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

    def start_interactive(self, work_dir: str = "~/Desktop/cmos65") -> str:
        """
        Navigates to work_dir and launches virtuoso -nograph in the foreground of the dedicated terminal session.
        """
        self.session.connect()
        target_dir = work_dir.strip() if work_dir and work_dir.strip() else "~/Desktop/cmos65"
        self.interactive_workdir = target_dir
        
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        
        # Navigate to safe_dir and launch virtuoso -nograph in foreground
        init_cmd = f"cd {safe_dir} && virtuoso -nograph\n"
        self.session.process.stdin.write(init_cmd)
        self.session.process.stdin.flush()
        
        # Send a sentinel print statement to detect when Virtuoso -nograph initialization is complete
        sentinel = "__VIRTUOSO_INIT_READY__"
        self.session.process.stdin.write(f'println("{sentinel}")\n')
        self.session.process.stdin.flush()
        
        start_time = time.time()
        output_lines = []
        
        while time.time() - start_time < 15.0:
            line = self.session.process.stdout.readline()
            if not line:
                break
            output_lines.append(line)
            if sentinel in line:
                break

        self.interactive_active = True
        return f"Foreground Virtuoso interactive session (virtuoso -nograph) initialized in {target_dir}."

    def run_interactive(self, command: str = "", work_dir: str = "", timeout: float = 10.0) -> str:
        """
        Executes a SKILL statement directly in the foreground virtuoso -nograph terminal session.
        """
        self.session.connect()
        
        if not self.interactive_active:
            target_dir = work_dir or self.interactive_workdir or "~/Desktop/cmos65"
            init_res = self.start_interactive(work_dir=target_dir)
            if "Failed" in init_res:
                return init_res

        clean_skill = self._clean_skill_command(command)
        if not clean_skill:
            return "Error: Empty SKILL command provided for interactive Virtuoso session."

        sentinel = f"__SKILL_DONE_{os.urandom(4).hex()}__"
        
        # Send SKILL command followed by a sentinel print to Virtuoso's stdin
        exec_str = f'{clean_skill}\nprintln("{sentinel}")\n'
        self.session.process.stdin.write(exec_str)
        self.session.process.stdin.flush()

        # Read lines from Virtuoso stdout until sentinel is found
        start_time = time.time()
        output_lines = []
        
        while time.time() - start_time < timeout:
            line = self.session.process.stdout.readline()
            if not line:
                self.interactive_active = False
                return f"Interactive Virtuoso session closed unexpectedly.\nPartial Output:\n" + "".join(output_lines)
            if sentinel in line:
                break
            output_lines.append(line)

        output_str = "".join(output_lines).strip()
        output = []
        output.append(f"[Interactive Virtuoso (virtuoso -nograph)]: {clean_skill}")
        if output_str:
            output.append(f"\n--- OUTPUT ---\n{output_str}")
        else:
            output.append("\n(Command executed cleanly with no stdout returned)")

        return "\n".join(output)

    def stop_interactive(self) -> str:
        """
        Stops and closes the interactive Virtuoso session cleanly by sending exit() to Virtuoso.
        """
        if not self.interactive_active:
            return "No interactive Virtuoso session is currently active."

        try:
            self.session.process.stdin.write("exit()\n")
            self.session.process.stdin.flush()
        except Exception:
            pass

        self.interactive_active = False
        self.interactive_workdir = None
        return "Interactive Virtuoso session (virtuoso -nograph) terminated cleanly."

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
