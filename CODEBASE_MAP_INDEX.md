# TeleMux Codebase Mapping - Complete Index

**Generated:** 2025-11-09  
**Comprehensiveness Level:** VERY THOROUGH (all files, all functions, all dependencies)  
**Document Status:** READY FOR PRODUCTION

---

## Quick Navigation

This mapping provides **complete visibility** into the TeleMux codebase. Choose your entry point:

### For Quick Answers
→ **[CODEBASE_MAP_QUICK_REF.txt](CODEBASE_MAP_QUICK_REF.txt)** (single-page cheat sheet)
- Function locations
- File line numbers
- Message flow diagrams
- DRY violations summary

### For Detailed Analysis
→ **[CODEBASE_MAP.md](CODEBASE_MAP.md)** (17 comprehensive sections)
- Complete source code analysis
- Deep dives into each function
- Configuration file structure
- Testing infrastructure
- Dependencies diagram
- Entry points for changes

### For This Document
→ **[CODEBASE_MAP_INDEX.md](CODEBASE_MAP_INDEX.md)** (this file)
- Navigation guide
- Key findings summary
- What was mapped
- How to use these documents

---

## What Was Mapped

### 1. Shell Functions (tg_* commands)
- [x] Source definition location (INSTALL.sh lines 113-198)
- [x] Deployment location (.zshrc lines 218-303)
- [x] Documentation copy (README.md lines 119-187)
- [x] Line-by-line analysis
- [x] Parameter handling
- [x] Message format specifications

**Functions Mapped:**
- `tg_alert()` - Simple one-way alerts
- `tg_agent()` - Bidirectional messaging
- `tg_done()` - Command completion notifications
- `tg-*` aliases - Control commands

### 2. Python Daemon (telegram_listener.py)
- [x] Source location (401 lines)
- [x] Deployed location (~/.telemux)
- [x] All 6 key functions analyzed
- [x] Configuration loading mechanism
- [x] Logging setup
- [x] Telegram API integration
- [x] Message routing logic

**Functions Mapped:**
- `load_telegram_config()`
- `load_state()`
- `parse_message_id()`
- `lookup_agent()`
- `route_to_agent()`
- `process_update()`
- `get_telegram_updates()`
- `send_telegram_message()`
- `main()` loop

### 3. Control Scripts (telegram_control.sh)
- [x] Source location (256 lines)
- [x] Deployed location (~/.telemux)
- [x] All 8 commands documented
- [x] Health check (tg-doctor) analysis

**Commands Mapped:**
- start, stop, restart, status, logs, attach, cleanup, doctor

### 4. Configuration Files
- [x] telegram_config (credentials)
- [x] listener_state.json (persistence)
- [x] outgoing.log (message registry)
- [x] incoming.log (message history)
- [x] Agent inboxes (per-agent structure)

### 5. Installation & Update Scripts
- [x] INSTALL.sh (main installation)
- [x] UPDATE.sh (upgrade mechanism)
- [x] UNINSTALL.sh (removal)
- [x] MIGRATE.sh (legacy migration)

### 6. Documentation & Examples
- [x] README.md (user guide)
- [x] CLAUDE.md (technical docs)
- [x] IMPLEMENTATION_PLAN.md (future roadmap)
- [x] examples/ directory (3 workflow examples)

### 7. Testing Infrastructure
- [x] Current test status (none exist)
- [x] Installation validation (bot connection test)
- [x] Health check system (tg-doctor)
- [x] Recommendations for test suite

---

## Key Findings

### DRY Analysis
**Status:** MINOR DRY VIOLATIONS

| Component | Location 1 | Location 2 | Location 3 | Issue |
|-----------|-----------|-----------|-----------|-------|
| `tg_alert()` | INSTALL.sh:125-144 | README.md:119-135 | .zshrc:227-246 | Duplicated 3 times |
| `tg_agent()` | INSTALL.sh:147-175 | README.md:138-166 | .zshrc:249-277 | Duplicated 3 times |
| `tg_done()` | INSTALL.sh:178-187 | README.md:169-177 | .zshrc:280-289 | Duplicated 3 times |

**Assessment:** Source of truth is INSTALL.sh. README.md is documentation copy (expected). .zshrc is deployed via INSTALL.sh append. All versions currently identical.

### Message ID Confusion
**Finding:** Two formats coexist in production
- Old: `msg-{timestamp}-{random}` (8 entries)
- New: `{session-name}` (1 entry)

