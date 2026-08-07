import re
import time
import os
import json
import logging
import shlex
import subprocess
import base64
import select
import tempfile
from typing import Tuple, List, Optional

logger = logging.getLogger("eda_mcp.ssh_client")

class RemoteSession:
    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.process = None
        self.load_config()
        
    def load_config(self):
        target_path = self.config_path
        if not os.path.exists(target_path):
            dir_name = os.path.dirname(os.path.abspath(target_path))
            fallback_candidates = [
                os.path.join(dir_name, "config", "config.json"),
                os.path.join(dir_name, "config.json"),
                os.path.join(os.path.dirname(dir_name), "config", "config.json"),
                os.path.join(os.path.dirname(dir_name), "config.json"),
            ]
            found = False
            for fb in fallback_candidates:
                if os.path.exists(fb):
                    logger.warning(f"Config file '{target_path}' not found. Falling back to '{fb}'.")
                    target_path = fb
                    found = True
                    break
            if not found:
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(target_path, "r") as f:
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
            
            # Read stdout until the initialization is complete with timeout
            start_time = time.time()
            init_timeout = 30.0
            while True:
                elapsed = time.time() - start_time
                if elapsed > init_timeout:
                    raise TimeoutError(f"SSH initialization timed out after {init_timeout}s.")
                
                r, _, _ = select.select([self.process.stdout], [], [], 1.0)
                if not r:
                    if self.process.poll() is not None:
                        raise RuntimeError("SSH process terminated during initialization.")
                    continue

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

    def execute_command(self, cmd: str, timeout: float = 60.0) -> tuple[int, str, str]:
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
        
        try:
            self.process.stdin.write(full_cmd)
            self.process.stdin.flush()
        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to write command to SSH session: {e}")
        
        # Read lines from stdout until we see the sentinel or time out
        output_lines = []
        exit_code = 0
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            remaining = timeout - elapsed
            if remaining <= 0:
                self.close() # Reset the contaminated session!
                raise TimeoutError(f"Command execution timed out after {timeout} seconds. The SSH session has been reset.")

            r, _, _ = select.select([self.process.stdout], [], [], min(remaining, 1.0))
            if not r:
                if self.process.poll() is not None:
                    self.close()
                    raise RuntimeError("SSH process terminated unexpectedly during command execution.")
                continue

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
        return exit_code, stdout_str, ""

    def execute_interactive_stream(self, cmd: str, prompt_regex: str = r"(%|>|\$|eldo>)\s*$", timeout: float = 10.0) -> tuple[int, str, str]:
        """
        Sends a command to the persistent interactive SSH session and streams stdout in real-time,
        detecting prompt readiness (matching prompt_regex) instantly even without trailing newlines.
        Returns: (exit_status, stdout_string, stderr_string)
        """
        self.connect()
        logger.debug(f"Sending interactive stream command: {cmd}")
        
        try:
            self.process.stdin.write(cmd + "\n")
            self.process.stdin.flush()
        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to write interactive command to SSH session: {e}")
        
        output_buffer = ""
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            remaining = timeout - elapsed
            if remaining <= 0:
                logger.warning(f"Interactive stream timed out after {timeout}s waiting for prompt matching '{prompt_regex}'")
                break

            r, _, _ = select.select([self.process.stdout], [], [], min(remaining, 0.5))
            if not r:
                if self.process.poll() is not None:
                    self.close()
                    raise RuntimeError("SSH process terminated unexpectedly during interactive stream.")
                continue

            chunk = self.process.stdout.read(1)
            if not chunk:
                self.close()
                break
            output_buffer += chunk
            
            # Test trailing line against prompt regex
            lines = output_buffer.splitlines()
            last_line = lines[-1] if lines else output_buffer
            if re.search(prompt_regex, last_line):
                break
                
        return 0, output_buffer, ""

    def read_file(self, remote_path: str, timeout: float = 60.0) -> str:
        """
        Reads a file from the remote server over the persistent SSH session 
        with non-blocking timeout handling via _read_until_sentinel().
        """
        self.connect()
        logger.info(f"Reading remote file: {remote_path}")
        
        target_path = remote_path.strip()
        quoted_path = f"$HOME{shlex.quote(target_path[1:])}" if target_path.startswith("~") else shlex.quote(target_path)
        sentinel = f"__READ_FINISHED_{os.urandom(4).hex()}__"
        
        # Single-line csh command to prevent parser stalls
        cmd = f"test -d {quoted_path} && echo '{sentinel}:is_dir' || (base64 {quoted_path}; echo '{sentinel}:'$status)\n"
        
        try:
            self.process.stdin.write(cmd)
            self.process.stdin.flush()
        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to write read command to SSH session: {e}")
        
        output_lines, result_status = self._read_until_sentinel(sentinel, timeout=timeout)
            
        if result_status == "404":
            raise FileNotFoundError(f"File not found: {remote_path}")
        elif result_status == "is_dir":
            raise IsADirectoryError(f"Path is a directory: {remote_path}")
            
        # If base64 failed (e.g. status was non-zero like 1 or command not found)
        if result_status != "0":
            cat_sentinel = f"__CAT_FINISHED_{os.urandom(4).hex()}__"
            cat_cmd = f"cat {quoted_path}; echo '{cat_sentinel}:'$status\n"
            try:
                self.process.stdin.write(cat_cmd)
                self.process.stdin.flush()
            except Exception as e:
                self.close()
                raise RuntimeError(f"Failed to write fallback read command to SSH session: {e}")
            
            cat_lines, cat_status = self._read_until_sentinel(cat_sentinel, timeout=timeout)
            try:
                cat_exit_code = int(cat_status)
            except ValueError:
                cat_exit_code = 0
                
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

    def _read_until_sentinel(self, sentinel: str, timeout: float = 30.0) -> Tuple[List[str], str]:
        """
        Reads stdout line-by-line from persistent SSH session until sentinel token is encountered.
        Returns: (output_lines, result_status_code)
        """
        start_time = time.time()
        output_lines = []
        result_status = "0"

        while True:
            if time.time() - start_time > timeout:
                self.close()
                raise TimeoutError(f"Operation timed out after {timeout} seconds reading SSH stream.")

            rlist, _, _ = select.select([self.process.stdout], [], [], 0.5)
            if not rlist:
                continue

            line = self.process.stdout.readline()
            if not line:
                self.close()
                raise RuntimeError("SSH connection lost while reading stdout stream.")

            if sentinel in line:
                parts = line.strip().split(":")
                if len(parts) > 1:
                    result_status = parts[-1]
                break

            output_lines.append(line)

        return output_lines, result_status

    def write_file(self, remote_path: str, content: str, timeout: float = 30.0):
        """
        Writes content to a remote file.
        """
        self.connect()
        logger.info(f"Writing remote file: {remote_path}")
        
        b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        sentinel = f"__WRITE_FINISHED_{os.urandom(4).hex()}__"
        target_path = remote_path.strip()
        quoted_path = f"$HOME{shlex.quote(target_path[1:])}" if target_path.startswith("~") else shlex.quote(target_path)
        
        cmd = f"echo {shlex.quote(b64_content)} | base64 -d > {quoted_path}; echo '{sentinel}:'$status\n"
        try:
            self.process.stdin.write(cmd)
            self.process.stdin.flush()
        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to write file command to SSH session: {e}")
        
        _, status_str = self._read_until_sentinel(sentinel, timeout=timeout)
        try:
            exit_code = int(status_str)
        except ValueError:
            exit_code = 0
                
        if exit_code != 0:
            raise RuntimeError(f"Failed to write file {remote_path} (exit status: {exit_code})")

    def read_file_bytes(self, remote_path: str, timeout: float = 30.0) -> bytes:
        """
        Reads remote file raw bytes over persistent SSH session (Base64 fallback).
        """
        self.connect()
        logger.info(f"Reading remote file bytes via subshell fallback: {remote_path}")
        target_path = remote_path.strip()
        quoted_path = f"$HOME{shlex.quote(target_path[1:])}" if target_path.startswith("~") else shlex.quote(target_path)
        sentinel = f"__READ_FINISHED_{os.urandom(4).hex()}__"
        cmd = f"test -d {quoted_path} && echo '{sentinel}:is_dir' || (base64 {quoted_path}; echo '{sentinel}:'$status)\n"
        
        try:
            self.process.stdin.write(cmd)
            self.process.stdin.flush()
        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to write read command to SSH session: {e}")
            
        output_lines, result_status = self._read_until_sentinel(sentinel, timeout=timeout)
        if result_status == "404":
            raise FileNotFoundError(f"File not found: {remote_path}")
        elif result_status == "is_dir":
            raise IsADirectoryError(f"Path is a directory: {remote_path}")
            
        b64_data = "".join(output_lines)
        b64_clean = "".join(c for c in b64_data if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r")
        return base64.b64decode(b64_clean.encode('ascii'))

    def write_file_bytes(self, remote_path: str, content: bytes, timeout: float = 30.0):
        """
        Writes raw bytes to remote file over persistent SSH session (Base64 fallback).
        """
        self.connect()
        logger.info(f"Writing remote file bytes via subshell fallback: {remote_path}")
        b64_content = base64.b64encode(content).decode('ascii')
        sentinel = f"__WRITE_FINISHED_{os.urandom(4).hex()}__"
        target_path = remote_path.strip()
        quoted_path = f"$HOME{shlex.quote(target_path[1:])}" if target_path.startswith("~") else shlex.quote(target_path)
        cmd = f"echo {shlex.quote(b64_content)} | base64 -d > {quoted_path}; echo '{sentinel}:'$status\n"
        try:
            self.process.stdin.write(cmd)
            self.process.stdin.flush()
        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to write file command to SSH session: {e}")
            
        _, status_str = self._read_until_sentinel(sentinel, timeout=timeout)
        try:
            exit_code = int(status_str)
        except ValueError:
            exit_code = 0
        if exit_code != 0:
            raise RuntimeError(f"Failed to write file {remote_path} (exit status: {exit_code})")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

