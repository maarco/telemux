# TeleMux Roadmap

This document outlines the path to a production-ready v1.0 release and future enhancements.

## Current Status

**Version:** 0.9.0 (Beta)
**Status:** Functional, actively tested, needs polish for v1.0
**Repository:** https://github.com/maarco/telemux

---

## Critical Issues (Block v1.0)

### 1. Complete Migration from Legacy Paths
**Priority:** 🔴 Critical
**Issue:** Agent inboxes still write to `~/.team_mux/agents/` instead of `~/.telemux/agents/`

**Tasks:**
- [ ] Update `telegram_listener.py` line ~164 to use `TELEMUX_DIR / "agents"`
- [ ] Update hardcoded "FROM MARCO" to "FROM USER" (line ~206)
- [ ] Test agent inbox creation in correct directory
- [ ] Add migration script to move existing `.team_mux` data to `.telemux`
- [ ] Update all log messages referencing old paths

**Files to modify:**
- `telegram_listener.py`

**Testing:**
```bash
# Test inbox creation
tg_agent "test-agent" "Test message"
ls -la ~/.telemux/agents/test-agent/inbox.txt  # Should exist
```

---

### 2. Fix Documentation Inconsistencies
**Priority:** 🔴 Critical

**Tasks:**
- [ ] Verify all README examples reference correct paths (`.telemux` not `.team_mux`)
- [ ] Update CLAUDE.md with correct inbox paths
- [ ] Fix function name typos in CHANGELOG.md
- [ ] Ensure all example scripts use correct paths
- [ ] Add migration notes for users upgrading from Tele-Claude

**Files to review:**
- `README.md`
- `CLAUDE.md`
- `CHANGELOG.md`
- `examples/*.sh`

---

## High Priority (Should have for v1.0)

### 3. Add Log Rotation
**Priority:** 🟡 High
**Issue:** All log files grow indefinitely without cleanup

**Tasks:**
- [ ] Implement max size for `outgoing.log` (e.g., 10MB)
- [ ] Implement max size for `incoming.log` (e.g., 10MB)
- [ ] Rotate logs monthly or at size limit
- [ ] Archive old logs to `message_queue/archive/`
- [ ] Add cleanup script: `~/.telemux/cleanup-logs.sh`
- [ ] Add optional cron job for automatic cleanup

**Implementation:**
```bash
# Add to telegram_control.sh
tg-cleanup() {
    # Rotate logs > 10MB
    # Archive to message_queue/archive/YYYY-MM/
}
```

**Files to create:**
- `cleanup-logs.sh` (new)
- Update `telegram_control.sh` with cleanup command

---

### 4. Improve Error Handling
**Priority:** 🟡 High

**Tasks:**
- [ ] Add retry logic for failed Telegram API calls (3 retries with exponential backoff)
- [ ] Add timeout handling for long-running requests
- [ ] Implement graceful degradation if Telegram is unreachable
- [ ] Add health check endpoint/command
- [ ] Better error messages for common failures
- [ ] Log all errors to dedicated error log file

