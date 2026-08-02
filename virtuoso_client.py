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
        Navigates to work_dir and launches virtuoso -nograph interactive REPL session using execute_interactive_stream.
        """
        self.session.connect()
        target_dir = work_dir.strip() if work_dir and work_dir.strip() else "~/Desktop/cmos65"
        self.interactive_workdir = target_dir
        
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        self.session.execute_command(f"cd {safe_dir}")
        
        # Launch virtuoso -nograph and wait for SKILL prompt (> or CIW>)
        cmd = "virtuoso -nograph"
        exit_code, stdout, stderr = self.session.execute_interactive_stream(cmd, prompt_regex=r"(>\s*$|\bCIW>\s*$)", timeout=15.0)
        
        self.interactive_active = True
        return f"Virtuoso standalone REPL session (virtuoso -nograph) initialized in {target_dir}.\nOutput:\n{stdout.strip()}"

    def start_interactive(self, work_dir: str = "~/Desktop/cmos65") -> str:
        return self.start_standalone(work_dir=work_dir)

    def run_standalone(self, command: str = "", work_dir: str = "", timeout: float = 10.0) -> str:
        """
        Executes SKILL statements directly in the active virtuoso -nograph interactive REPL stream.
        """
        self.session.connect()
        
        if not self.interactive_active:
            target_dir = work_dir or self.interactive_workdir or "~/Desktop/cmos65"
            init_res = self.start_standalone(work_dir=target_dir)
            if "Failed" in init_res:
                return init_res

        clean_skill = self._clean_skill_command(command)
        if not clean_skill:
            return "Error: Empty SKILL command provided for standalone Virtuoso session."

        exit_code, stdout, stderr = self.session.execute_interactive_stream(clean_skill, prompt_regex=r"(>\s*$|\bCIW>\s*$)", timeout=timeout)

        output = []
        output.append(f"[Standalone Virtuoso (virtuoso -nograph)]: {clean_skill}")
        if stdout.strip():
            output.append(f"\n--- STDOUT ---\n{stdout.strip()}")

        return "\n".join(output)

    def run_interactive(self, command: str = "", work_dir: str = "", timeout: float = 10.0) -> str:
        return self.run_standalone(command=command, work_dir=work_dir, timeout=timeout)

    def stop_standalone(self) -> str:
        """
        Stops and closes the standalone Virtuoso REPL session cleanly.
        """
        if not self.interactive_active:
            return "No standalone Virtuoso session is currently active."

        try:
            self.session.execute_interactive_stream("exit()", prompt_regex=r"(%|>|\$)\s*$", timeout=5.0)
        except Exception:
            pass

        self.interactive_active = False
        self.interactive_workdir = None
        return "Standalone Virtuoso REPL session (virtuoso -nograph) terminated cleanly."

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

    def assisted_run(self, skill_code: str, timeout: float = 30.0) -> str:
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
            
        # If timeout reached, return whatever is in mcp_output.txt or a diagnostic timeout notice
        try:
            current_content = self.session.read_file(output_file)
            if current_content.strip():
                return f"[Timeout Warning: RESULT marker not detected within {timeout}s]\nPartial Output:\n{current_content}\n\nNote: Cadence Virtuoso may be blocked by a modal UI dialog (e.g. geOpen prompt, unlinked master confirmation, schCheck dialog, or save prompt). Please check the Virtuoso GUI or increase the 'timeout' parameter."
        except Exception:
            pass
            
        return f"Execution timed out ({timeout}s). No response received from Virtuoso in {output_file}.\nPossible causes:\n1. Virtuoso GUI is waiting for user interaction on a modal dialog (e.g., geOpen, schCheck unlinked master prompt, file overwrite prompt).\n2. The SKILL script contains a long-running execution (e.g., system(...) shell call, netlist check, heavy simulation setup).\nRemedies: Pass a larger 'timeout' parameter or interact with/close the modal dialog in the Virtuoso GUI on the remote server."

    def run(self, skill_code: str, timeout: float = 10.0) -> str:
        return self.assisted_run(skill_code=skill_code, timeout=timeout)

    def run_terminal_command(self, command: str, work_dir: str = "", timeout: float = 60.0) -> str:
        """
        Executes a terminal/shell command in the dedicated Virtuoso SSH terminal session.
        Shares working directory and persistent shell environment with Virtuoso assisted mode.
        """
        self.session.connect()
        target_dir = (work_dir.strip() if work_dir and work_dir.strip() else None) or self.workdir
        if target_dir:
            safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
            self.session.execute_command(f"cd {safe_dir}")
            
        exit_code, stdout, stderr = self.session.execute_command(command, timeout=timeout)
        output = []
        output.append(f"[Virtuoso Terminal Command]: {command}")
        output.append(f"Exit Status: {exit_code}")
        if stdout.strip():
            output.append(f"\n--- STDOUT ---\n{stdout.strip()}")
        if stderr.strip():
            output.append(f"\n--- STDERR ---\n{stderr.strip()}")
        return "\n".join(output)

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
        return "\n".join(output)
