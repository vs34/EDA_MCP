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
        init_cmd = f"mkdir -p {safe_dir} && cd {safe_dir} && rm -f interctive.fifo && mkfifo interctive.fifo && touch intective_out.txt"
        exit_code, stdout, stderr = self.session.execute_command(init_cmd)
        
        if exit_code != 0:
            return f"Failed to initialize Eldo working directory at {target_dir} (Exit code {exit_code}): {stdout}"

        return f"Eldo session initialized in {target_dir}. Created interctive.fifo and intective_out.txt."

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

    def start_interactive(self, netlist_file: str, work_dir: str = "") -> str:
        """
        Initializes and spawns a persistent interactive Eldo background process
        listening on interctive.fifo and redirecting output to intective_out.txt.
        """
        self.session.connect()
        target_dir = (work_dir.strip() if work_dir and work_dir.strip() else None) or self.workdir or "~/Desktop/eldo"
        self.workdir = target_dir
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)

        if not netlist_file.strip():
            return "Error: Please specify the name of the netlist (.cir) file to create an interactive process."

        cir_file = netlist_file.strip()

        # Check if an interactive session is already running
        if self.is_interactive_running():
            return f"An interactive Eldo session (PID {self.interactive_pid}) is already running for '{self.interactive_cir}'."

        # Setup FIFO and background processes
        setup_cmd = (
            f"mkdir -p {safe_dir} && cd {safe_dir} && "
            f"rm -f interctive.fifo && mkfifo interctive.fifo && touch intective_out.txt && "
            f"tail -f /dev/null > interctive.fifo & echo $! && "
            f"eldo {shlex.quote(cir_file)} -inter < interctive.fifo >& intective_out.txt & echo $!"
        )
        exit_code, stdout, stderr = self.session.execute_command(setup_cmd)
        
        if exit_code != 0:
            return f"Failed to start interactive Eldo process for '{cir_file}' (Exit code {exit_code}): {stderr or stdout}"

        lines = [line.strip() for line in stdout.splitlines() if line.strip().isdigit()]
        if len(lines) >= 2:
            self.interactive_keeper_pid = lines[0]
            self.interactive_pid = lines[1]
        elif len(lines) == 1:
            self.interactive_pid = lines[0]

        self.interactive_cir = cir_file
        return f"Started interactive Eldo process (PID {self.interactive_pid}) for '{cir_file}' in {target_dir}."

    def run_interactive(self, command: str = "", work_dir: str = "") -> str:
        """
        Sends an interactive command to the running Eldo session via interctive.fifo
        and reads the response from intective_out.txt.
        """
        self.session.connect()
        target_dir = (work_dir.strip() if work_dir and work_dir.strip() else None) or self.workdir or "~/Desktop/eldo"
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)
        self.session.execute_command(f"cd {safe_dir}")

        # Verify process health
        if not self.is_interactive_running():
            # Auto-start if command looks like a netlist file
            clean_cmd = command.strip()
            if clean_cmd.endswith(".cir") or clean_cmd.endswith(".sp") or clean_cmd.endswith(".net"):
                return self.start_interactive(netlist_file=clean_cmd, work_dir=work_dir)
            return "No Eldo interactive process is currently running. What is the name of the .cir file with which you want to create an interactive process?"

        if not command.strip():
            return f"Interactive Eldo process (PID {self.interactive_pid}) for '{self.interactive_cir}' is active. Provide a command to send to Eldo."

        cmd_str = command.strip()

        # 1. Clear output log: cp /dev/null intective_out.txt
        # 2. Write command to FIFO: echo "cmd" > interctive.fifo
        fifo_cmd = (
            f"cp /dev/null intective_out.txt && "
            f"echo {shlex.quote(cmd_str)} > interctive.fifo"
        )
        exit_code, stdout, stderr = self.session.execute_command(fifo_cmd)

        if exit_code != 0:
            return f"Failed to send command into interctive.fifo (Exit code {exit_code}): {stderr or stdout}"

        # Allow time for Eldo to process & write output
        time.sleep(0.3)

        # Read output from intective_out.txt
        try:
            out_content = self.session.read_file("intective_out.txt")
            if not out_content.strip():
                # Retry once after a brief pause if output file is empty
                time.sleep(0.5)
                out_content = self.session.read_file("intective_out.txt")
        except Exception as e:
            out_content = f"Error reading intective_out.txt: {str(e)}"

        output = []
        output.append(f"[Interactive Eldo (PID {self.interactive_pid})]: {cmd_str}")
        if out_content.strip():
            output.append(f"\n--- OUTPUT (intective_out.txt) ---\n{out_content}")
        else:
            output.append("\n(Command sent successfully. No output generated in intective_out.txt)")

        return "\n".join(output)

    def stop_interactive(self, work_dir: str = "") -> str:
        """
        Terminates the interactive Eldo background process and keeper.
        """
        self.session.connect()
        target_dir = (work_dir.strip() if work_dir and work_dir.strip() else None) or self.workdir or "~/Desktop/eldo"
        safe_dir = f"$HOME{target_dir[1:]}" if target_dir.startswith("~") else shlex.quote(target_dir)

        if not self.interactive_pid:
            return "No interactive Eldo process is currently running."

        pid = self.interactive_pid
        keeper_pid = self.interactive_keeper_pid
        cir_file = self.interactive_cir

        stop_cmd = f"cd {safe_dir} && kill -9 {pid} {keeper_pid or ''} 2>/dev/null"
        self.session.execute_command(stop_cmd)

        self.interactive_pid = None
        self.interactive_keeper_pid = None
        self.interactive_cir = None

        return f"Stopped interactive Eldo session (PID {pid}) for '{cir_file}'."

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
