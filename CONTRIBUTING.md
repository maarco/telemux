# Contributing to TeleMux

Thank you for considering contributing to TeleMux! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, professional, and constructive. We're here to build great software together.

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report:
- Check the [existing issues](https://github.com/maarco/telemux/issues) to avoid duplicates
- Run `tg-doctor` to check your setup
- Check the logs with `tg-logs`

When creating a bug report, include:
- **TeleMux version**: Check CHANGELOG.md or run `git log --oneline | head -1`
- **Environment**: OS, Python version, tmux version
- **Steps to reproduce**: Clear, numbered steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Logs**: Relevant excerpts from `~/.telemux/telegram_listener.log`
- **Config**: Sanitized config (remove bot token!)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:
- Check the [ROADMAP.md](ROADMAP.md) to see if it's already planned
- Open an issue with the `enhancement` label
- Explain the use case and why it would be valuable
- Consider backward compatibility

### Pull Requests

1. **Fork and clone**
   ```bash
   git clone https://github.com/maarco/telemux.git
   cd telemux
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-number-description
   ```

3. **Make your changes**
   - Follow the coding style (see below)
   - Write tests for new features
   - Update documentation as needed

4. **Test your changes**
   ```bash
   # Run test suite
   pytest -v

   # Run specific tests
   pytest tests/test_listener.py -v

   # Check test coverage
   pytest --cov=telegram_listener --cov-report=html
   ```

5. **Lint your code**
   ```bash
   # Python
   flake8 telegram_listener.py

   # Shell scripts
   shellcheck *.sh
   ```

6. **Commit with a clear message**
   ```bash
   git commit -m "Add feature: description of what you did

   - Detailed point 1
   - Detailed point 2

   Fixes #issue_number"
   ```

7. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a PR on GitHub.

## Development Setup

### Prerequisites

```bash
# Install development dependencies
pip3 install -r requirements-dev.txt

# Install testing tools
pip3 install pytest pytest-cov pytest-mock flake8
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# With coverage
pytest --cov=telegram_listener --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Testing Locally

```bash
# Install your changes
./INSTALL.sh

# Start listener
tg-start

# Test in a tmux session
tmux new -s test-session
tg_alert "Test message"
tg_agent "test-agent" "Can you hear me?"

# Check logs
tg-logs
```

## Coding Style

### Python (telegram_listener.py)

- **PEP 8** compliant
- **Type hints** for function signatures
- **Docstrings** for all functions
- **4 spaces** for indentation
- **Max line length**: 127 characters

Example:
```python
def parse_message_id(text: str) -> Optional[Tuple[str, str]]:
    """
    Parse message ID and response from text

    Args:
        text: Message text in format "session-name: response"

    Returns:
        Tuple of (message_id, response) or None if invalid
    """
    pattern = r'^([\w-]+):\s*(.+)$'
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return None
```

### Shell Scripts

- **ShellCheck** compliant
- **Use `set -euo pipefail`** at the top
- **Quote all variables**: `"$variable"`
- **Use functions** for reusable code
- **Add comments** for complex logic

Example:
```bash
#!/usr/bin/env bash
set -euo pipefail

# Function description
function do_something() {
    local input="$1"

    if [[ -z "$input" ]]; then
        echo "Error: Input required"
        return 1
    fi

    echo "Processing: $input"
}
```

### Documentation

- **No emojis** in new code or docs (see docs/CLAUDE.md style guide)
- **Clear, technical prose**
- **Code examples** should be functional
- **Update relevant docs** when changing features

## Project Structure

```
telemux/
├── telegram_listener.py      # Main daemon
├── telegram_control.sh        # Control script
├── shell_functions.sh         # Shell integration
├── INSTALL.sh, UPDATE.sh, UNINSTALL.sh
├── benchmark.sh               # Performance testing
├── tests/
│   ├── test_listener.py       # Unit tests
│   ├── test_integration.py    # Integration tests
│   └── README.md              # Testing guide
├── docs/
│   ├── QUICKSTART.md
│   ├── CLAUDE.md             # Technical docs
│   ├── SECURITY_AUDIT.md
│   └── COMPATIBLE_LLMS.md
└── examples/                  # Usage examples
```

## Testing Guidelines

### Unit Tests

- Test individual functions in isolation
- Use mocks for external dependencies
- Fast execution (<1s per test)
- Place in `tests/test_listener.py`

### Integration Tests

- Test complete workflows
- Mock Telegram API (use `responses` library)
- Mock subprocess calls
- Place in `tests/test_integration.py`

### Test Naming

```python
def test_feature_behavior():
    """Test that feature does X when Y"""
    pass

def test_feature_edge_case():
    """Test feature handles edge case Z"""
    pass
```

## Documentation Guidelines

### README.md

- Keep examples up to date
- Test all command examples
- Update feature list when adding features

### CHANGELOG.md

- Follow [Keep a Changelog](https://keepachangelog.com/) format
- Categories: Added, Changed, Deprecated, Removed, Fixed, Security
- Add entries as you develop features

### Code Comments

- Explain **why**, not **what**
- Document **security-critical** sections
- Note **TODOs** with issue numbers

## Security

- **Never commit credentials** (bot tokens, chat IDs)
- **Sanitize user input** (see `shlex.quote()` usage)
- **Review command injection risks** in new features
- **Run security audit** checklist for security-related changes

## Release Process

1. Update version in CHANGELOG.md
2. Run full test suite
3. Run security audit checklist
4. Update ROADMAP.md
5. Create git tag: `git tag v1.0.0`
6. Push: `git push origin v1.0.0`
7. Create GitHub release with CHANGELOG excerpt

## Getting Help

- **Questions**: Open a [discussion](https://github.com/maarco/telemux/discussions)
- **Bugs**: Open an [issue](https://github.com/maarco/telemux/issues)
- **Documentation**: Check [README.md](README.md) and [docs/](docs/)
- **Chat**: (Add Discord/Slack link when available)

## Good First Issues

Looking for something to work on? Check issues labeled:
- `good first issue` - Perfect for newcomers
- `help wanted` - Maintainers need help
- `documentation` - Improve docs
- `tests` - Add test coverage

## Recognition

Contributors will be:
- Listed in CHANGELOG.md for their contributions
- Credited in release notes
- Added to a CONTRIBUTORS.md file (coming soon)

## Questions?

Open a discussion or reach out via issues. We're happy to help!

---

**Happy contributing!** 🚀

Thank you for making TeleMux better!
