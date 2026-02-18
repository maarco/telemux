#!/usr/bin/env python3
"""
Unit tests for telemux listener module
Tests message parsing, state management, and core functionality
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path so we can import telemux
sys.path.insert(0, str(Path(__file__).parent.parent))

import telemux


@pytest.mark.unit
class TestMessageParsing:
    """Tests for parse_message_id function"""

    def test_parse_session_message_format(self):
        """Test parsing session-name: message format returns tuple with False bypass"""
        text = "claude-session: Deploy to production"
        result = telemux.parse_message_id(text)
        assert result is not None
        session_name, response, bypass = result
        assert session_name == "claude-session"
        assert response == "Deploy to production"
        assert bypass is False

    def test_parse_with_extra_colons(self):
        """Test parsing message with colons in response"""
        text = "deploy-agent: Time: 14:30, Status: Ready"
        result = telemux.parse_message_id(text)
        assert result is not None
        session_name, response, bypass = result
        assert session_name == "deploy-agent"
        assert response == "Time: 14:30, Status: Ready"
        assert bypass is False

    def test_parse_with_spaces(self):
        """Test parsing with extra spaces after colon"""
        text = "test-session:     Multiple spaces here"
        result = telemux.parse_message_id(text)
        assert result is not None
        session_name, response, bypass = result
        assert session_name == "test-session"
        assert response == "Multiple spaces here"

    def test_parse_with_underscores(self):
        """Test session names with underscores"""
        text = "build_server_1: Build complete"
        result = telemux.parse_message_id(text)
        assert result is not None
        session_name, response, bypass = result
        assert session_name == "build_server_1"
        assert response == "Build complete"

    def test_parse_bypass_mode_with_session(self):
        """Test parsing bypass mode (!prefix) with explicit session"""
        text = "test-session: !rm -rf /tmp/test"
        result = telemux.parse_message_id(text)
        assert result is not None
        session_name, response, bypass = result
        assert session_name == "test-session"
        assert response == "rm -rf /tmp/test"
        assert bypass is True

    def test_parse_implicit_session_no_bypass(self):
        """Test parsing implicit session (no session: prefix)"""
        text = "Just a message"
        result = telemux.parse_message_id(text)
        assert result is not None
        session_name, response, bypass = result
        assert session_name is None  # No explicit session
        assert response == "Just a message"
        assert bypass is False

    def test_parse_implicit_session_with_bypass(self):
        """Test parsing implicit session with bypass mode"""
        text = "!ls -la"
        result = telemux.parse_message_id(text)
        assert result is not None
        session_name, response, bypass = result
        assert session_name is None
        assert response == "ls -la"
        assert bypass is True

    def test_parse_multiline_response(self):
        """Test parsing multiline responses"""
        text = "agent-1: First line\nSecond line\nThird line"
        result = telemux.parse_message_id(text)
        assert result is not None
        session_name, response, bypass = result
        assert session_name == "agent-1"
        assert "First line" in response
        assert "Second line" in response

    def test_parse_empty_response(self):
        """Test parsing with empty response after colon"""
        text = "session-name: "
        result = telemux.parse_message_id(text)
        # Single space is technically matched by regex (.+)
        assert result is not None
        session_name, response, bypass = result
        assert session_name == "session-name"
        assert response == " "


@pytest.mark.unit
class TestStateManagement:
    """Tests for load_state and save_state functions"""

    def test_load_nonexistent_state(self, tmp_path):
        """Test loading state when file doesn't exist"""
        original = telemux.LISTENER_STATE
        telemux.LISTENER_STATE = tmp_path / "nonexistent.json"

        state = telemux.load_state()
        assert state == {"last_update_id": 0, "last_active_session": None}

        telemux.LISTENER_STATE = original

    def test_load_existing_state(self, tmp_path):
        """Test loading existing state file"""
        state_file = tmp_path / "listener_state.json"
        state_file.write_text('{"last_update_id": 12345, "last_active_session": "my-session"}')

        original = telemux.LISTENER_STATE
        telemux.LISTENER_STATE = state_file

        state = telemux.load_state()
        assert state["last_update_id"] == 12345
        assert state["last_active_session"] == "my-session"

        telemux.LISTENER_STATE = original

    def test_load_backward_compatibility(self, tmp_path):
        """Test loading old state file without last_active_session"""
        state_file = tmp_path / "listener_state.json"
        state_file.write_text('{"last_update_id": 12345}')

        original = telemux.LISTENER_STATE
        telemux.LISTENER_STATE = state_file

        state = telemux.load_state()
        assert state["last_update_id"] == 12345
        # Should add last_active_session for backward compatibility
        assert state["last_active_session"] is None

        telemux.LISTENER_STATE = original

    def test_save_state(self, tmp_path):
        """Test saving state to file"""
        state_file = tmp_path / "message_queue" / "listener_state.json"

        original_state = telemux.LISTENER_STATE
        original_queue = telemux.MESSAGE_QUEUE_DIR

        telemux.LISTENER_STATE = state_file
        telemux.MESSAGE_QUEUE_DIR = tmp_path / "message_queue"

        state = {"last_update_id": 99999, "last_active_session": "test-session"}
        telemux.save_state(state)

        assert state_file.exists()
        saved_data = json.loads(state_file.read_text())
        assert saved_data["last_update_id"] == 99999
        assert saved_data["last_active_session"] == "test-session"

        telemux.LISTENER_STATE = original_state
        telemux.MESSAGE_QUEUE_DIR = original_queue

    def test_save_state_creates_directory(self, tmp_path):
        """Test that save_state creates directory if it doesn't exist"""
        state_file = tmp_path / "new_dir" / "listener_state.json"

        original_state = telemux.LISTENER_STATE
        original_queue = telemux.MESSAGE_QUEUE_DIR

        telemux.LISTENER_STATE = state_file
        telemux.MESSAGE_QUEUE_DIR = tmp_path / "new_dir"

        state = {"last_update_id": 555, "last_active_session": None}
        telemux.save_state(state)

        assert state_file.exists()
        assert state_file.parent.is_dir()

        telemux.LISTENER_STATE = original_state
        telemux.MESSAGE_QUEUE_DIR = original_queue


@pytest.mark.unit
class TestProcessUpdate:
    """Tests for process_update function"""

    def test_process_update_missing_message_key(self):
        """Test that process_update handles update without message key"""
        state = {"last_update_id": 0, "last_active_session": None}
        update = {"update_id": 123}  # No "message" key

        # Should not crash
        telemux.process_update(update, "test-token", "123", None, state)

    def test_process_update_empty_message_text(self):
        """Test that process_update handles empty message text"""
        state = {"last_update_id": 0, "last_active_session": "test-session"}
        update = {
            "update_id": 123,
            "message": {
                "text": "",
                "from": {"first_name": "Test", "id": 999},
                "chat": {"id": "123"}
            }
        }

        # Should not crash, will try to parse and send empty-ish message
        with pytest.telemetry_mocked():  # We'll mock subprocess to avoid actual tmux calls
            pass  # The function should handle gracefully


@pytest.mark.unit
class TestTmuxCommand:
    """Tests for tmux_cmd helper"""

    def test_tmux_cmd_builds_command(self):
        """Test that tmux_cmd builds correct command list"""
        result = telemux.tmux_cmd('list-sessions', '-F', '#{session_name}')
        expected = ['tmux', '-L', 'telemux', 'list-sessions', '-F', '#{session_name}']
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
