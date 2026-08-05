import os
import json
import hashlib
import logging
import subprocess
import shlex
import time
from typing import Dict, Any, Optional, Tuple, List
from ssh_client import RemoteSession

logger = logging.getLogger("eda_mcp.workboard_client")

class WorkBoardClient:
    """
    WorkBoard Client Engine managing Local-Remote Git-backed Workspaces, 
    File Registry Sync (.workboard.json), and Local Version Control.
    """
    def __init__(self, session: Optional[RemoteSession] = None, base_workboard_dir: str = "./workboard"):
        self.session = session or RemoteSession()
        self.base_workboard_dir = os.path.abspath(base_workboard_dir)
        self.active_workboard: Optional[str] = None
        os.makedirs(self.base_workboard_dir, exist_ok=True)

    def _list_workboards(self) -> List[str]:
        """Lists all existing local WorkBoard names in base_workboard_dir."""
        if not os.path.exists(self.base_workboard_dir):
            return []
        return [
            d for d in os.listdir(self.base_workboard_dir) 
            if os.path.isdir(os.path.join(self.base_workboard_dir, d)) and not d.startswith(".")
        ]

    def _resolve_workboard_name(self, workboard_name: str = "") -> Tuple[str, Optional[str]]:
        """
        Resolves the target WorkBoard name.
        If workboard_name is provided, uses it and sets active_workboard.
        If omitted, attempts to use active_workboard or single existing workboard.
        Returns: (workboard_name, error_message)
        """
        clean_name = workboard_name.strip()
        if clean_name:
            self.active_workboard = clean_name
            return clean_name, None

        if self.active_workboard:
            return self.active_workboard, None

        existing = self._list_workboards()
        if len(existing) == 1:
            self.active_workboard = existing[0]
            return existing[0], None
        elif len(existing) > 1:
            return "", f"Error: Multiple WorkBoards exist ({', '.join(existing)}). Please specify 'workboard_name'."
        else:
            default_name = "default"
            self.active_workboard = default_name
            return default_name, None

    def _get_workboard_dir(self, workboard_name: str) -> str:
        """Returns the absolute path to the local WorkBoard directory."""
        return os.path.join(self.base_workboard_dir, workboard_name)

    def _get_registry_path(self, workboard_dir: str) -> str:
        """Returns path to .workboard.json manifest inside local workboard_dir."""
        return os.path.join(workboard_dir, ".workboard.json")

    def _load_registry(self, workboard_dir: str, workboard_name: str) -> Dict[str, Any]:
        """Loads .workboard.json registry file or returns default structure."""
        registry_file = self._get_registry_path(workboard_dir)
        if os.path.exists(registry_file):
            try:
                with open(registry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read registry at {registry_file}: {e}")
        
        return {
            "workboard_name": workboard_name,
            "local_root": workboard_dir,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_synced": "",
            "files": {}
        }

    def _save_registry(self, workboard_dir: str, registry: Dict[str, Any]):
        """Saves registry dictionary to .workboard.json manifest."""
        os.makedirs(workboard_dir, exist_ok=True)
        registry_file = self._get_registry_path(workboard_dir)
        registry["last_synced"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

    def _git_cmd(self, workboard_dir: str, args: List[str]) -> Tuple[int, str, str]:
        """Executes a local git command inside workboard_dir using subprocess."""
        try:
            cmd = ["git", "-c", "user.name=WorkBoard Agent", "-c", "user.email=agent@workboard.local"] + args
            res = subprocess.run(
                cmd,
                cwd=workboard_dir,
                capture_output=True,
                text=True,
                check=False
            )
            return res.returncode, res.stdout, res.stderr
        except Exception as e:
            logger.error(f"Git command failed in {workboard_dir}: {e}")
            return -1, "", str(e)

    def _calculate_checksum(self, filepath: str) -> str:
        """Calculates SHA-256 checksum of a local file."""
        if not os.path.exists(filepath) or os.path.isdir(filepath):
            return ""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def initialize(self, workboard_name: str = "default", local_dir: Optional[str] = None) -> str:
        """
        Creates a clean local WorkBoard workspace directory and initializes a local Git repository.
        Does NOT pull any files from the remote server on init.
        """
        name = workboard_name.strip() or "default"
        if local_dir:
            self.base_workboard_dir = os.path.abspath(local_dir)
        wb_dir = self._get_workboard_dir(name)
        os.makedirs(wb_dir, exist_ok=True)
        self.active_workboard = name

        output = []
        output.append(f"Initialized WorkBoard '{name}' at: {wb_dir}")

        # Git init if not already a git repo
        git_dir = os.path.join(wb_dir, ".git")
        if not os.path.exists(git_dir):
            ret, out, err = self._git_cmd(wb_dir, ["init"])
            if ret == 0:
                output.append("Initialized local Git repository.")
            else:
                output.append(f"Git init notice: {err.strip()}")

        # Write default .gitignore
        gitignore_path = os.path.join(wb_dir, ".gitignore")
        if not os.path.exists(gitignore_path):
            gitignore_content = "*.tr0\n*.wdb\n*.vcd\n*.log\ntemp/\n__pycache__/\n"
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(gitignore_content)
            output.append("Created default .gitignore for large simulation binaries.")

        # Create/Save registry
        registry = self._load_registry(wb_dir, name)
        self._save_registry(wb_dir, registry)
        output.append(f"Created .workboard.json manifest.")

        return "\n".join(output)

    def add(self, remote_path: str, local_path: str = "", workboard_name: str = "", timeout: float = 60.0) -> str:
        """
        Fetches a file from remote EDA server via binary-safe SSH transfer, saves it to local WorkBoard,
        updates .workboard.json registry, and commits to local Git.
        """
        if not remote_path.strip():
            return "Error: 'remote_path' is required for add action."

        wb_name, err = self._resolve_workboard_name(workboard_name)
        if err:
            return err

        wb_dir = self._get_workboard_dir(wb_name)
        self.initialize(workboard_name=wb_name, local_dir=self.base_workboard_dir)
        registry = self._load_registry(wb_dir, wb_name)

        rel_local = local_path.strip() or os.path.basename(remote_path.strip())
        target_local_path = os.path.join(wb_dir, rel_local)
        os.makedirs(os.path.dirname(target_local_path), exist_ok=True)

        try:
            # Binary-safe download using read_file_bytes
            raw_bytes = self.session.read_file_bytes(remote_path, timeout=timeout)
            with open(target_local_path, "wb") as f:
                f.write(raw_bytes)

            checksum = self._calculate_checksum(target_local_path)

            # Update registry manifest
            registry["files"][rel_local] = {
                "remote_path": remote_path,
                "local_checksum": checksum,
                "sync_status": "IN_SYNC",
                "is_directory": False
            }
            self._save_registry(wb_dir, registry)

            # Local Git Add & Commit (using -f to allow explicit tracking of files matched by .gitignore)
            self._git_cmd(wb_dir, ["add", "-f", rel_local, ".workboard.json"])
            self._git_cmd(wb_dir, ["commit", "-m", f"WorkBoard Add: {remote_path} -> {rel_local}"])

            return f"Successfully added '{remote_path}' to WorkBoard '{wb_name}' at '{rel_local}' (Checksum: {checksum[:8]}). Committed to local Git."
        except Exception as e:
            return f"Failed to add '{remote_path}' to WorkBoard '{wb_name}': {str(e)}"

    def pull(self, local_path: str, workboard_name: str = "", timeout: float = 60.0) -> str:
        """
        Re-fetches latest version of an added file from remote server to update local WorkBoard,
        and commits update to local Git repo.
        """
        if not local_path.strip():
            return "Error: 'local_path' is required for pull action."

        wb_name, err = self._resolve_workboard_name(workboard_name)
        if err:
            return err

        wb_dir = self._get_workboard_dir(wb_name)
        registry = self._load_registry(wb_dir, wb_name)

        rel_local = local_path.strip()
        file_meta = registry["files"].get(rel_local)
        if not file_meta or not file_meta.get("remote_path"):
            return f"Error: Local path '{rel_local}' is not registered in WorkBoard '{wb_name}'. Use action='add' first."

        remote_path = file_meta["remote_path"]
        target_local_path = os.path.join(wb_dir, rel_local)

        try:
            raw_bytes = self.session.read_file_bytes(remote_path, timeout=timeout)
            with open(target_local_path, "wb") as f:
                f.write(raw_bytes)

            checksum = self._calculate_checksum(target_local_path)
            registry["files"][rel_local]["local_checksum"] = checksum
            registry["files"][rel_local]["sync_status"] = "IN_SYNC"
            self._save_registry(wb_dir, registry)

            self._git_cmd(wb_dir, ["add", "-f", rel_local, ".workboard.json"])
            self._git_cmd(wb_dir, ["commit", "-m", f"WorkBoard Pull Update: {rel_local}"])

            return f"Successfully pulled latest '{remote_path}' to '{rel_local}' in WorkBoard '{wb_name}'. Committed to local Git."
        except Exception as e:
            return f"Failed to pull '{local_path}': {str(e)}"

    def push(self, local_path: str, workboard_name: str = "", message: str = "Agent sync", timeout: float = 60.0) -> str:
        """
        Uploads local edits from WorkBoard back to mapped remote server location over SSH,
        and commits change to local Git repo.
        """
        if not local_path.strip():
            return "Error: 'local_path' is required for push action."

        wb_name, err = self._resolve_workboard_name(workboard_name)
        if err:
            return err

        wb_dir = self._get_workboard_dir(wb_name)
        registry = self._load_registry(wb_dir, wb_name)

        rel_local = local_path.strip()
        target_local_path = os.path.join(wb_dir, rel_local)

        if not os.path.exists(target_local_path):
            return f"Error: Local file not found: {target_local_path}"

        file_meta = registry["files"].get(rel_local)
        if not file_meta or not file_meta.get("remote_path"):
            return f"Error: Local path '{rel_local}' is not registered in WorkBoard '{wb_name}'. Please use action='add' first."

        remote_dest = file_meta["remote_path"]

        try:
            with open(target_local_path, "rb") as f:
                raw_bytes = f.read()

            # Binary-safe upload using write_file_bytes
            self.session.write_file_bytes(remote_dest, raw_bytes, timeout=timeout)

            checksum = self._calculate_checksum(target_local_path)
            registry["files"][rel_local]["local_checksum"] = checksum
            registry["files"][rel_local]["sync_status"] = "IN_SYNC"
            self._save_registry(wb_dir, registry)

            self._git_cmd(wb_dir, ["add", "-f", rel_local, ".workboard.json"])
            self._git_cmd(wb_dir, ["commit", "-m", f"WorkBoard Push: {rel_local} -> {remote_dest} ({message})"])

            return f"Successfully pushed '{rel_local}' to remote '{remote_dest}'. Local Git commit created."
        except Exception as e:
            return f"Failed to push '{local_path}' to remote: {str(e)}"

    def diff(self, local_path: str = "", workboard_name: str = "") -> str:
        """
        Generates unified line-by-line diff between local WorkBoard file and Git baseline.
        """
        wb_name, err = self._resolve_workboard_name(workboard_name)
        if err:
            return err

        wb_dir = self._get_workboard_dir(wb_name)
        target = local_path.strip() if local_path else "."
        ret, stdout, stderr = self._git_cmd(wb_dir, ["diff", target])
        if stdout.strip():
            return f"--- WorkBoard '{wb_name}' Diff ({target}) ---\n{stdout.strip()}"
        return f"No local diff detected for '{target}' in WorkBoard '{wb_name}'."

    def status(self, workboard_name: str = "") -> str:
        """
        Reports status of tracked files in the WorkBoard.
        """
        wb_name, err = self._resolve_workboard_name(workboard_name)
        if err:
            return err

        wb_dir = self._get_workboard_dir(wb_name)
        registry = self._load_registry(wb_dir, wb_name)
        ret, stdout, stderr = self._git_cmd(wb_dir, ["status", "--short"])

        output = []
        output.append(f"WorkBoard Name: {wb_name}")
        output.append(f"Local Root: {wb_dir}")
        output.append(f"Active Memory State: {'(Active)' if self.active_workboard == wb_name else ''}")
        output.append(f"Last Synced: {registry.get('last_synced', 'Never')}")
        output.append("\n--- Local Git Status ---")
        output.append(stdout.strip() if stdout.strip() else "Working tree clean.")

        output.append("\n--- Registered Files ---")
        files_dict = registry.get("files", {})
        if not files_dict:
            output.append("No files registered yet.")
        else:
            for rel, meta in files_dict.items():
                local_file = os.path.join(wb_dir, rel)
                current_checksum = self._calculate_checksum(local_file)
                stored_checksum = meta.get("local_checksum", "")
                status_label = "IN_SYNC"
                if current_checksum != stored_checksum:
                    status_label = "LOCAL_MODIFIED"

                output.append(f"  • {rel} -> {meta.get('remote_path')} [{status_label}]")

        return "\n".join(output)
