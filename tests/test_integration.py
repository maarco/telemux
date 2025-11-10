#!/usr/bin/env python3
"""
Integration tests for TeleMux
Tests full workflow with mocked Telegram API
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import telegram_listener


@pytest.mark.integration
class TestFullWorkflow:
    """Integration tests for complete message routing workflow"""

    @patch('telegram_listener.send_telegram_message')
    @patch('subprocess.run')
    def test_process_update_delivers_to_tmux(self, mock_subprocess, mock_send_telegram):
        """Test that process_update successfully delivers message to tmux session"""
        # Mock tmux list-sessions to show session exists
        mock_list_result = Mock()
        mock_list_result.returncode = 0
        mock_list_result.stdout = "test-session\nother-session\n"

        # Mock tmux send-keys to succeed
        mock_send_result = Mock()
        mock_send_result.returncode = 0
        mock_send_result.stdout = ""
        mock_send_result.stderr = ""

        # Return different mocks based on command
        def subprocess_side_effect(cmd, **kwargs):
            if 'list-sessions' in cmd:
                return mock_list_result
            else:
                return mock_send_result

        mock_subprocess.side_effect = subprocess_side_effect

        # Create update
        update = {
            "update_id": 12345,
            "message": {
                "text": "test-session: Deploy now",
                "from": {"first_name": "TestUser"}
            }
        }

        # Process update
        telegram_listener.process_update(update)

        # Verify tmux send-keys was called twice (text + Enter)
        assert mock_subprocess.call_count >= 3  # list-sessions + send-keys + send-keys (Enter)

        # Verify confirmation sent to Telegram
        mock_send_telegram.assert_called_once()
        call_args = mock_send_telegram.call_args[0][0]
        assert "test-session" in call_args
        assert "delivered" in call_args.lower()

    @patch('telegram_listener.send_telegram_message')
    @patch('subprocess.run')
    def test_process_update_session_not_found(self, mock_subprocess, mock_send_telegram):
        """Test that process_update handles missing tmux session"""
        # Mock tmux list-sessions showing no matching session
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "other-session\ndifferent-session\n"
        mock_subprocess.return_value = mock_result

        update = {
            "update_id": 12346,
            "message": {
                "text": "nonexistent-session: Deploy now",
                "from": {"first_name": "TestUser"}
            }
        }

        telegram_listener.process_update(update)

        # Verify error message sent to Telegram
        mock_send_telegram.assert_called_once()
        call_args = mock_send_telegram.call_args[0][0]
        assert "not found" in call_args.lower()

    @patch('telegram_listener.send_telegram_message')
    def test_process_update_invalid_format(self, mock_send_telegram):
        """Test that process_update ignores invalid message format"""
        update = {
            "update_id": 12347,
            "message": {
                "text": "Just a regular message without format",
                "from": {"first_name": "TestUser"}
            }
        }

        telegram_listener.process_update(update)

        # Should not send any Telegram message
        mock_send_telegram.assert_not_called()

    @patch('telegram_listener.send_telegram_message')
    @patch('subprocess.run')
    def test_process_update_no_tmux_sessions(self, mock_subprocess, mock_send_telegram):
        """Test handling when no tmux sessions are running"""
        # Mock tmux returning error (no sessions)
        mock_result = Mock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        update = {
            "update_id": 12348,
            "message": {
                "text": "test-session: Deploy now",
                "from": {"first_name": "TestUser"}
            }
        }

        telegram_listener.process_update(update)

        # Verify error message sent
        mock_send_telegram.assert_called_once()
        call_args = mock_send_telegram.call_args[0][0]
        assert "no tmux sessions" in call_args.lower()

    @patch('telegram_listener.send_telegram_message')
    @patch('subprocess.run')
    def test_process_update_sanitizes_input(self, mock_subprocess, mock_send_telegram):
        """Test that malicious input is sanitized to prevent command injection"""
        # Mock tmux session exists
        mock_list_result = Mock()
        mock_list_result.returncode = 0
        mock_list_result.stdout = "test-session\n"

        mock_send_result = Mock()
        mock_send_result.returncode = 0

        def subprocess_side_effect(cmd, **kwargs):
            if 'list-sessions' in cmd:
                return mock_list_result
            else:
                # Verify the message was sanitized (should be quoted)
                if 'send-keys' in cmd and len(cmd) > 3:
                    message = cmd[4]  # The message argument
                    # Should NOT contain unescaped shell metacharacters
                    assert '$(' not in message or "\\$(" in message or "'" in message
                return mock_send_result

        mock_subprocess.side_effect = subprocess_side_effect

        # Malicious input attempting command injection
        update = {
            "update_id": 12349,
            "message": {
                "text": "test-session: $(rm -rf /)",
                "from": {"first_name": "TestUser"}
            }
        }

        telegram_listener.process_update(update)

        # Verify message was delivered (after sanitization)
        mock_send_telegram.assert_called_once()


@pytest.mark.integration
class TestTelegramAPI:
    """Integration tests for Telegram API functions"""

    @patch('requests.get')
    def test_get_telegram_updates_success(self, mock_get):
        """Test successful Telegram API polling"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": [
                {"update_id": 1, "message": {"text": "test"}},
                {"update_id": 2, "message": {"text": "test2"}}
            ]
        }
        mock_get.return_value = mock_response

        # Set bot token for testing
        telegram_listener.BOT_TOKEN = "test-token"

        updates = telegram_listener.get_telegram_updates(offset=0)

        assert len(updates) == 2
        assert updates[0]["update_id"] == 1
        assert updates[1]["update_id"] == 2

    @patch('requests.get')
    def test_get_telegram_updates_retry_on_timeout(self, mock_get):
        """Test retry logic on timeout"""
        # TimeoutError is caught as unexpected exception, doesn't retry
        # Only requests.exceptions.Timeout retries
        import requests

        mock_response = Mock()
        mock_response.json.return_value = {"ok": True, "result": []}

        mock_get.side_effect = [
            requests.exceptions.Timeout("Connection timeout"),
            mock_response
        ]

        telegram_listener.BOT_TOKEN = "test-token"

        updates = telegram_listener.get_telegram_updates(offset=0, max_retries=2)

        # Should retry and eventually succeed
        assert updates == []
        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_get_telegram_updates_max_retries_exceeded(self, mock_get):
        """Test that max retries are respected"""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

        telegram_listener.BOT_TOKEN = "test-token"

        updates = telegram_listener.get_telegram_updates(offset=0, max_retries=3)

        # Should return empty list after max retries
        assert updates == []
        assert mock_get.call_count == 3

    @patch('requests.post')
    def test_send_telegram_message_success(self, mock_post):
        """Test successful message sending"""
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        telegram_listener.BOT_TOKEN = "test-token"
        telegram_listener.CHAT_ID = "12345"

        result = telegram_listener.send_telegram_message("Test message")

        assert result is True
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_send_telegram_message_retry_on_failure(self, mock_post):
        """Test retry logic when sending fails"""
        # First two calls fail, third succeeds
        import requests

        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}

        mock_post.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            requests.exceptions.ConnectionError("Network error"),
            mock_response
        ]

        telegram_listener.BOT_TOKEN = "test-token"
        telegram_listener.CHAT_ID = "12345"

        result = telegram_listener.send_telegram_message("Test", max_retries=3)

        assert result is True
        assert mock_post.call_count == 3


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEnd:
    """End-to-end tests simulating real workflow"""

    @patch('telegram_listener.get_telegram_updates')
    @patch('telegram_listener.send_telegram_message')
    @patch('subprocess.run')
    def test_full_workflow_agent_response(
        self, mock_subprocess, mock_send_telegram, mock_get_updates, tmp_path
    ):
        """Test complete workflow from Telegram message to tmux delivery"""
        # Note: The new code uses session-based routing (direct to tmux)
        # instead of agent-based routing (inbox files). This test verifies
        # the message reaches tmux successfully.

        # Mock tmux session exists
        mock_list_result = Mock()
        mock_list_result.returncode = 0
        mock_list_result.stdout = "deploy-session\n"

        mock_send_result = Mock()
        mock_send_result.returncode = 0
        mock_send_result.stdout = ""
        mock_send_result.stderr = ""

        def subprocess_side_effect(cmd, **kwargs):
            if 'list-sessions' in cmd:
                return mock_list_result
            return mock_send_result

        mock_subprocess.side_effect = subprocess_side_effect

        # Simulate Telegram update (user reply)
        update = {
            "update_id": 1,
            "message": {
                "text": "deploy-session: yes, proceed with deployment",
                "from": {"first_name": "TestUser"}
            }
        }

        # Process the update
        telegram_listener.process_update(update)

        # Verify tmux send-keys was called (text + Enter)
        assert mock_subprocess.call_count >= 3  # list-sessions + send-keys + send-keys (Enter)

        # Verify confirmation sent to Telegram
        mock_send_telegram.assert_called_once()
        call_args = mock_send_telegram.call_args[0][0]
        assert "deploy-session" in call_args
        assert "delivered" in call_args.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
