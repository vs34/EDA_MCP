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
        self.load_config()
        
    def load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
            
        self.ssh_host = self.config.get("ssh_host", "eda-uni")
        self.env_setup_cmd = self.config.get("env_setup_cmd", "source /cadance/cshrc")

    def connect(self):
        # Verify connection works
        logger.info(f"Connecting to remote host: {self.ssh_host}")
        try:
            r = subprocess.run(
                ['ssh', '-o', 'BatchMode=yes', self.ssh_host, 'echo CONNECTED'],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=10
            )
            if r.returncode != 0:
                raise RuntimeError(f"SSH Connection test failed with code {r.returncode}: {r.stderr}")
            logger.info("SSH connection tested successfully.")
        except subprocess.TimeoutExpired:
            raise TimeoutError("SSH Connection test timed out after 10 seconds.")
        except Exception as e:
            logger.error(f"Failed to connect to remote host: {e}")
            raise e

    def close(self):
        logger.info("SSH connection closed.")

    def wrap_command(self, cmd: str) -> str:
        """
        Wraps the command to run inside csh and source the environment script.
        """
        # Escape single quotes in the command to safely nest it inside csh -c '...'
        escaped_cmd = cmd.replace("'", "'\\''")
        return f"csh -c '{self.env_setup_cmd} && {escaped_cmd}'"

    def execute_command(self, cmd: str) -> tuple[int, str, str]:
        """
        Executes a command on the remote host with environment sourced.
        Returns: (exit_status, stdout_string, stderr_string)
        """
        wrapped_cmd = self.wrap_command(cmd)
        logger.debug(f"Executing wrapped command: {wrapped_cmd}")
        
        r = subprocess.run(
            ['ssh', '-o', 'BatchMode=yes', self.ssh_host, wrapped_cmd],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True
        )
        return r.returncode, r.stdout, r.stderr

    def read_file(self, remote_path: str) -> str:
        """
        Reads a file from the remote server.
        """
        logger.info(f"Reading remote file: {remote_path}")
        
        # Try using base64 for safe binary/unicode transfer
        r = subprocess.run(
            ['ssh', '-o', 'BatchMode=yes', self.ssh_host, f'base64 {shlex.quote(remote_path)}'],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True
        )
        if r.returncode == 0:
            b64_data = r.stdout.replace('\n', '').replace('\r', '')
            try:
                return base64.b64decode(b64_data).decode('utf-8', errors='replace')
            except Exception:
                pass
                
        # Fallback to cat
        r = subprocess.run(
            ['ssh', '-o', 'BatchMode=yes', self.ssh_host, f'cat {shlex.quote(remote_path)}'],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True
        )
        if r.returncode != 0:
            raise FileNotFoundError(f"Failed to read file {remote_path}: {r.stderr}")
        return r.stdout

    def write_file(self, remote_path: str, content: str):
        """
        Writes content to a remote file.
        """
        logger.info(f"Writing remote file: {remote_path}")
        
        # Try using base64 for safe transfer
        b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        r = subprocess.run(
            ['ssh', '-o', 'BatchMode=yes', self.ssh_host, f'base64 -d > {shlex.quote(remote_path)}'],
            input=b64_content,
            capture_output=True,
            text=True
        )
        if r.returncode != 0:
            # Fallback to cat piping
            r = subprocess.run(
                ['ssh', '-o', 'BatchMode=yes', self.ssh_host, f'cat > {shlex.quote(remote_path)}'],
                input=content,
                capture_output=True,
                text=True
            )
            if r.returncode != 0:
                raise RuntimeError(f"Failed to write file {remote_path}: {r.stderr}")

    def list_dir(self, remote_path: str) -> list[dict]:
        """
        Lists files in a remote directory.
        """
        logger.info(f"Listing remote directory: {remote_path}")
        
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
        # Run using remote Python (python 2 or 3)
        r = subprocess.run(
            ['ssh', '-o', 'BatchMode=yes', self.ssh_host, f"python -c {shlex.quote(py_script)}"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True
        )
        if r.returncode != 0:
            # Try python3 if python command not found
            r = subprocess.run(
                ['ssh', '-o', 'BatchMode=yes', self.ssh_host, f"python3 -c {shlex.quote(py_script)}"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True
            )
            if r.returncode != 0:
                raise RuntimeError(f"Failed to list directory {remote_path}: {r.stderr}")
                
        try:
            data = json.loads(r.stdout.strip())
            if isinstance(data, list) and len(data) > 0 and "error" in data[0]:
                raise RuntimeError(data[0]["error"])
            return data
        except Exception as e:
            logger.error(f"Failed to parse directory list output: {r.stdout} (error: {e})")
            raise e

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
