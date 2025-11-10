# TeleMux Security Audit Checklist

This document provides a comprehensive security audit checklist for TeleMux before v1.0 release.

## Audit Status

**Last Audit:** Not yet performed
**Auditor:** TBD
**Date:** TBD
**Version:** 0.9.1

---

## 1. Credential Management

### 1.1 Storage Security
- [ ] Telegram bot token stored securely (not in git)
- [ ] Config file has correct permissions (600 - owner read/write only)
- [ ] No credentials in code or documentation examples
- [ ] No credentials in logs
- [ ] .gitignore properly excludes all credential files

**Test Commands:**
```bash
# Check file permissions
ls -la ~/.telemux/telegram_config
# Should show: -rw------- (600)

# Check for credentials in git
git log --all -p | grep -i "bot.*token" || echo "Good: No tokens in git history"
git log --all -p | grep -i "TELEMUX_TG" || echo "Good: No env vars in git history"
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 1.2 Credential Exposure
- [ ] Credentials not echoed in error messages
- [ ] Telegram API responses don't leak sensitive info
- [ ] No credentials in tmux session output
- [ ] Installation script doesn't display entered credentials

**Test Commands:**
```bash
# Test with invalid credentials
export TELEMUX_TG_BOT_TOKEN="invalid"
export TELEMUX_TG_CHAT_ID="invalid"
python3 telegram_listener.py  # Should fail safely without echoing token

# Check logs for credential leaks
grep -r "bot[0-9]" ~/.telemux/ || echo "Good: No tokens in logs"
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 2. Command Injection Prevention

