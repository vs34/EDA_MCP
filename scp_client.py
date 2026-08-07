import os
import json
import logging
import tempfile
import subprocess
from typing import Optional, List

logger = logging.getLogger("eda_mcp.scp_client")

class SCPClient:
    """
    Dedicated SCP Transport Engine for direct binary file and directory transfers 
    between local workstation and remote SSH host without terminal shell parsing.
    """
    def __init__(
        self, 
        config_path: str = "config.json", 
        host: str = "", 
        user: str = "", 
        port: int = 22, 
        key_filename: Optional[str] = None,
        ssh_config_path: Optional[str] = None
    ):
        self.config_path = config_path
        self.host = host
        self.user = user
        self.port = port
        self.key_filename = key_filename
        self.ssh_config_path = ssh_config_path
        self.load_config()

    def load_config(self):
        """Loads SSH credentials from config file if not provided directly."""
        if self.host:
            return

        target_path = self.config_path
        if not os.path.exists(target_path):
            dir_name = os.path.dirname(os.path.abspath(target_path))
            fallback_candidates = [
                os.path.join(dir_name, "config.json"),
                os.path.join(os.path.dirname(dir_name), "config", "config.json"),
                os.path.join(os.path.dirname(dir_name), "config_remote_control.json"),
                os.path.join(os.path.dirname(dir_name), "config", "config_remote_control.json"),
            ]
            for fb in fallback_candidates:
                if os.path.exists(fb):
                    target_path = fb
                    break

        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.host = config.get("ssh_host") or config.get("host") or self.host or "eda-uni"
                    self.user = config.get("ssh_user") or config.get("user") or self.user or ""
                    self.port = int(config.get("port", self.port or 22))
                    self.key_filename = config.get("key_filename", self.key_filename)
                    self.ssh_config_path = config.get("ssh_config_path", self.ssh_config_path)
            except Exception as e:
                logger.error(f"Failed to load SSH config in SCPClient from {target_path}: {e}")

        if not self.host:
            self.host = "eda-uni"

    def _get_base_scp_cmd(self) -> List[str]:
        """Constructs base SCP command options."""
        cmd = ["scp", "-O", "-q", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no"]
        
        # Pass explicit SSH config file path if specified or available (~/.ssh/config)
        cfg_path = self.ssh_config_path or "~/.ssh/config"
        expanded_cfg = os.path.expanduser(cfg_path)
        if os.path.exists(expanded_cfg):
            cmd.extend(["-F", expanded_cfg])

        if self.port and self.port != 22:
            cmd.extend(["-P", str(self.port)])
        if self.key_filename and os.path.exists(self.key_filename):
            cmd.extend(["-i", self.key_filename])
        return cmd

    def download(self, remote_path: str, local_path: str, timeout: float = 60.0) -> str:
        """
        Downloads a remote file OR directory (-r) via SCP directly to local_path.
        Bypasses terminal shell parsing and Base64 size expansion.
        """
        if not self.host:
            raise ValueError("SCPClient not configured: missing host or ssh_host credentials.")

        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)

        remote_target = remote_path.strip()
        quoted_remote = f"{self.user}@{self.host}:{remote_target}" if self.user else f"{self.host}:{remote_target}"

        cmd = self._get_base_scp_cmd() + ["-r", quoted_remote, local_path]
        logger.info(f"SCP Downloading: {remote_target} -> {local_path}")

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
            if res.returncode != 0:
                err_msg = res.stderr.strip() or res.stdout.strip()
                raise RuntimeError(f"SCP download failed ({res.returncode}): {err_msg}")
            return f"Successfully downloaded {remote_path} to {local_path} via SCP."
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"SCP download timed out after {timeout} seconds for {remote_path}")

    def upload(self, local_path: str, remote_path: str, timeout: float = 60.0) -> str:
        """
        Uploads a local file OR directory (-r) via SCP directly to remote_path.
        """
        if not self.host:
            raise ValueError("SCPClient not configured: missing host or ssh_host credentials.")

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local path does not exist for SCP upload: {local_path}")

        remote_target = remote_path.strip()
        quoted_remote = f"{self.user}@{self.host}:{remote_target}" if self.user else f"{self.host}:{remote_target}"

        cmd = self._get_base_scp_cmd() + ["-r", local_path, quoted_remote]
        logger.info(f"SCP Uploading: {local_path} -> {remote_target}")

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
            if res.returncode != 0:
                err_msg = res.stderr.strip() or res.stdout.strip()
                raise RuntimeError(f"SCP upload failed ({res.returncode}): {err_msg}")
            return f"Successfully uploaded {local_path} to {remote_path} via SCP."
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"SCP upload timed out after {timeout} seconds for {local_path}")

    def read_bytes(self, remote_path: str, timeout: float = 30.0) -> bytes:
        """
        Downloads a remote file via SCP into a temporary file and returns raw bytes.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.download(remote_path, tmp_path, timeout=timeout)
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def write_bytes(self, remote_path: str, content: bytes, timeout: float = 30.0) -> str:
        """
        Writes raw bytes to a temporary local file and uploads via SCP to remote_path.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            return self.upload(tmp_path, remote_path, timeout=timeout)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
