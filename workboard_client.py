import os
import json
import hashlib
import logging
import subprocess
import shlex
import time
import difflib
from typing import Dict, Any, Optional, Tuple, List
from ssh_client import RemoteSession
from scp_client import SCPClient

logger = logging.getLogger("eda_mcp.workboard_client")

class WorkBoardClient:
    """
    WorkBoard Client Engine managing Local-Remote Git-backed Workspaces, 
    File Registry Sync (.workboard.json), and Commit-Baseline Version Control.
    """
    def __init__(
        self, 
        session: Optional[RemoteSession] = None, 
        scp_client: Optional[SCPClient] = None,
        base_workboard_dir: str = "./workboard"
    ):
        self.session = session or RemoteSession()
        self.scp_client = scp_client or SCPClient()
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
            cmd = ["git", "-c", "user.name=WorkBoard MCP", "-c", "user.email=mcp@workboard.local"] + args
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

    def _get_current_head_commit(self, workboard_dir: str) -> str:
        """Returns current local Git HEAD short commit SHA or 'UNKNOWN'."""
        ret, stdout, stderr = self._git_cmd(workboard_dir, ["rev-parse", "--short", "HEAD"])
        if ret == 0 and stdout.strip():
            return stdout.strip()
        return "UNKNOWN"

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
        commits to local Git, and records commit SHA & timestamp baseline in .workboard.json.
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
            transfer_mode = "via SCP"
            self.scp_client.download(remote_path, target_local_path, timeout=timeout)

            checksum = self._calculate_checksum(target_local_path)
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Stage file and initial manifest placeholder
            self._git_cmd(wb_dir, ["add", "-f", rel_local])
            self._git_cmd(wb_dir, ["commit", "-m", f"WorkBoard Add: {remote_path} -> {rel_local}"])
            commit_sha = self._get_current_head_commit(wb_dir)

            # Update registry manifest with sync commit baseline
            registry["files"][rel_local] = {
                "remote_path": remote_path,
                "local_checksum": checksum,
                "last_sync_commit": commit_sha,
                "last_sync_time": now_iso,
                "is_directory": os.path.isdir(target_local_path)
            }
            self._save_registry(wb_dir, registry)
            self._git_cmd(wb_dir, ["add", "-f", ".workboard.json"])
            self._git_cmd(wb_dir, ["commit", "--amend", "--no-edit"])

            return (
                f"Successfully added '{remote_path}' to WorkBoard '{wb_name}' at '{rel_local}' ({transfer_mode}).\n"
                f"Synced at local Git commit {commit_sha} ({now_iso}). Checksum: {checksum[:8]}."
            )
        except Exception as e:
            return f"Failed to add '{remote_path}' to WorkBoard '{wb_name}': {str(e)}"

    def pull(self, local_path: str, workboard_name: str = "", timeout: float = 60.0) -> str:
        """
        Re-fetches latest version of an added file from remote server to update local WorkBoard,
        commits to local Git, and advances sync commit baseline in .workboard.json.
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
            transfer_mode = "via SCP"
            self.scp_client.download(remote_path, target_local_path, timeout=timeout)

            checksum = self._calculate_checksum(target_local_path)
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ")

            self._git_cmd(wb_dir, ["add", "-f", rel_local])
            self._git_cmd(wb_dir, ["commit", "-m", f"WorkBoard Pull Update: {rel_local}"])
            commit_sha = self._get_current_head_commit(wb_dir)

            registry["files"][rel_local]["local_checksum"] = checksum
            registry["files"][rel_local]["last_sync_commit"] = commit_sha
            registry["files"][rel_local]["last_sync_time"] = now_iso
            self._save_registry(wb_dir, registry)
            self._git_cmd(wb_dir, ["add", "-f", ".workboard.json"])
            self._git_cmd(wb_dir, ["commit", "--amend", "--no-edit"])

            return (
                f"Successfully pulled latest '{remote_path}' to '{rel_local}' in WorkBoard '{wb_name}' ({transfer_mode}).\n"
                f"Advanced sync baseline to commit {commit_sha} ({now_iso})."
            )
        except Exception as e:
            return f"Failed to pull '{local_path}': {str(e)}"

    def push(self, local_path: str, workboard_name: str = "", message: str = "Agent sync", timeout: float = 60.0) -> str:
        """
        Uploads local edits from WorkBoard back to mapped remote server location over SSH,
        commits to local Git, and advances sync commit baseline in .workboard.json.
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
            transfer_mode = "via SCP"
            self.scp_client.upload(target_local_path, remote_dest, timeout=timeout)

            checksum = self._calculate_checksum(target_local_path)
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ")

            self._git_cmd(wb_dir, ["add", "-f", rel_local])
            self._git_cmd(wb_dir, ["commit", "-m", f"WorkBoard Push: {rel_local} -> {remote_dest} ({message})"])
            commit_sha = self._get_current_head_commit(wb_dir)

            registry["files"][rel_local]["local_checksum"] = checksum
            registry["files"][rel_local]["last_sync_commit"] = commit_sha
            registry["files"][rel_local]["last_sync_time"] = now_iso
            self._save_registry(wb_dir, registry)
            self._git_cmd(wb_dir, ["add", "-f", ".workboard.json"])
            self._git_cmd(wb_dir, ["commit", "--amend", "--no-edit"])

            return (
                f"Successfully pushed '{rel_local}' to remote '{remote_dest}' ({transfer_mode}).\n"
                f"Committed locally and advanced sync baseline to commit {commit_sha} ({now_iso})."
            )
        except Exception as e:
            return f"Failed to push '{local_path}' to remote: {str(e)}"

    def diff(self, local_path: str = "", workboard_name: str = "", timeout: float = 60.0) -> str:
        """
        Fetches live remote server file over SSH and compares line-by-line with local file.
        Auto-Update Rule: If local and remote files are identical, automatically updates .workboard.json
        with the latest local Git HEAD commit and timestamp, advancing the sync baseline!
        """
        wb_name, err = self._resolve_workboard_name(workboard_name)
        if err:
            return err

        wb_dir = self._get_workboard_dir(wb_name)
        registry = self._load_registry(wb_dir, wb_name)

        rel_local = local_path.strip()

        # If specific local_path provided and registered
        if rel_local and rel_local in registry.get("files", {}):
            file_meta = registry["files"][rel_local]
            remote_path = file_meta["remote_path"]
            target_local_path = os.path.join(wb_dir, rel_local)

            if not os.path.exists(target_local_path):
                return f"Error: Local file not found: {target_local_path}"

            try:
                remote_bytes = self.scp_client.read_bytes(remote_path, timeout=timeout)
                with open(target_local_path, "rb") as f:
                    local_bytes = f.read()

                # Case 1: Local and remote files are 100% identical!
                if local_bytes == remote_bytes:
                    current_head = self._get_current_head_commit(wb_dir)
                    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ")

                    # Advance sync commit baseline in registry
                    registry["files"][rel_local]["last_sync_commit"] = current_head
                    registry["files"][rel_local]["last_sync_time"] = now_iso
                    registry["files"][rel_local]["local_checksum"] = self._calculate_checksum(target_local_path)
                    self._save_registry(wb_dir, registry)
                    self._git_cmd(wb_dir, ["add", "-f", ".workboard.json"])
                    self._git_cmd(wb_dir, ["commit", "-m", f"WorkBoard Diff: Verified sync baseline for {rel_local} at {current_head}"])

                    return (
                        f"✓ No diff detected for '{rel_local}'. Local and live remote server files are IDENTICAL.\n"
                        f"Advanced sync baseline in .workboard.json to commit {current_head} ({now_iso})."
                    )

                # Case 2: Files differ! Compute line-by-line unified diff
                local_str = local_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
                remote_str = remote_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)

                diff_lines = list(difflib.unified_diff(
                    local_str,
                    remote_str,
                    fromfile=f"local:{rel_local}",
                    tofile=f"remote:{remote_path}"
                ))

                if diff_lines:
                    return f"--- Unified Local vs Remote Diff ({rel_local}) ---\n" + "".join(diff_lines)
                else:
                    return f"No visual diff lines for '{rel_local}'."

            except Exception as e:
                return f"Failed to check remote diff for '{rel_local}': {str(e)}"

        # Default local Git diff if local_path is omitted or not registered
        target = rel_local if rel_local else "."
        ret, stdout, stderr = self._git_cmd(wb_dir, ["diff", target])
        if stdout.strip():
            return f"--- Local Git Diff ({target}) ---\n{stdout.strip()}"
        return f"No local uncommitted Git diff for '{target}' in WorkBoard '{wb_name}'."

    def status(self, workboard_name: str = "") -> str:
        """
        Reports file-wise status of all tracked files in the WorkBoard, detailing
        mapped remote paths, sync commit baselines, and local Git states.
        """
        wb_name, err = self._resolve_workboard_name(workboard_name)
        if err:
            return err

        wb_dir = self._get_workboard_dir(wb_name)
        registry = self._load_registry(wb_dir, wb_name)
        ret, git_status_out, stderr = self._git_cmd(wb_dir, ["status", "--short"])

        output = []
        output.append(f"WorkBoard Name: {wb_name}")
        output.append(f"Local Root: {wb_dir}")
        output.append(f"Active Memory State: {'(Active)' if self.active_workboard == wb_name else ''}")
        output.append(f"Last Registry Sync: {registry.get('last_synced', 'Never')}")
        
        output.append("\n--- Local Git Repository Status ---")
        output.append(git_status_out.strip() if git_status_out.strip() else "Working tree clean.")

        output.append("\n--- Registered Files (Synced Commit Baseline) ---")
        files_dict = registry.get("files", {})
        if not files_dict:
            output.append("No files registered yet in this WorkBoard.")
        else:
            for rel, meta in files_dict.items():
                local_file = os.path.join(wb_dir, rel)
                current_checksum = self._calculate_checksum(local_file)
                stored_checksum = meta.get("local_checksum", "")
                
                sync_commit = meta.get("last_sync_commit", "UNKNOWN")
                sync_time = meta.get("last_sync_time", "Unknown time")
                remote_path = meta.get("remote_path", "Unmapped")

                if not os.path.exists(local_file):
                    local_state = "LOCAL_MISSING"
                elif current_checksum != stored_checksum:
                    local_state = "LOCAL_MODIFIED (since last sync)"
                else:
                    local_state = f"CLEAN (synced at commit {sync_commit})"

                output.append(
                    f"  • {rel} -> {remote_path}\n"
                    f"    - Last Synced Baseline: Commit {sync_commit} ({sync_time})\n"
                    f"    - Local File State: {local_state}\n"
                    f"    - Note: Server state may vary; run action='diff' to verify live remote server file."
                )

        return "\n".join(output)

    def history(self, local_path: str = "", workboard_name: str = "", limit: int = 10) -> str:
        """
        Displays Git commit history for a specific file or the entire WorkBoard repository.
        """
        wb_name, err = self._resolve_workboard_name(workboard_name)
        if err:
            return err

        wb_dir = self._get_workboard_dir(wb_name)
        rel_local = local_path.strip()
        git_args = ["log", f"-n{limit}", "--pretty=format:%h - %an, %ar : %s"]
        if rel_local:
            git_args.extend(["--", rel_local])

        ret, stdout, stderr = self._git_cmd(wb_dir, git_args)
        if ret == 0 and stdout.strip():
            target_desc = f"'{rel_local}'" if rel_local else "Workspace"
            header = f"--- WorkBoard '{wb_name}' Commit History ({target_desc}) ---"
            return f"{header}\n{stdout.strip()}"
        return f"No commit history found for '{rel_local if rel_local else 'workspace'}' in WorkBoard '{wb_name}'."

