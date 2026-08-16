# AUDIT_AND_MAINTENANCE_SPEC

## 1. Code Discrepancy & Bug Audit Matrix

| Issue ID | File / Location | Description | Severity | Fix Specification |
| :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | [`server.py:194`](../../server.py#L194) / [`eldo_client.py`](../../eldo_client.py) | `eldo_client.run_script(...)` is called when `action="run_script"`, but `run_script` method is NOT defined in `EldoClient`. | **HIGH** | Implement `run_script(self, script_path: str, work_dir: str = "")` in `EldoClient` executing batch `eldo <script_path>` via `execute_command`. |
| **CLEANUP-01** | [`eldo_client.py:16-17`](../../eldo_client.py#L16-L17) | `interactive_pid` and `interactive_keeper_pid` initialized in `__init__` and reset in `is_interactive_running()`, but `is_interactive_running()` is dead code (never called). | **LOW** | Remove dead attributes or wire `is_interactive_running()` into interactive action checks. |
| **CLEANUP-02** | [`virtuoso_client.py:16`](../../virtuoso_client.py#L16) | `self.pid = None` initialized in `__init__` but never set or populated. | **LOW** | Remove unreferenced `self.pid` attribute or populate with remote PID. |
| **TYPE-01** | [`ssh_client.py:113`](../../ssh_client.py#L113) | `execute_command` return type hint states `tuple[int, str, str]`, but stderr is merged into stdout (`stderr=subprocess.STDOUT`), returning `""` for stderr. | **LOW** | Update return type hint or docstring to reflect stdout/stderr interleaving. |

---

## 2. Test Suite Execution Command

Execute full offline unit test suite:
```bash
PYTHONPATH=. python3 -m unittest discover -s tests
```
