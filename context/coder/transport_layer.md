# TRANSPORT_LAYER_SPEC

## 1. Subshell Transport Contract ([`ssh_client.py`](../../ssh_client.py))

```python
self.process = subprocess.Popen(
    ['ssh', '-o', 'BatchMode=yes', self.ssh_host, 'csh'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    bufsize=0
)
```

### Protocol Mechanics
- **Subshell Binary**: `csh` (C Shell on remote Linux cluster)
- **Initialization Sourcing**: `self.env_setup_cmd` executed on connection; blocks until sentinel string `__CSH_INIT_DONE__:<status>` appears in stdout stream.
- **Synchronous Sentinel Command Execution**:
  ```python
  sentinel = f"__CMD_FINISHED_{os.urandom(4).hex()}__"
  full_cmd = f"{cmd}; echo '{sentinel}:'$status\n"
  ```
  `_read_until_sentinel()` uses non-blocking `select.select([self.process.stdout], [], [], 0.5)` loop, reads chunks via `os.read(self.process.stdout.fileno(), 4096)`, parses line matching `sentinel`, extracts status code after `:`, and returns `(exit_code, stdout_str, "")`.

- **Interactive Regex Streaming (`execute_interactive_stream`)**:
  Used for REPL sessions (`virtuoso -nograph`, `eldo -inter`). Accumulates stdout bytes until the trailing output line matches prompt regex:
  - Virtuoso: `r"(>\s*$|\bCIW>\s*$)"`
  - Eldo: `r"(eldo>\s*$|\bELDO>\s*$)"`

---

## 2. Direct SCP Transport Contract ([`scp_client.py`](../../scp_client.py))

Executes OpenSSH legacy SCP protocol (`scp -O`) to bypass terminal escaping and Base64 size expansion for binary files/directories:

```python
cmd = [
  "scp", "-O", "-q", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
  "-F", os.path.expanduser(self.ssh_config_path or "~/.ssh/config"),
  "-r", source_path, destination_path
]
```
- Download: `download(remote_path, local_path)`
- Upload: `upload(local_path, remote_path)`
- Byte Stream: `read_bytes()` / `write_bytes()` via `tempfile.NamedTemporaryFile`