### 2.1 User Input Sanitization
- [ ] All user messages sanitized before tmux send-keys
- [ ] Shell metacharacters properly escaped ($, `, &&, ;, |, etc.)
- [ ] No eval() or exec() on user input
- [ ] No subprocess.shell=True with user data

**Test Commands:**
```bash
# Test command injection attempts (in Telegram)
# Reply format: session-name: malicious_command

# Test case 1: Command substitution
# Message: test-session: $(rm -rf /tmp/test)

# Test case 2: Backticks
# Message: test-session: `whoami`

# Test case 3: Ampersand
# Message: test-session: echo test && echo injected

# Test case 4: Semicolon
# Message: test-session: echo test; echo injected

# All should be sent as literal strings, not executed
```

**Code Review:**
```python
# Check telegram_listener.py line ~371
# Should use shlex.quote() to sanitize input:
safe_response = shlex.quote(response)
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 2.2 Path Traversal Prevention
- [ ] No user-controlled file paths
- [ ] Agent names validated (no ../ or /)
- [ ] Session names validated (alphanumeric, dash, underscore only)

**Test Commands:**
```bash
# Test path traversal in agent names
# Message: ../../../etc/passwd: test

# Should be rejected by regex: ^([\w-]+):\s*(.+)$
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 3. Authentication & Authorization

### 3.1 Telegram Bot Security
- [ ] Bot privacy mode properly configured
- [ ] Bot only responds to authorized chat IDs
- [ ] No public API endpoints exposed
- [ ] Bot can't be added to unauthorized groups

**Test Commands:**
```bash
# Check bot settings via BotFather
# 1. Message @BotFather
# 2. /mybots
# 3. Select your bot
# 4. Bot Settings → Group Privacy
# Should be OFF for group chat mode

# Test unauthorized access
# Try sending message from different Telegram account
# Should be ignored (check logs)
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 3.2 Tmux Session Access
- [ ] Only owner can access tmux sessions
- [ ] No world-readable tmux sockets
- [ ] Session isolation properly enforced

**Test Commands:**
```bash
# Check tmux socket permissions
ls -la /tmp/tmux-$(id -u)/
# Should be drwx------ (700)

# Verify can't attach from different user
sudo -u nobody tmux attach -t telegram-listener 2>&1
# Should fail with permission denied
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 4. Network Security

### 4.1 HTTPS Enforcement
- [ ] All Telegram API calls use HTTPS
- [ ] No HTTP fallback
- [ ] Certificate validation enabled
- [ ] No SSL verification disabled

**Code Review:**
```python
# Check telegram_listener.py
# All requests should use https://api.telegram.org/
# No 'verify=False' in requests.get() or requests.post()
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 4.2 Network Exposure
- [ ] No listening sockets (only outgoing connections)
- [ ] No webhook mode (long-polling only)
- [ ] No exposed ports
- [ ] Firewall rules not needed (no inbound connections)

**Test Commands:**
```bash
# Check for listening ports
netstat -an | grep LISTEN | grep python
# Should return nothing for telegram_listener.py

# Verify no webhook endpoints
grep -r "webhook" telegram_listener.py
# Should return nothing or only comments
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 5. Input Validation

### 5.1 Message Format Validation
- [ ] Regex properly validates message format
- [ ] Empty message IDs rejected
- [ ] Invalid characters in session names rejected
- [ ] Excessively long messages handled safely

**Test Commands:**
```bash
# Test malformed messages (in Telegram)
# 1. Empty session name: ": message"
# 2. Special chars: "test@session: message"
# 3. Very long: "<10000 chars>: message"
# 4. Unicode: "test🔥: message"

# Check behavior in logs
tail -f ~/.telemux/telegram_listener.log
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 5.2 Configuration Validation
- [ ] tg-doctor validates all config values
- [ ] Invalid bot tokens detected
- [ ] Invalid chat IDs detected
- [ ] Missing dependencies detected

**Test Commands:**
```bash
# Run health check
tg-doctor

# Test with invalid config
echo 'TELEMUX_TG_BOT_TOKEN="invalid"' > ~/.telemux/telegram_config.test
echo 'TELEMUX_TG_CHAT_ID="invalid"' >> ~/.telemux/telegram_config.test
# Should fail validation gracefully
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 6. Error Handling

### 6.1 Graceful Degradation
- [ ] Network failures don't crash daemon
- [ ] Invalid messages logged, not crashed
- [ ] Telegram API errors handled properly
- [ ] Tmux errors handled without data loss

**Test Commands:**
```bash
# Test network failure
# 1. Start listener
# 2. Disable network
# 3. Wait 5 minutes
# 4. Re-enable network
# Listener should recover automatically

# Check error logs
tail -100 ~/.telemux/telegram_errors.log
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 6.2 Error Information Disclosure
- [ ] Stack traces don't leak sensitive paths
- [ ] Error messages don't expose system info
- [ ] Debug logs don't contain credentials
- [ ] Telegram error responses sanitized

**Test Commands:**
```bash
# Trigger errors and check messages
# 1. Invalid config
# 2. Missing files
# 3. Permission denied

# Check what user sees
grep -i "error" ~/.telemux/telegram_listener.log | head -20
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 7. Logging & Audit Trail

### 7.1 Sensitive Data in Logs
- [ ] No credentials logged
- [ ] No full message content logged (only truncated)
- [ ] No API tokens in logs
- [ ] User IPs not logged

**Test Commands:**
```bash
# Check all log files
grep -ri "bot[0-9]" ~/.telemux/
grep -ri "token" ~/.telemux/*.log
grep -ri "password" ~/.telemux/*.log
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 7.2 Log File Security
- [ ] Log files have proper permissions (644 or 600)
- [ ] Log rotation prevents disk fill
- [ ] Old logs properly archived
- [ ] No sensitive data in archived logs

**Test Commands:**
```bash
# Check log file permissions
ls -la ~/.telemux/*.log

# Test log rotation
tg-cleanup
ls -la ~/.telemux/message_queue/archive/
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 8. Dependency Security

### 8.1 Dependency Versions
- [ ] All dependencies have pinned versions
- [ ] No known CVEs in dependencies
- [ ] requests library version up to date
- [ ] Python version requirements documented

**Test Commands:**
```bash
# Check for outdated packages
pip3 list --outdated | grep -E "(requests|urllib3)"

# Check for security vulnerabilities
pip3 install safety
safety check -r requirements.txt
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 8.2 Dependency Sources
- [ ] All dependencies from PyPI (official)
- [ ] No arbitrary code execution during install
- [ ] No unverified third-party packages
- [ ] INSTALL.sh doesn't download external scripts

**Code Review:**
```bash
# Check INSTALL.sh
grep -E "(curl|wget)" INSTALL.sh
# Should only download from official sources if any
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 9. File System Security

### 9.1 File Permissions
- [ ] ~/.telemux/ directory is 755
- [ ] telegram_config is 600
- [ ] Scripts are 755 (not 777)
- [ ] No world-writable files

**Test Commands:**
```bash
# Audit all file permissions
find ~/.telemux -type f -ls
find ~/.telemux -type d -ls

# Check for world-writable
find ~/.telemux -type f -perm -002 -ls
# Should return nothing
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 9.2 Temporary Files
- [ ] No credentials in /tmp
- [ ] Temp files created with mktemp
- [ ] Temp files cleaned up properly
- [ ] No race conditions in temp file creation

**Test Commands:**
```bash
# Check for telemux temp files
ls -la /tmp | grep -i telemux
ls -la /tmp | grep -i telegram

# Should be minimal or none
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 10. Installation Security

### 10.1 INSTALL.sh Security
- [ ] No sudo required (user-space only)
- [ ] No modifications to system files
- [ ] Creates backup before modifications
- [ ] Validates all inputs
- [ ] Safe handling of shell config files

**Test Commands:**
```bash
# Dry-run installation
# Check what INSTALL.sh would modify
grep -n ">" INSTALL.sh | grep -v "#"
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 10.2 Uninstall Security
- [ ] UNINSTALL.sh creates backup
- [ ] No data loss on uninstall
- [ ] Confirmation prompts present
- [ ] Cleans up all files safely

**Test Commands:**
```bash
# Test uninstall with backup
./UNINSTALL.sh --backup
# Verify backup exists and is complete
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 11. Rate Limiting & DoS Prevention

### 11.1 Telegram API Rate Limits
- [ ] Respects Telegram rate limits (30 msg/sec)
- [ ] Retry logic uses exponential backoff
- [ ] No infinite retry loops
- [ ] Handles 429 Too Many Requests properly

**Code Review:**
```python
# Check telegram_listener.py retry logic
# Should have max_retries and exponential backoff
time.sleep(2 ** attempt)
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

### 11.2 Resource Exhaustion
- [ ] Message queue doesn't grow unbounded
- [ ] Log files have size limits
- [ ] No memory leaks in long-running daemon
- [ ] CPU usage reasonable under load

**Test Commands:**
```bash
# Run benchmark for extended period
./benchmark.sh 10000 50

# Monitor resource usage
ps aux | grep telegram_listener
top -p $(pgrep -f telegram_listener)
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 12. Code Review

### 12.1 Secure Coding Practices
- [ ] No use of dangerous functions (eval, exec, etc.)
- [ ] Input validation on all external data
- [ ] Error handling on all I/O operations
- [ ] No hardcoded secrets in code
- [ ] Type hints used appropriately

**Manual Review:**
```bash
# Search for dangerous patterns
grep -r "eval\|exec\|__import__" *.py
grep -r "shell=True" *.py
grep -r "verify=False" *.py
```

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## 13. Documentation Review

### 13.1 Security Documentation
- [ ] Security considerations documented
- [ ] Credential storage explained
- [ ] Setup guide includes security steps
- [ ] Known limitations documented
- [ ] Responsible disclosure policy present

**Check:**
- README.md security section
- CLAUDE.md security considerations
- .env.example comments

**Status:** [ ] PASS [ ] FAIL
**Notes:**

---

## Summary

**Total Checks:** 50+
**Passed:** __/__
**Failed:** __/__
**Not Applicable:** __/__

**Critical Issues Found:**
1.
2.
3.

**Medium Issues Found:**
1.
2.
3.

**Low Issues Found:**
1.
2.
3.

**Recommendations:**
1.
2.
3.

**Sign-off:**
- Auditor Name: _______________
- Date: _______________
- Signature: _______________

---

## Post-Audit Actions

### Immediate (Critical Issues)
- [ ] Issue #1: [Description]
- [ ] Issue #2: [Description]

### Short-term (Medium Issues)
- [ ] Issue #1: [Description]
- [ ] Issue #2: [Description]

### Long-term (Low Issues / Improvements)
- [ ] Issue #1: [Description]
- [ ] Issue #2: [Description]

---

## Re-audit Schedule

**Next audit:** [Date]
**Frequency:** Before each major release
**Trigger events:** Security-related changes, new features touching auth/credentials
