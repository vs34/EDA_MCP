# WORKBOARD_BACKEND_SPEC

## 1. Directory Structure & Registry Schema ([`workboard_client.py`](file:///Users/vs/function/EDA_MCP/workboard_client.py))

### Path Binding
- Base Directory: `./workboard/<workboard_name>/`
- Manifest File: `./workboard/<workboard_name>/.workboard.json`

### `.workboard.json` Schema Structure
```json
{
  "workboard_name": "string",
  "local_root": "string",
  "created_at": "ISO-8601 string",
  "last_synced": "ISO-8601 string",
  "files": {
    "<rel_local_path>": {
      "remote_path": "string",
      "local_checksum": "SHA-256 string",
      "last_sync_commit": "Git SHA-1 short hash string",
      "last_sync_time": "ISO-8601 string",
      "is_directory": false
    }
  }
}
```

---

## 2. Git Subprocess Invocation (`_git_cmd`)
```python
cmd = ["git", "-c", "user.name=WorkBoard MCP", "-c", "user.email=mcp@workboard.local"] + args
```

---

## 3. `diff` Auto-Baseline Advancing Algorithm

```
                  diff(local_path)
                         │
                         ▼
        scp_client.read_bytes(remote_path)
                         │
                         ▼
             Compare local vs remote bytes
            ┌─────────────────┴─────────────────┐
            │                                   │
      local == remote                     local != remote
            │                                   │
            ▼                                   ▼
 Get HEAD commit SHA                 difflib.unified_diff()
 Update last_sync_commit                    │
 Update last_sync_time                      ▼
 Save .workboard.json               Return unified diff string
 git commit --amend / commit
            │
            ▼
 Return "No diff detected..."
```