**Implementation:**
```python
def send_with_retry(url, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                return response
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

**Files to modify:**
- `telegram_listener.py`

---

### 5. Add Dependency Management
**Priority:** 🟡 High

**Tasks:**
- [ ] Create `requirements.txt` with pinned versions
- [ ] Update INSTALL.sh to check/install Python dependencies
- [ ] Add `pip install -r requirements.txt` step to installation
- [ ] Document Python version requirements (3.6+)
- [ ] Test on clean Python environment

**Files to create:**
```txt
# requirements.txt
requests>=2.25.0,<3.0.0
```

**Files to modify:**
- `INSTALL.sh` (add pip install step)
- `README.md` (update prerequisites)

---

## Medium Priority (Nice to have)

### 6. Add Automated Tests
**Priority:** 🟢 Medium

**Tasks:**
- [ ] Unit tests for message parsing regex
- [ ] Unit tests for agent lookup logic
- [ ] Integration test for full workflow (mock Telegram API)
- [ ] Test error conditions (missing session, bad format, etc.)
- [ ] Add GitHub Actions CI workflow
- [ ] Test installer on fresh systems

**Files to create:**
- `tests/test_listener.py`
- `tests/test_integration.py`
- `.github/workflows/test.yml`

**Framework:** pytest

---

### 7. Add Configuration Validation
**Priority:** 🟢 Medium

**Tasks:**
- [ ] Validate bot token format on installation
- [ ] Validate chat ID format (negative for groups, positive for DM)
- [ ] Test bot connection before completing installation
- [ ] Add `tg-doctor` command to diagnose common issues
- [ ] Check for common misconfigurations

**Implementation:**
```bash
# New command: tg-doctor
tg-doctor() {
    # Check bot token format
    # Test API connection
    # Verify chat ID
    # Check tmux installation
    # Verify listener process
    # Check log permissions
}
```

---

### 8. Improve Installer UX
**Priority:** 🟢 Medium

**Tasks:**
- [ ] Add progress indicators during installation
- [ ] Better error messages if prerequisites missing
- [ ] Add uninstall script
- [ ] Support for fish shell
- [ ] Detect if listener is already running before starting
- [ ] Add interactive setup wizard option

**Files to create:**
- `UNINSTALL.sh` (new)

**Files to modify:**
- `INSTALL.sh`

---

### 9. Enhanced Logging
**Priority:** 🟢 Medium

**Tasks:**
- [ ] Add log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] Configurable log verbosity
- [ ] Structured logging (JSON format option)
- [ ] Log rotation built into daemon
- [ ] Performance metrics logging

**Files to modify:**
- `telegram_listener.py`

---

## Long-Term Enhancements

### 10. Multi-User Support
**Priority:** 🔵 Future

**Description:** Allow multiple Telegram users to control different tmux sessions

**Tasks:**
- [ ] User ID → session mapping
- [ ] Per-user configuration
- [ ] Access control for sessions
- [ ] User authentication

**Use case:** Team environments where multiple developers share infrastructure

---

### 11. Rich Media Support
**Priority:** 🔵 Future

**Tasks:**
- [ ] Send images to Telegram
- [ ] Send files/attachments
- [ ] Inline keyboards for quick replies
- [ ] Support receiving images/files from Telegram
- [ ] Voice message transcription

---

### 12. Platform Expansion
**Priority:** 🔵 Future

**Description:** Support additional messaging platforms

**Platforms:**
- [ ] WhatsApp (Twilio API)
- [ ] Slack
- [ ] Discord
- [ ] Signal (unofficial API)

**Architecture:**
- Rename to MessageMux or keep TeleMux with plugins
- Platform-agnostic router
- Unified message queue
- Per-platform listeners

---

### 13. Advanced Features
**Priority:** 🔵 Future

**Tasks:**
- [ ] Message threading/conversation tracking
- [ ] Multi-step workflows (conversation state machine)
- [ ] Template messages with variables
- [ ] Scheduled messages
- [ ] Message queue persistence (SQLite)
- [ ] Web dashboard for monitoring
- [ ] Metrics and analytics

---

### 14. Security Enhancements
**Priority:** 🔵 Future

**Tasks:**
- [ ] End-to-end encryption for stored messages
- [ ] API key rotation mechanism
- [ ] Rate limiting protection
- [ ] Audit logging for all actions
- [ ] Support for multiple bot tokens (failover)

---

## Documentation Tasks

### 15. Documentation Improvements
**Priority:** 🟢 Medium

**Tasks:**
- [ ] Add troubleshooting flowchart
- [ ] Create video tutorial/demo
- [ ] Add more real-world example scripts
- [ ] Document all error codes
- [ ] Create FAQ based on user questions
- [ ] Add architecture diagrams (proper ones, not ASCII)
- [ ] API documentation for programmatic usage

**Files to create/update:**
- `TROUBLESHOOTING.md` (new)
- `EXAMPLES.md` (new)
- `API.md` (new)

---

## Release Plan

### v0.9.1 (Next Patch)
**Target:** 1 week
**Focus:** Critical bug fixes

- [x] Remove system reminder tags from docs
- [x] Clean up README duplicates
- [x] Add Claude Code integration to installer
- [ ] Complete migration from `.team_mux` to `.telemux`
- [ ] Fix all path inconsistencies in logs

### v1.0.0 (Stable Release)
**Target:** 2-3 weeks
**Focus:** Production ready

**Must have:**
- [ ] All Critical issues resolved
- [ ] All High priority tasks completed
- [ ] Comprehensive testing
- [ ] Clean documentation
- [ ] No known bugs

**Checklist:**
- [ ] Migration complete
- [ ] Log rotation implemented
- [ ] Error handling improved
- [ ] Dependencies managed
- [ ] Tests passing
- [ ] Documentation complete
- [ ] Installer polished

### v1.1.0 (First Enhancement)
**Target:** 1-2 months
**Focus:** User feedback and polish

- [ ] Configuration validation
- [ ] Enhanced logging
- [ ] More example scripts
- [ ] Community feature requests

### v2.0.0 (Major Features)
**Target:** 3-6 months
**Focus:** Multi-platform support

- [ ] WhatsApp integration
- [ ] Slack integration
- [ ] Rich media support
- [ ] Multi-user support

---

## Contributing

Want to help? Pick a task from this roadmap and:

1. Open an issue referencing the task
2. Fork the repository
3. Create a feature branch
4. Submit a pull request

**Good first issues:**
- Documentation improvements
- Example scripts
- Test coverage
- Bug fixes

---

## Metrics for v1.0

### Code Quality
- [ ] Test coverage > 70%
- [ ] No lint errors
- [ ] All TODOs resolved
- [ ] Code documented

### Documentation
- [ ] All features documented
- [ ] Troubleshooting guide complete
- [ ] 5+ real-world examples
- [ ] FAQ with 10+ questions

### Stability
- [ ] No critical bugs
- [ ] 7+ days continuous uptime tested
- [ ] Handles 1000+ messages without issues
- [ ] Graceful degradation tested

### User Experience
- [ ] Installation < 5 minutes
- [ ] First message sent < 10 minutes
- [ ] Clear error messages
- [ ] Self-documenting commands

---

## Community Feedback

Current user count: ~5 (private testing)
Target for v1.0: Public release, documented, ready for community

**Feedback channels:**
- GitHub Issues
- Discussions tab
- Pull requests welcome

---

## Notes

### Known Limitations
- Requires tmux (by design)
- Single bot token per installation
- No message encryption at rest
- Long-polling only (no webhooks)

### Future Considerations
- Consider webhooks for faster delivery
- Consider message queue (Redis/RabbitMQ) for high volume
- Consider web UI for non-tmux users
- Consider mobile app integration

---

**Last updated:** 2025-11-09
**Current version:** 0.9.0
**Next milestone:** v1.0.0
