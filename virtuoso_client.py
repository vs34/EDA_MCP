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

    def initialize(self, work_dir: str = "~/Desktop/cmos65", display: str = ":0") -> str:
        """
        Navigates to work_dir, deploys MCP_initialize.sh, sets DISPLAY, runs script, and tracks Virtuoso PID.
        """
        self.session.connect()
        self.workdir = work_dir
        
        init_script_content = (
            "#!/bin/csh\n"
            "if ( ! -e MCP.command ) then\n"
            "    mkfifo MCP.command\n"
            "    echo 'Created FIFO pipe: MCP.command'\n"
            "else\n"
            "    echo 'FIFO pipe MCP.command already exists.'\n"
            "endif\n\n"
            "if ( -e .cshrc_cmos065 ) then\n"
            "    source .cshrc_cmos065\n"
            "endif\n\n"
            "if ( ! $?DISPLAY ) then\n"
            f"    setenv DISPLAY {display}\n"
            "endif\n\n"
            "virtuoso >& virtuoso_launch.log &\n"
        )
        
        remote_script = f"{work_dir}/MCP_initialize.sh"
        try:
            self.session.write_file(remote_script, init_script_content)
            self.session.execute_command(f"chmod +x {shlex.quote(remote_script)}")
        except Exception as e:
            logger.warning(f"Could not deploy script to {remote_script}: {e}")

        cmd = f"cd {shlex.quote(work_dir)} && env DISPLAY={shlex.quote(display)} csh MCP_initialize.sh &"
        exit_code, stdout, stderr = self.session.execute_command(cmd)
        
        if exit_code != 0:
            return f"Failed to initialize Virtuoso (Exit code {exit_code}): {stdout}"

        # Wait 3 seconds for Virtuoso process to initialize
        time.sleep(3)

        # Fetch Virtuoso PID for current user
        pid_cmd = "pgrep -u $USER -f virtuoso | head -n 1"
        _, pid_stdout, _ = self.session.execute_command(pid_cmd)
        pid_str = pid_stdout.strip()
        if pid_str.isdigit():
            self.pid = int(pid_str)
        
        pid_info = f"PID: {self.pid}" if self.pid else "PID: unknown"
        return f"Virtuoso initialization complete in {work_dir}. ({pid_info})\nOutput:\n{stdout.strip()}"

    def run(self, skill_code: str, timeout: float = 10.0) -> str:
        """
        Executes a SKILL command in Virtuoso via FIFO pipe and polls mcp_output.txt for output.
        """
        self.session.connect()
        if self.workdir:
            self.session.execute_command(f"cd {shlex.quote(self.workdir)}")
            
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
            self.session.execute_command(f"cd {shlex.quote(self.workdir)}")
            
        output = []
        try:
            self.session.execute_command("echo 'exit()' > MCP.command")
            output.append("Sent exit() to Virtuoso FIFO pipe.")
        except Exception as e:
            output.append(f"Failed to send exit() command: {e}")
            
        time.sleep(2)
        
        if self.pid:
            check_cmd = f"ps -p {self.pid}"
            exit_code, out, _ = self.session.execute_command(check_cmd)
            if exit_code == 0 and str(self.pid) in out:
                output.append(f"Virtuoso (PID {self.pid}) is still alive. Sending kill -9...")
                self.session.execute_command(f"kill -9 {self.pid}")
                output.append(f"Killed Virtuoso PID {self.pid}.")
            else:
                output.append(f"Virtuoso (PID {self.pid}) has cleanly exited.")
            self.pid = None
        else:
            output.append("No recorded Virtuoso PID to kill.")
            
        return "\n".join(output)
