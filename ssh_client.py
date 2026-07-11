import os
import json
import logging
import paramiko
import shlex

logger = logging.getLogger("eda_mcp.ssh_client")

class RemoteSession:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.ssh_client = None
        self.sftp_client = None
        
        # Load configuration
        self.load_config()
        
    def load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
            
        self.ssh_host = self.config.get("ssh_host", "eda-uni")
        self.ssh_config_path = os.path.expanduser(self.config.get("ssh_config_path", "~/.ssh/config"))
        self.env_setup_cmd = self.config.get("env_setup_cmd", "source /cadance/cshrc")

    def connect(self):
        if self.ssh_client is not None:
            return
            
        logger.info(f"Connecting to remote host: {self.ssh_host}")
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load SSH config if available
        connect_kwargs = {}
        if os.path.exists(self.ssh_config_path):
            ssh_config = paramiko.SSHConfig()
            with open(self.ssh_config_path) as f:
                ssh_config.parse(f)
            host_info = ssh_config.lookup(self.ssh_host)
            
            # Extract parameters
            hostname = host_info.get("hostname", self.ssh_host)
            username = host_info.get("user")
            port = host_info.get("port")
            if port:
                port = int(port)
                
            if "identityfile" in host_info:
                key_files = host_info["identityfile"]
                if isinstance(key_files, str):
                    key_files = [key_files]
                key_files = [os.path.expanduser(kf) for kf in key_files if kf]
                connect_kwargs["key_filename"] = [kf for kf in key_files if os.path.exists(kf)]
        else:
            hostname = self.ssh_host
            username = None
            port = 22
            
        try:
            self.ssh_client.connect(
                hostname,
                username=username,
                port=port or 22,
                **connect_kwargs
            )
            self.sftp_client = self.ssh_client.open_sftp()
            logger.info("SSH and SFTP connections established successfully.")
        except Exception as e:
            self.close()
            logger.error(f"Failed to connect to remote host: {e}")
            raise e

    def close(self):
        if self.sftp_client:
            try:
                self.sftp_client.close()
            except Exception:
                pass
            self.sftp_client = None
            
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None
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
        self.connect()
        wrapped_cmd = self.wrap_command(cmd)
        logger.debug(f"Executing wrapped command: {wrapped_cmd}")
        
        stdin, stdout, stderr = self.ssh_client.exec_command(wrapped_cmd)
        
        # Read channels
        stdout_str = stdout.read().decode("utf-8", errors="replace")
        stderr_str = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        
        return exit_status, stdout_str, stderr_str

    def read_file(self, remote_path: str) -> str:
        """
        Reads a file from the remote server.
        """
        self.connect()
        logger.info(f"Reading remote file: {remote_path}")
        with self.sftp_client.open(remote_path, "r") as f:
            return f.read().decode("utf-8", errors="replace")

    def write_file(self, remote_path: str, content: str):
        """
        Writes content to a remote file.
        """
        self.connect()
        logger.info(f"Writing remote file: {remote_path}")
        # Ensure remote directory path exists or file is created
        with self.sftp_client.open(remote_path, "w") as f:
            f.write(content.encode("utf-8"))

    def list_dir(self, remote_path: str) -> list[dict]:
        """
        Lists files in a remote directory.
        """
        self.connect()
        logger.info(f"Listing remote directory: {remote_path}")
        try:
            attributes = self.sftp_client.listdir_attr(remote_path)
            results = []
            for attr in attributes:
                is_dir = (attr.st_mode & 0o170000) == 0o040000
                results.append({
                    "name": attr.filename,
                    "is_directory": is_dir,
                    "size": attr.st_size,
                    "modified": attr.st_mtime
                })
            return results
        except Exception as e:
            logger.error(f"Failed to list remote directory {remote_path}: {e}")
            raise e

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