**Impact:** Both formats still handled by parser. Users may be confused by format switching.

### Pre-Registration Requirement
**Finding:** Current architecture requires messages to be pre-registered in outgoing.log to receive replies

**Impact:** 
- `tg_agent()` works (pre-registers + sends)
- `tg_alert()` sends but can't receive replies (no pre-registration)

**Proposed Fix:** IMPLEMENTATION_PLAN.md suggests removing this requirement

### No Automated Tests
**Finding:** Only manual installation validation exists

**Gap:** No unit tests, shell tests, or integration tests

---

## Message Flow Architecture

### Outgoing (Agent → Telegram)

```
User in tmux session
    ↓
  tg_agent "deploy-agent" "Deploy now?"  [.zshrc:249-277]
    ↓
  Get tmux session name: $(tmux display-message -p '#S')
    ↓
  Append to outgoing.log: "{session_id}:{agent_name}:{session}:{timestamp}"
    ↓
  curl POST to Telegram API
    ↓
  User receives message on phone
```

### Incoming (Telegram → Agent)

```
User replies on Telegram: "session-name: yes deploy"
    ↓
  telegram_listener.py polls Telegram (long-polling)
    ↓
  parse_message_id("session-name: yes deploy")
    Result: ("session-name", "yes deploy")
    ↓
  lookup_agent("session-name") from outgoing.log
    Result: {agent_name, tmux_session, timestamp}
    ↓
  route_to_agent():
    a. Create ~/.telemux/agents/{agent_name}/inbox.txt
    b. Write response to inbox file
    c. Log to incoming.log
    d. Check if tmux session is active
    e. If active: send via tmux send-keys (with 1s sleep!)
    f. Send confirmation to Telegram
    ↓
  User sees "[FROM USER via Telegram] yes deploy" in their tmux session
```

---

## Critical Code Locations

### Message Parsing
**File:** telegram_listener.py  
**Function:** `parse_message_id()` Lines 207-220  
**Regex:** `r'^([\w-]+):\s*(.+)$'`  
**Purpose:** Extract session-name and response from user message

### Agent Lookup
**File:** telegram_listener.py  
**Function:** `lookup_agent()` Lines 223-242  
**Source:** ~/.telemux/message_queue/outgoing.log  
**Purpose:** Find agent_name and tmux_session for incoming message

### Message Delivery
**File:** telegram_listener.py  
**Function:** `route_to_agent()` Lines 245-315  
**Critical:** Line 299 - Sleep 1 second before tmux Enter (buffer time!)  
**Purpose:** Write to inbox, log, deliver to tmux session

### Main Loop
**File:** telegram_listener.py  
**Function:** `process_update()` Lines 317-345  
**Purpose:** Route each Telegram message to correct agent

---

## Files to Know

### Source Control (Repository Root)
```
/Users/malmazan/dev/telemux/
├── INSTALL.sh              (SHELL FUNCTIONS SOURCE)
├── UPDATE.sh               (UPGRADE SCRIPT)
├── telegram_listener.py    (PYTHON DAEMON SOURCE)
├── telegram_control.sh     (CONTROL SCRIPT SOURCE)
├── README.md               (DOCUMENTATION)
├── CLAUDE.md               (TECHNICAL DOCS)
├── IMPLEMENTATION_PLAN.md  (FUTURE ROADMAP)
├── CODEBASE_MAP.md         (THIS MAPPING - DETAILED)
└── examples/               (3 WORKFLOW EXAMPLES)
```

### Installation (User's Home)
```
~/.zshrc                                 (SHELL FUNCTIONS DEPLOYED)
~/.telemux/
├── telegram_config                      (CREDENTIALS)
├── telegram_listener.py                 (DAEMON DEPLOYED)
├── telegram_control.sh                  (CONTROL SCRIPT DEPLOYED)
├── telegram_listener.log                (MAIN LOG)
├── telegram_errors.log                  (ERROR LOG)
└── message_queue/
    ├── outgoing.log                     (SENT MESSAGES)
    ├── incoming.log                     (RECEIVED MESSAGES)
    └── listener_state.json              (STATE TRACKING)
```

---

## Using This Mapping

### For Test Suite Design
1. Read **CODEBASE_MAP.md SECTION 9** (Testing Infrastructure)
2. Review SECTION 14 (Recommendations) for test structure
3. Use function locations from SECTION 3 (telegram_listener.py) for unit tests

