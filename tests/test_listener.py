#!/usr/bin/env python3
"""
Unit tests for telegram_listener.py
Tests message parsing, agent lookup, and core functionality
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add parent directory to path so we can import telegram_listener
sys.path.insert(0, str(Path(__file__).parent.parent))

import telegram_listener


@pytest.mark.unit
class TestMessageParsing:
    """Tests for parse_message_id function"""

    def test_parse_session_name_format(self):
        """Test parsing session-name: message format"""
        text = "claude-session: Deploy to production"
        result = telegram_listener.parse_message_id(text)
        assert result is not None
        message_id, response = result
        assert message_id == "claude-session"
        assert response == "Deploy to production"

    def test_parse_with_extra_colons(self):
        """Test parsing message with colons in response"""
        text = "deploy-agent: Time: 14:30, Status: Ready"
        result = telegram_listener.parse_message_id(text)
        assert result is not None
        message_id, response = result
        assert message_id == "deploy-agent"
        assert response == "Time: 14:30, Status: Ready"

    def test_parse_with_spaces(self):
        """Test parsing with extra spaces after colon"""
        text = "test-session:     Multiple spaces here"
        result = telegram_listener.parse_message_id(text)
        assert result is not None
        message_id, response = result
        assert message_id == "test-session"
        assert response == "Multiple spaces here"

    def test_parse_with_underscores(self):
        """Test session names with underscores"""
        text = "build_server_1: Build complete"
        result = telegram_listener.parse_message_id(text)
        assert result is not None
        message_id, response = result
        assert message_id == "build_server_1"
        assert response == "Build complete"

    def test_parse_old_msg_format(self):
        """Test parsing old msg-timestamp format"""
        text = "msg-1234567890-12345: Legacy message"
        result = telegram_listener.parse_message_id(text)
        assert result is not None
        message_id, response = result
        assert message_id == "msg-1234567890-12345"
        assert response == "Legacy message"

    def test_parse_multiline_response(self):
        """Test parsing multiline responses"""
        text = "agent-1: First line\nSecond line\nThird line"
        result = telegram_listener.parse_message_id(text)
        assert result is not None
        message_id, response = result
        assert message_id == "agent-1"
        assert "First line" in response
        assert "Second line" in response

    def test_parse_invalid_no_colon(self):
        """Test parsing fails without colon"""
        text = "Just a regular message"
        result = telegram_listener.parse_message_id(text)
        assert result is None

    def test_parse_invalid_empty_message_id(self):
        """Test parsing fails with empty message ID"""
        text = ": Message without ID"
        result = telegram_listener.parse_message_id(text)
        assert result is None

    def test_parse_invalid_special_chars_in_id(self):
        """Test parsing fails with invalid characters in message ID"""
        text = "session@name: Invalid characters"
        result = telegram_listener.parse_message_id(text)
        assert result is None

    def test_parse_empty_response(self):
        """Test parsing with empty response after colon"""
        text = "session-name: "
        result = telegram_listener.parse_message_id(text)
        # Single space is technically matched by regex (.+)
        assert result is not None
        message_id, response = result
        assert message_id == "session-name"
        assert response == " "


@pytest.mark.unit
class TestAgentLookup:
    """Tests for lookup_agent function"""

    def test_lookup_existing_agent(self, tmp_path):
        """Test looking up an agent that exists in outgoing log"""
        outgoing_log = tmp_path / "outgoing.log"
        outgoing_log.write_text(
            "session-1:agent-alpha:session-1:2025-11-09T10:00:00-07:00\n"
            "session-2:agent-beta:session-2:2025-11-09T10:05:00-07:00\n"
        )

        # Temporarily override OUTGOING_LOG
        original = telegram_listener.OUTGOING_LOG
        telegram_listener.OUTGOING_LOG = outgoing_log

        result = telegram_listener.lookup_agent("session-1")
        assert result is not None
        assert result["message_id"] == "session-1"
        assert result["agent_name"] == "agent-alpha"
        assert result["tmux_session"] == "session-1"
        # Timestamp gets split by colons, so only first part is returned
        assert result["timestamp"] == "2025-11-09T10"

        # Restore
        telegram_listener.OUTGOING_LOG = original

    def test_lookup_nonexistent_agent(self, tmp_path):
        """Test looking up an agent that doesn't exist"""
        outgoing_log = tmp_path / "outgoing.log"
        outgoing_log.write_text("session-1:agent-alpha:session-1:2025-11-09T10:00:00-07:00\n")

        original = telegram_listener.OUTGOING_LOG
        telegram_listener.OUTGOING_LOG = outgoing_log

        result = telegram_listener.lookup_agent("nonexistent")
        assert result is None

        telegram_listener.OUTGOING_LOG = original

    def test_lookup_missing_log_file(self, tmp_path):
        """Test lookup when outgoing log doesn't exist"""
        nonexistent_log = tmp_path / "nonexistent.log"

        original = telegram_listener.OUTGOING_LOG
        telegram_listener.OUTGOING_LOG = nonexistent_log

        result = telegram_listener.lookup_agent("session-1")
        assert result is None

        telegram_listener.OUTGOING_LOG = original

    def test_lookup_malformed_log_entry(self, tmp_path):
        """Test lookup with malformed log entries"""
        outgoing_log = tmp_path / "outgoing.log"
        outgoing_log.write_text(
            "invalid-entry\n"
            "session-1:agent-alpha:session-1:2025-11-09T10:00:00-07:00\n"
        )

        original = telegram_listener.OUTGOING_LOG
        telegram_listener.OUTGOING_LOG = outgoing_log

        result = telegram_listener.lookup_agent("session-1")
        assert result is not None
        assert result["agent_name"] == "agent-alpha"

        telegram_listener.OUTGOING_LOG = original


