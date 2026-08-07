>note from human to AI
>this is the file created by an AI agent here are the findings of the agent so that you dont have to work from strach, thank you!!!

---

# SYSTEM CONTEXT: SSH & SCP FILE TRANSFER DIAGNOSTIC RULES & ENVIRONMENT PROFILE

## ENVIRONMENT METADATA
- **Local Client**: macOS Sonoma/Sequoia | OpenSSH_10.3p1 | LibreSSL 3.3.6
- **Remote Host**: `192.168.3.58` | Alias: `eda-uni` | User: `vaibhav22555`
- **Remote OS / SSH Daemon**: RHEL/CentOS Linux (`edatools-server2`) | OpenSSH_5.3
- **Remote Shell Stack**: `/bin/bash` -> executes `csh` via `~/.bashrc`

---

## KNOWN HEURISTICS & FAILURE MODES

### 1. Host Key Negotiation Failure (`ssh-rsa`)
- **Trigger Log**: `Unable to negotiate with <IP> port 22: no matching host key type found. Their offer: ssh-rsa,ssh-dss`
- **Cause**: OpenSSH 8.8+ disables `ssh-rsa` (SHA-1) host key signatures by default.
- **Resolution**: Pass `-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa` or enforce in `~/.ssh/config`:
  ```sshconfig
  Host eda-uni
      HostName 192.168.3.58
      User vaibhav22555
      HostKeyAlgorithms +ssh-rsa
      PubkeyAcceptedKeyTypes +ssh-rsa
      IdentityFile ~/.ssh/id_rsa_legacy
  ```

### 2. Protocol Hang on OpenSSH 5.3 (SFTP vs Legacy SCP)
- **Trigger**: `scp` connection hangs indefinitely after successful authentication.
- **Cause**: OpenSSH 9.0+ defaults `scp` to SFTP protocol. Legacy OpenSSH 5.3 server hangs on SFTP channel setup.
- **Resolution**: Use `-O` flag to enforce original SCP wire protocol:
  `scp -O eda-uni:<remote_path> <local_path>`

### 3. Non-Interactive Shell Traps (`csh` in `~/.bashrc`)
- **Trigger**: `ssh -vvv` shows `exec request accepted on channel 0` but STDOUT stream hangs at `rwindow 0`. `ssh -tt` shows `tput: unknown terminal` or `csh: No entry for terminal type`.
- **Cause**: Remote `~/.bashrc` contains subshell invocations (`csh`) or interactive commands (`tput`, `stty`, `echo`) executed during non-interactive SSH/SCP sessions.
- **Resolution**: Enforce early return guard at line 1 of remote `~/.bashrc`:
  `[ -z "$PS1" ] && return`

---

## CANONICAL COMMAND PATTERNS

### Download File from `eda-uni`
```bash
scp -O eda-uni:~/path/to/file.ext .
```

### Download Directory from `eda-uni`
```bash
scp -O -r eda-uni:~/path/to/directory .
```

### Fallback Direct Command (without SSH config alias)
```bash
scp -O -o HostKeyAlgorithms=+ssh-rsa vaibhav22555@192.168.3.58:~/path/to/file.ext .
```

---

## DIAGNOSTIC PROTOCOL FOR SSH/SCP STALLS

1. **Verify SSH Auth & Protocol**:
   `ssh -vvv -o ConnectTimeout=5 <alias_or_host> "exit"`
   - Check if key accepted (`Server accepts key`).
   - Inspect banner version (`remote software version OpenSSH_5.3`).

2. **Detect Shell TTY Traps**:
   `ssh -tt <alias_or_host>`
   - Inspect output for `csh`, `tput`, `stty`, or missing terminal errors (`tmux-256color`).

3. **Validate Non-Interactive Execution**:
   `ssh <alias_or_host> "echo READY"`
   - If `READY` is returned cleanly without extra stdout lines, SCP will succeed.
