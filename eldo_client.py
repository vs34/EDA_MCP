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
        self.interactive_pid = None
        self.interactive_keeper_pid = None
        self.interactive_cir = None

    def initialize(self, work_dir: str = "~/Desktop/eldo") -> str:
        """
        Navigates to work_dir (default: ~/Desktop/eldo), sets working directory for Eldo,
        and creates interctive.fifo FIFO pipe and intective_out.txt file.
        """
        self.session.connect()
        target_dir = work_dir.strip() if work_dir and work_dir.strip() else "~/Desktop/eldo"
        self.workdir = target_dir
        
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        init_cmd = f"mkdir -p {safe_dir} && cd {safe_dir}"
        exit_code, stdout, stderr = self.session.execute_command(init_cmd)
        
        if exit_code != 0:
            return f"Failed to initialize Eldo working directory at {target_dir} (Exit code {exit_code}): {stdout}"

        return f"Eldo session initialized in {target_dir}."

    def is_interactive_running(self) -> bool:
        """
        Checks if the background Eldo interactive process is alive using kill -0.
        """
        if not self.interactive_pid:
            return False
        
        check_cmd = f"kill -0 {self.interactive_pid} 2>/dev/null"
        exit_code, _, _ = self.session.execute_command(check_cmd)
        if exit_code != 0:
            self.interactive_pid = None
            self.interactive_keeper_pid = None
            self.interactive_cir = None
            return False
        return True

    def start_interactive(self, netlist_file: str = "", work_dir: str = "") -> str:
        """
        Spawns an interactive Eldo REPL session (eldo -inter) using execute_interactive_stream.
        """
        self.session.connect()
        target_dir = (work_dir.strip() if work_dir and work_dir.strip() else None) or self.workdir or "~/Desktop/eldo"
        self.workdir = target_dir
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)

        self.session.execute_command(f"mkdir -p {safe_dir} && cd {safe_dir}")

        cir_file = netlist_file.strip() if netlist_file else ""
        cmd = f"eldo {shlex.quote(cir_file)} -inter" if cir_file else "eldo -inter"
        
        # Launch interactive Eldo and wait for eldo> prompt
        exit_code, stdout, stderr = self.session.execute_interactive_stream(cmd, prompt_regex=r"(eldo>\s*$|\bELDO>\s*$)", timeout=15.0)

        self.interactive_active = True
        self.interactive_cir = cir_file or "interactive"
        return f"Started interactive Eldo REPL session for '{self.interactive_cir}' in {target_dir}.\nOutput:\n{stdout.strip()}"

    def run_interactive(self, command: str = "", work_dir: str = "", timeout: float = 10.0) -> str:
        """
        Sends an interactive command to the active Eldo REPL session and streams the response in real-time.
        """
        self.session.connect()
        target_dir = (work_dir.strip() if work_dir and work_dir.strip() else None) or self.workdir or "~/Desktop/eldo"
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)

        if not getattr(self, "interactive_active", False):
            clean_cmd = command.strip()
            if clean_cmd.endswith(".cir") or clean_cmd.endswith(".sp") or clean_cmd.endswith(".net"):
                return self.start_interactive(netlist_file=clean_cmd, work_dir=work_dir)
            return self.start_interactive(netlist_file="", work_dir=work_dir)

        if not command.strip():
            return f"Interactive Eldo REPL is active for '{self.interactive_cir}'. Provide a command to send to Eldo."

        cmd_str = command.strip()
        exit_code, stdout, stderr = self.session.execute_interactive_stream(cmd_str, prompt_regex=r"(eldo>\s*$|\bELDO>\s*$)", timeout=timeout)

        output = []
        output.append(f"[Interactive Eldo]: {cmd_str}")
        if stdout.strip():
            output.append(f"\n--- OUTPUT ---\n{stdout.strip()}")

        return "\n".join(output)

    def stop_interactive(self, work_dir: str = "") -> str:
        """
        Terminates the interactive Eldo REPL session cleanly.
        """
        if not getattr(self, "interactive_active", False):
            return "No interactive Eldo session is currently active."

        try:
            self.session.execute_interactive_stream("quit", prompt_regex=r"(%|>|\$)\s*$", timeout=5.0)
        except Exception:
            pass

        self.interactive_active = False
        self.interactive_cir = None
        return "Stopped interactive Eldo session."

    def read_extract(self, work_dir: str = "") -> str:
        """
        Reads the .extract measurement file generated by the most recent Eldo simulation run.
        """
        self.session.connect()
        target_dir = (work_dir.strip() if work_dir and work_dir.strip() else None) or self.workdir or "~/Desktop/eldo"
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        self.session.execute_command(f"cd {safe_dir}")

        # Auto-detect the most recently created .extract file
        find_extract_cmd = "ls -t *.extract 2>/dev/null | head -n 1"
        exit_code, stdout, _ = self.session.execute_command(find_extract_cmd)
        extract_file = stdout.strip()

        if not extract_file:
            return f"No .extract measurement file found in working directory ({target_dir}). Ensure netlist ran successfully and contains .EXTRACT or .MEASURE directives."

        try:
            content = self.session.read_file(extract_file)
            output = []
            output.append(f"[Eldo Extracted Measurement File]: {extract_file}")
            output.append(f"\n--- CONTENT ({extract_file}) ---\n{content}")
            return "\n".join(output)
        except Exception as e:
            return f"Error reading extracted measurement file '{extract_file}': {str(e)}"

    def run_terminal_command(self, command: str, work_dir: str = "", timeout: float = 60.0) -> str:
        """
        Executes a terminal/shell command in the dedicated Eldo SSH terminal session.
        Shares working directory and persistent shell environment with Eldo simulation execution.
        """
        self.session.connect()
        target_dir = (work_dir.strip() if work_dir and work_dir.strip() else None) or self.workdir or "~/Desktop/eldo"
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        self.session.execute_command(f"cd {safe_dir}")
            
        exit_code, stdout, stderr = self.session.execute_command(command, timeout=timeout)
        output = []
        output.append(f"[Eldo Terminal Command]: {command}")
        output.append(f"Exit Status: {exit_code}")
        if stdout.strip():
            output.append(f"\n--- STDOUT ---\n{stdout.strip()}")
        if stderr.strip():
            output.append(f"\n--- STDERR ---\n{stderr.strip()}")
        return "\n".join(output)