### For DRY Refactoring
1. Read **CODEBASE_MAP_QUICK_REF.txt** (DRY VIOLATIONS section)
2. Review SECTION 2 in **CODEBASE_MAP.md** (DRY Analysis)
3. See SECTION 14 (Recommendation 1) for refactoring plan

### For Bug Fixes
1. Use CODEBASE_MAP_QUICK_REF.txt to locate the function
2. Review CODEBASE_MAP.md for detailed analysis
3. Follow SECTION 17 (Entry Points for Changes)

### For New Features
1. Check IMPLEMENTATION_PLAN.md for planned changes
2. Review message flow diagrams in this mapping
3. Identify which file(s) need changes
4. Follow SECTION 17 entry points

### For Developer Onboarding
1. Start with **CODEBASE_MAP_QUICK_REF.txt** (30 min read)
2. Review CODEBASE_MAP.md SECTIONS 1-6 (1 hour)
3. Run `tg-doctor` to understand real installation
4. Review example scripts in examples/

---

## Critical Insights

### What Makes TeleMux Work
1. **Session Name as Message ID** - Clever use of tmux session name for routing
2. **Long-Polling** - Telegram long-polling with 30s timeout + 3 retries
3. **Inbox Files** - Persistent message storage, independent of tmux session
4. **tmux send-keys** - Direct message injection to active sessions
5. **1-Second Sleep** - Critical timing for tmux text buffering (Line 299 of daemon)

### Architecture Strengths
- Clean separation: shell functions ↔ Python daemon ↔ Telegram API
- Resilient: messages persist in inbox if tmux session dies
- Flexible: can route to any active tmux session
- Debuggable: comprehensive logging to two log files

### Architecture Weaknesses
- Pre-registration requirement (planned fix in IMPLEMENTATION_PLAN.md)
- Mixed message ID formats (legacy + new)
- No automatic inbox file cleanup
- No rate limiting per chat/user
- No encryption for local files

---

## Next Steps

### Immediate (Ready to Do)
1. Create test suite (no tests exist currently)
2. Fix DRY violations (extract shell_functions.sh)
3. Standardize message ID format (migrate old → new)

### Short Term (per IMPLEMENTATION_PLAN.md)
1. Remove pre-registration requirement
2. Make `tg_alert()` bidirectional
3. Simplify message routing logic

### Long Term (Future)
1. Add support for multiple platforms (WhatsApp, Slack, Discord)
2. Support rich media (images, files, buttons)
3. Multi-user support (different users → different sessions)

---

## Document Maintenance

### This Mapping Stays Current When:
- [ ] You're about to change shell functions → Update CODEBASE_MAP.md SECTION 1
- [ ] You're modifying Python daemon → Update CODEBASE_MAP.md SECTION 3
- [ ] You're changing control script → Update CODEBASE_MAP.md SECTION 4
- [ ] Configuration changes → Update CODEBASE_MAP.md SECTION 5
- [ ] New test suite added → Update CODEBASE_MAP.md SECTION 9

### How to Keep This Updated
1. When you modify a file, note the line numbers
2. Update the corresponding SECTION in CODEBASE_MAP.md
3. Update CODEBASE_MAP_QUICK_REF.txt line numbers
4. Commit both files together

---

## Related Documentation

- **CLAUDE.md** - Technical architecture deep dive (this repo)
- **IMPLEMENTATION_PLAN.md** - Future roadmap (this repo)
- **README.md** - User guide (this repo)
- **CHANGELOG.md** - Version history (this repo)

---

## Summary

**This mapping provides:**
- ✅ Complete file locations with line numbers
- ✅ Function-by-function analysis
- ✅ Message flow diagrams
- ✅ DRY violation assessment
- ✅ Testing recommendations
- ✅ Dependency charts
- ✅ Entry points for changes
- ✅ Architecture weaknesses identified

**Ready for:**
- ✅ Test suite design
- ✅ DRY refactoring
- ✅ Developer onboarding
- ✅ Bug fix planning
- ✅ Feature planning

---

**Total Lines Analyzed:** 2000+  
**Total Files Examined:** 15+  
**Functions Documented:** 20+  
**DRY Violations Identified:** 3  
**Critical Findings:** 5  

**Mapping Status:** COMPLETE & PRODUCTION-READY

