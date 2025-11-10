# TeleMux Test Suite

Automated tests for TeleMux to ensure reliability and catch regressions.

## Running Tests

### Install Test Dependencies

```bash
pip3 install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Run with Coverage

```bash
pytest --cov=telegram_listener --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── test_listener.py         # Unit tests for core functions
├── test_integration.py      # Integration tests with mocked APIs
└── README.md               # This file
```

## Test Categories

### Unit Tests (`test_listener.py`)

Tests individual functions in isolation:

- **Message Parsing**: `parse_message_id()`
  - Session name format: `session-name: message`
  - Old format: `msg-timestamp: message`
  - Invalid formats
  - Edge cases (multiline, special characters, etc.)

- **Agent Lookup**: `lookup_agent()`
  - Finding agents in outgoing log
  - Handling missing/malformed data

- **State Management**: `load_state()`, `save_state()`
  - Loading existing state
  - Creating new state
  - Directory creation

- **Routing**: `route_to_agent()`
  - Creating inbox files
  - Logging incoming messages

### Integration Tests (`test_integration.py`)

Tests complete workflows with mocked external dependencies:

- **Full Workflow**: Complete message routing from Telegram to tmux
- **Error Handling**: Missing sessions, invalid formats, network errors
- **Security**: Command injection prevention
- **Retry Logic**: Network timeout handling
- **End-to-End**: Complete agent communication cycle

## Writing New Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
def test_full_workflow():
    pass

@pytest.mark.slow
def test_performance():
    pass
```

### Mocking External Dependencies

Use `unittest.mock` for external calls:

```python
from unittest.mock import Mock, patch

@patch('telegram_listener.send_telegram_message')
@patch('subprocess.run')
def test_example(mock_subprocess, mock_telegram):
    # Your test here
    pass
```

### Using Temporary Directories

Use `tmp_path` fixture for file operations:

```python
def test_file_creation(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()
```

## Test Coverage Goals

- **Overall coverage**: > 70%
- **Critical functions**: 100%
  - `parse_message_id()`
  - `process_update()`
  - Security-related functions

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: pytest --cov=telegram_listener --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Import Errors

If you get import errors, ensure the parent directory is in PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Mock Issues

If mocks aren't working, verify the patch target:

```python
# Correct: Patch where it's used
@patch('telegram_listener.subprocess.run')

# Incorrect: Patch at source
@patch('subprocess.run')
```

### Temporary Directory Cleanup

Pytest automatically cleans up `tmp_path` directories. To keep them for debugging:

```bash
pytest --basetemp=test_output
```

## Future Test Additions

- [ ] Performance tests (1000+ messages)
- [ ] Stress tests (concurrent updates)
- [ ] Security penetration tests
- [ ] Long-running daemon stability tests
- [ ] Cross-platform compatibility tests

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
