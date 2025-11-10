# Changelog

All notable changes to TeleMux will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - v1.0.0

### Planned
- Production testing completion (7+ days with 3+ users)
- Performance benchmarking validation (1000+ messages)
- Security audit execution
- Public release announcement

## [0.9.1] - 2025-11-10

### Added
- **Comprehensive test suite** (56 passing tests)
  - Unit tests for message parsing, agent lookup, state management
  - Integration tests with mocked Telegram API
  - Security tests for command injection prevention
  - Test coverage >70% of critical paths
- **Performance benchmarking tool** (`benchmark.sh`)
  - Configurable message count and delays
  - Success rate validation (95%+ threshold)
  - Comprehensive logging and metrics
- **Security audit checklist** (`SECURITY_AUDIT.md`)
  - 50+ checks across 13 security categories
  - Credential management validation
  - Command injection prevention tests
- **Documentation improvements**
  - Organized docs into `docs/` folder
  - Added emoji-free style guide
  - Created `.env.example` template
  - Fixed config path errors in README (9 instances)
- **GitHub Actions CI/CD**
  - Automated testing on push/PR
  - Multi-version Python support (3.8-3.12)
  - Code linting and shellcheck
  - Coverage reporting

### Fixed
- README.md config paths (`~/.telegram_config` → `~/.telemux/telegram_config`)
- Shell function installation instructions now match INSTALL.sh
- Missing v0.9.1 command aliases in documentation

### Changed
- Simplified shell function installation (source from single file)
- Cleaned up 7 development artifact files

## [0.9.0] - 2025-11-09

### Added
- **Log rotation system** (`cleanup-logs.sh`)
  - 10MB size limit with automatic archiving
  - Archives to `message_queue/archive/YYYY-MM/`
  - Auto-cleanup of archives older than 6 months
  - Optional cron job installation
  - New command: `tg-cleanup`
- **Health check diagnostics** (`tg-doctor`)
  - Validates tmux, Python, dependencies
  - Checks config file format and permissions
  - Tests bot connection
  - Validates chat ID format
  - Shows message queue statistics
- **Enhanced error handling**
  - Retry logic with exponential backoff (3 attempts)
  - Separate timeout and connection error handling
  - Better error messages for common failures
  - Graceful degradation when Telegram unreachable
  - Separate error log file (`telegram_errors.log`)
- **Dependency management**
  - Created `requirements.txt` with pinned versions
  - Updated INSTALL.sh to check/install dependencies
  - Python version detection
  - Graceful handling when pip3 not available
- **Enhanced logging**
  - Configurable log levels (DEBUG/INFO/WARNING/ERROR)
  - `TELEMUX_LOG_LEVEL` environment variable
  - Separate error log file
  - Multiple handlers with different levels
- **Migration and uninstall tools**
  - `MIGRATE.sh` - Migrate from legacy `.team_mux` paths
  - `UNINSTALL.sh` - Complete removal with backup option
  - `UPDATE.sh` - Upgrade existing installations

### Fixed
- Documentation inconsistencies (function names, branding)
- Path references (updated `.team_mux` → `.telemux`)
- All TODOs resolved

### Changed
- Environment variables: `TELEGRAM_*` → `TELEMUX_TG_*`
- Project renamed from "Team Mux" to "TeleMux"
- Moved from `~/.team_mux/` to `~/.telemux/`

## [0.1.0] - 2025-11-09

### Added
- Initial release of TeleMux bidirectional Telegram bridge
- **Core Features**
  - `tg_alert()` - Send one-way notifications to Telegram
  - `tg_agent()` - Bidirectional agent messaging
  - `tg_done()` - Alert when commands complete
- **Listener Daemon**
  - Python daemon with long-polling
  - Runs 24/7 in dedicated tmux session
  - Auto-recovery on restart
  - State management for message tracking
- **Message Queue System**
  - Persistent logging of all messages
  - Inbox files for each agent
  - Audit trail for sent/received messages
- **Clean API**
  - Session name as message ID (simple format)
  - Formatted delivery: `message`
  - Proper tmux injection with sleep + Enter
- **Control Commands**
  - `tg-start` / `tg-stop` / `tg-restart`
  - `tg-status` - Check listener status
  - `tg-logs` - View logs
  - `tg-attach` - Attach to listener session
- **Components**
  - `telegram_listener.py` - Main listener daemon
  - `telegram_control.sh` - Control script
  - `shell_functions.sh` - Shell integration
  - `INSTALL.sh` - Automated installer
- **Documentation**
  - README.md - Complete user guide
  - QUICKSTART.md - 5-minute setup
  - CLAUDE.md - Technical documentation
  - Example scripts (deployment, build, agent questions)

### Requirements
- tmux
- Python 3.6+
- curl
- Telegram bot (via @BotFather)

---

## Future Enhancements

### v1.1.0 (Planned)
- Multiple chat support (group + personal DM)
- Rich message formatting (markdown, buttons)
- Message threading/conversations
- Command shortcuts (/deploy, /status, etc.)
- Fish shell support
- Interactive setup wizard

### v1.2.0 (Planned)
- Web dashboard for message history
- Agent status monitoring
- Message analytics and insights
- Performance optimizations

### v2.0.0 (Planned - Multi-Platform)
- WhatsApp integration (Twilio API)
- Slack integration
- Discord integration
- Multi-user support
- Permission system
- Approval workflows

---

**Repository:** https://github.com/maarco/telemux
**License:** MIT
**Maintainer:** Marco (with Claude Code)