@pytest.mark.unit
class TestStateManagement:
    """Tests for load_state and save_state functions"""

    def test_load_nonexistent_state(self, tmp_path):
        """Test loading state when file doesn't exist"""
        original = telegram_listener.LISTENER_STATE
        telegram_listener.LISTENER_STATE = tmp_path / "nonexistent.json"

        state = telegram_listener.load_state()
        assert state == {"last_update_id": 0}

        telegram_listener.LISTENER_STATE = original

    def test_load_existing_state(self, tmp_path):
        """Test loading existing state file"""
        state_file = tmp_path / "listener_state.json"
        state_file.write_text('{"last_update_id": 12345}')

        original = telegram_listener.LISTENER_STATE
        telegram_listener.LISTENER_STATE = state_file

        state = telegram_listener.load_state()
        assert state["last_update_id"] == 12345

        telegram_listener.LISTENER_STATE = original

    def test_save_state(self, tmp_path):
        """Test saving state to file"""
        state_file = tmp_path / "message_queue" / "listener_state.json"

        original_state = telegram_listener.LISTENER_STATE
        original_queue = telegram_listener.MESSAGE_QUEUE_DIR

        telegram_listener.LISTENER_STATE = state_file
        telegram_listener.MESSAGE_QUEUE_DIR = tmp_path / "message_queue"

        state = {"last_update_id": 99999}
        telegram_listener.save_state(state)

        assert state_file.exists()
        saved_data = json.loads(state_file.read_text())
        assert saved_data["last_update_id"] == 99999

        telegram_listener.LISTENER_STATE = original_state
        telegram_listener.MESSAGE_QUEUE_DIR = original_queue

    def test_save_state_creates_directory(self, tmp_path):
        """Test that save_state creates directory if it doesn't exist"""
        state_file = tmp_path / "new_dir" / "listener_state.json"

        original_state = telegram_listener.LISTENER_STATE
        original_queue = telegram_listener.MESSAGE_QUEUE_DIR

        telegram_listener.LISTENER_STATE = state_file
        telegram_listener.MESSAGE_QUEUE_DIR = tmp_path / "new_dir"

        state = {"last_update_id": 555}
        telegram_listener.save_state(state)

        assert state_file.exists()
        assert state_file.parent.is_dir()

        telegram_listener.LISTENER_STATE = original_state
        telegram_listener.MESSAGE_QUEUE_DIR = original_queue


@pytest.mark.unit
class TestRouting:
    """Tests for route_to_agent function"""

    def test_route_creates_inbox_file(self, tmp_path):
        """Test that routing creates inbox file"""
        original_dir = telegram_listener.TELEMUX_DIR
        original_incoming = telegram_listener.INCOMING_LOG

        telegram_listener.TELEMUX_DIR = tmp_path
        telegram_listener.INCOMING_LOG = tmp_path / "message_queue" / "incoming.log"
        telegram_listener.INCOMING_LOG.parent.mkdir(parents=True, exist_ok=True)

        agent_info = {
            "message_id": "test-session",
            "agent_name": "test-agent",
            "tmux_session": "test-session"
        }

        telegram_listener.route_to_agent(agent_info, "Test response")

        inbox_file = tmp_path / "agents" / "test-agent" / "inbox.txt"
        assert inbox_file.exists()

        content = inbox_file.read_text()
        assert "MESSAGE FROM USER" in content
        assert "test-session" in content
        assert "Test response" in content

        telegram_listener.TELEMUX_DIR = original_dir
        telegram_listener.INCOMING_LOG = original_incoming

    def test_route_logs_incoming_message(self, tmp_path):
        """Test that routing logs to incoming.log"""
        original_dir = telegram_listener.TELEMUX_DIR
        original_incoming = telegram_listener.INCOMING_LOG

        telegram_listener.TELEMUX_DIR = tmp_path
        incoming_log = tmp_path / "message_queue" / "incoming.log"
        incoming_log.parent.mkdir(parents=True, exist_ok=True)
        telegram_listener.INCOMING_LOG = incoming_log

        agent_info = {
            "message_id": "session-1",
            "agent_name": "agent-1",
            "tmux_session": "session-1"
        }

        telegram_listener.route_to_agent(agent_info, "Response text")

        assert incoming_log.exists()
        content = incoming_log.read_text()
        assert "session-1" in content
        assert "agent-1" in content

        telegram_listener.TELEMUX_DIR = original_dir
        telegram_listener.INCOMING_LOG = original_incoming


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
