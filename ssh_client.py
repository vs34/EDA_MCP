import os
import json
import logging
import shlex
import subprocess
import base64

logger = logging.getLogger("eda_mcp.ssh_client")

class RemoteSession:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.process = None
        self.load_config()
        
    def load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
            
        self.ssh_host = self.config.get("ssh_host", "eda-uni")
        self.env_setup_cmd = self.config.get("env_setup_cmd", "source /cadence/cshrc")

    def connect(self):
        if self.process is not None and self.process.poll() is None:
            return
            
        logger.info(f"Establishing persistent SSH shell session to: {self.ssh_host}")
        try:
            # Start the ssh process executing csh on the remote host
            # We merge stderr into stdout (stderr=subprocess.STDOUT) to easily interleave them,
            # which mimics a real terminal and prevents pipe buffer deadlocks.
            self.process = subprocess.Popen(
                ['ssh', '-o', 'BatchMode=yes', self.ssh_host, 'csh'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0  # Unbuffered
            )
            
            # Sourcing the CAD environment script on startup
            init_sentinel = "__CSH_INIT_DONE__"
            init_cmd = f"{self.env_setup_cmd}; echo '{init_sentinel}:'$status\n"
            self.process.stdin.write(init_cmd)
            self.process.stdin.flush()
            
            # Read stdout until the initialization is complete
            while True:
                line = self.process.stdout.readline()
                if not line:
                    raise RuntimeError("SSH connection lost during shell initialization.")
                if init_sentinel in line:
                    break
                    
            logger.info("Persistent SSH shell session established and sourced successfully.")
        except Exception as e:
            self.close()
            logger.error(f"Failed to connect and initialize persistent shell: {e}")
            raise e

    def close(self):
        if self.process:
            logger.info("Closing persistent SSH session...")
            try:
                # Send exit to csh
                self.process.stdin.write("exit\n")
                self.process.stdin.flush()
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        logger.info("SSH connection closed.")

    def execute_command(self, cmd: str) -> tuple[int, str, str]:
        """
        Executes a command on the remote host in the persistent shell session.
        Keeps directory state (cd) and environment variables across calls.
        Returns: (exit_status, stdout_string, stderr_string)
        """
        self.connect()
        sentinel = f"__CMD_FINISHED_{os.urandom(4).hex()}__"
        
        # csh executes command and prints the sentinel with exit status
        full_cmd = f"{cmd}; echo '{sentinel}:'$status\n"
        logger.debug(f"Sending command: {cmd}")
        
        self.process.stdin.write(full_cmd)
        self.process.stdin.flush()
        
        # Read lines from stdout until we see the sentinel
        output_lines = []
        exit_code = 0
        while True:
            line = self.process.stdout.readline()
            if not line:
                self.close()
                raise RuntimeError("SSH connection lost during command execution.")
            if sentinel in line:
                parts = line.strip().split(":")
                if len(parts) > 1:
                    try:
                        exit_code = int(parts[1])
                    except ValueError:
                        exit_code = 0
                break
            output_lines.append(line)
            
        stdout_str = "".join(output_lines)
        # Stderr is merged into stdout for the terminal timeline, so we return empty stderr
        return exit_code, stdout_str, ""

    def read_file(self, remote_path: str) -> str:
        """
        Reads a file from the remote server.
        """
        self.connect()
        logger.info(f"Reading remote file: {remote_path}")
        
        quoted_path = shlex.quote(remote_path)
        sentinel = f"__READ_FINISHED_{os.urandom(4).hex()}__"
        
        # csh multi-line if statement to check path status
        cmd = (
            f"if ( -d {quoted_path} ) then\n"
            f"  echo '{sentinel}:is_dir'\n"
            f"else if ( -e {quoted_path} ) then\n"
            f"  base64 {quoted_path}; echo '{sentinel}:'$status\n"
            f"else\n"
            f"  echo '{sentinel}:404'\n"
            f"endif\n"
        )
        
        self.process.stdin.write(cmd)
        self.process.stdin.flush()
        
        output_lines = []
        result_status = "0"
        
        while True:
            line = self.process.stdout.readline()
            if not line:
                self.close()
                raise RuntimeError("SSH connection lost during file read.")
            if sentinel in line:
                parts = line.strip().split(":")
                if len(parts) > 1:
                    result_status = parts[-1]
                break
            output_lines.append(line)
            
        if result_status == "404":
            raise FileNotFoundError(f"File not found: {remote_path}")
        elif result_status == "is_dir":
            raise IsADirectoryError(f"Path is a directory: {remote_path}")
            
        # If base64 failed (e.g. status was non-zero like 1 or command not found)
        if result_status != "0":
            cat_sentinel = f"__CAT_FINISHED_{os.urandom(4).hex()}__"
            cat_cmd = f"cat {quoted_path}; echo '{cat_sentinel}:'$status\n"
            self.process.stdin.write(cat_cmd)
            self.process.stdin.flush()
            
            cat_lines = []
            cat_exit_code = 0
            while True:
                line = self.process.stdout.readline()
                if not line:
                    self.close()
                    raise RuntimeError("SSH connection lost during fallback file read.")
                if cat_sentinel in line:
                    parts = line.strip().split(":")
                    if len(parts) > 1:
                        try:
                            cat_exit_code = int(parts[-1])
                        except ValueError:
                            cat_exit_code = 0
                    break
                cat_lines.append(line)
                
            if cat_exit_code != 0:
                err_msg = "".join(cat_lines).strip()
                if "Permission denied" in err_msg:
                    raise PermissionError(f"Permission denied: {remote_path}")
                raise RuntimeError(f"Failed to read file {remote_path}: {err_msg}")
                
            return "".join(cat_lines)
            
        # Decode base64
        b64_data = "".join(output_lines)
        b64_clean = "".join(c for c in b64_data if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r")
        try:
            return base64.b64decode(b64_clean.encode('utf-8')).decode('utf-8', errors='replace')
        except Exception as e:
            # Fallback to output lines if base64 decoding fails unexpectedly
            logger.warning(f"Base64 decoding failed for {remote_path}, returning raw lines: {e}")
            return "".join(output_lines)

    def write_file(self, remote_path: str, content: str):
        """
        Writes content to a remote file.
        """
        self.connect()
        logger.info(f"Writing remote file: {remote_path}")
        
        b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        eof_marker = f"__WRITE_EOF_{os.urandom(8).hex()}__"
        sentinel = f"__WRITE_FINISHED_{os.urandom(4).hex()}__"
        
        # csh script to run python to decode and write file
        py_script = f"""import base64
open({repr(remote_path)}, "wb").write(base64.b64decode(b"{b64_content}"))
"""
        cmd = f"python << {eof_marker}\n{py_script}\n{eof_marker}\n"
        self.process.stdin.write(cmd)
        self.process.stdin.flush()
        
        # Check command
        check_cmd = f"echo '{sentinel}:'$status\n"
        self.process.stdin.write(check_cmd)
        self.process.stdin.flush()
        
        exit_code = 0
        while True:
            line = self.process.stdout.readline()
            if not line:
                self.close()
                raise RuntimeError("SSH connection lost during file write.")
            if sentinel in line:
                parts = line.strip().split(":")
                if len(parts) > 1:
                    try:
                        exit_code = int(parts[-1])
                    except ValueError:
                        exit_code = 0
                break
                
        if exit_code != 0:
            raise RuntimeError(f"Failed to write file {remote_path} (exit status: {exit_code})")

    def list_dir(self, remote_path: str) -> list[dict]:
        """
        Lists files in a remote directory.
        """
        self.connect()
        logger.info(f"Listing remote directory: {remote_path}")
        
        sentinel = f"__LIST_FINISHED_{os.urandom(4).hex()}__"
        
        # Run python 2/3 compatible script on remote to list directory and output JSON
        py_script = f"""import os, json, sys
path = {repr(remote_path)}
try:
    items = os.listdir(path)
    res = []
    for item in items:
        p = os.path.join(path, item)
        is_dir = os.path.isdir(p)
        try:
            stat = os.stat(p)
            size = stat.st_size if not is_dir else 0
            mtime = int(stat.st_mtime)
        except Exception:
            size = 0
            mtime = 0
        res.append({{"name": item, "is_directory": is_dir, "size": size, "modified": mtime}})
    print(json.dumps(res))
except Exception as e:
    print(json.dumps([{{"error": str(e)}}]))
"""
        eof_marker = f"__PY_EOF_{os.urandom(8).hex()}__"
        cmd = f"python -c << '{eof_marker}'\n{py_script}\n{eof_marker}\n"
        self.process.stdin.write(cmd)
        self.process.stdin.flush()
        
        check_cmd = f"echo '{sentinel}:'$status\n"
        self.process.stdin.write(check_cmd)
        self.process.stdin.flush()
        
        output_lines = []
        exit_code = 0
        while True:
            line = self.process.stdout.readline()
            if not line:
                self.close()
                raise RuntimeError("SSH connection lost during directory listing.")
            if sentinel in line:
                parts = line.strip().split(":")
                if len(parts) > 1:
                    try:
                        exit_code = int(parts[1])
                    except ValueError:
                        exit_code = 0
                break
            output_lines.append(line)
            
        # Try python3 if python command not found
        if exit_code != 0:
            py3_sentinel = f"__LIST3_FINISHED_{os.urandom(4).hex()}__"
            cmd = f"python3 -c << '{eof_marker}'\n{py_script}\n{eof_marker}\n"
            self.process.stdin.write(cmd)
            self.process.stdin.flush()
            
            check_cmd = f"echo '{py3_sentinel}:'$status\n"
            self.process.stdin.write(check_cmd)
            self.process.stdin.flush()
            
            output_lines = []
            while True:
                line = self.process.stdout.readline()
                if not line:
                    self.close()
                    raise RuntimeError("SSH connection lost during directory listing fallback.")
                if py3_sentinel in line:
                    break
                output_lines.append(line)
                
        stdout_str = "".join(output_lines).strip()
        try:
            # Parse only the JSON portion to ignore warnings/MOTD
            json_start = stdout_str.find("[")
            json_end = stdout_str.rfind("]")
            if json_start != -1 and json_end != -1:
                json_str = stdout_str[json_start:json_end+1]
                data = json.loads(json_str)
                if isinstance(data, list) and len(data) > 0 and "error" in data[0]:
                    raise RuntimeError(data[0]["error"])
                return data
            else:
                raise RuntimeError("Could not find JSON payload in command output.")
        except Exception as e:
            logger.error(f"Failed to parse directory list output: {stdout_str} (error: {e})")
            raise e

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
