#!/usr/bin/env python3
"""
Unit tests for telegram_listener.py - NEW SESSION-BASED ROUTING

These tests verify the NEW behavior (per IMPLEMENTATION_PLAN.md):
- Route messages directly to tmux sessions (no pre-registration)
- Check if tmux session exists
- Show active sessions if target doesn't exist
- Make tg_alert bidirectional

These tests should FAIL initially (TDD red phase).
After implementing the new routing logic, they should PASS (green phase).
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Add parent directory to path to import telegram_listener
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the module we're testing
import telegram_listener


class TestParseMessageId(unittest.TestCase):
    """Test message parsing (session-name: message format)"""

    def test_parse_valid_session_message(self):
        """Parse valid 'session-name: message' format"""
        result = telegram_listener.parse_message_id("claude-session: hello world")
        self.assertEqual(result, ("claude-session", "hello world"))

    def test_parse_session_with_dashes(self):
        """Parse session name with dashes"""
        result = telegram_listener.parse_message_id("team-mux-setup: test message")
        self.assertEqual(result, ("team-mux-setup", "test message"))

    def test_parse_session_with_underscores(self):
        """Parse session name with underscores"""
        result = telegram_listener.parse_message_id("test_session: message")
        self.assertEqual(result, ("test_session", "message"))

    def test_parse_message_with_colons(self):
        """Parse message that contains colons"""
        result = telegram_listener.parse_message_id("session: message with: colons")
        self.assertEqual(result, ("session", "message with: colons"))

    def test_parse_message_with_extra_spaces(self):
        """Parse message with extra spaces after colon"""
        result = telegram_listener.parse_message_id("session:    message")
        self.assertEqual(result, ("session", "message"))

    def test_parse_invalid_no_colon(self):
        """Reject message without colon"""
        result = telegram_listener.parse_message_id("invalid message")
        self.assertIsNone(result)

    def test_parse_invalid_empty_session(self):
        """Reject message with empty session name"""
        result = telegram_listener.parse_message_id(": message")
        self.assertIsNone(result)

    def test_parse_invalid_spaces_in_session(self):
        """Reject session name with spaces"""
        result = telegram_listener.parse_message_id("session name: message")
        self.assertIsNone(result)


class TestNewRoutingLogic(unittest.TestCase):
    """Test NEW session-based routing (no pre-registration required)"""

    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.send_telegram_message')
    @patch('telegram_listener.time.sleep')
    def test_route_to_existing_session(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Route message to existing tmux session"""
        # Mock tmux list-sessions output
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="claude-session\ntest-session\ntelemux\n"
        )

        # This test verifies the NEW process_update() implementation
        update = {
            "message": {
                "text": "claude-session: test message",
                "from": {"first_name": "Marco"}
            }
        }

        # Call process_update with new routing logic
        telegram_listener.process_update(update)

        # Verify tmux send-keys was called
        calls = [str(call) for call in mock_subprocess.call_args_list]

        # Should call tmux send-keys with the message
        self.assertTrue(any('send-keys' in str(call) for call in calls))

        # Should send confirmation to Telegram
        mock_send_tg.assert_called()
        confirmation = str(mock_send_tg.call_args)
        self.assertIn("delivered", confirmation.lower())

    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.send_telegram_message')
    def test_route_to_nonexistent_session(self, mock_send_tg, mock_subprocess):
        """Show active sessions when target doesn't exist"""
        # Mock tmux list-sessions output (target session not in list)
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="claude-session\ntest-session\ntelemux\n"
        )

        update = {
            "message": {
                "text": "nonexistent-session: test message",
                "from": {"first_name": "Marco"}
            }
        }

        telegram_listener.process_update(update)

        # Should send error message with active sessions
        mock_send_tg.assert_called()
        error_msg = str(mock_send_tg.call_args)
        self.assertIn("not found", error_msg.lower())
        self.assertIn("claude-session", error_msg)
        self.assertIn("test-session", error_msg)

    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.send_telegram_message')
    def test_route_when_no_tmux_sessions(self, mock_send_tg, mock_subprocess):
        """Handle case when no tmux sessions are running"""
        # Mock tmux list-sessions failure (no sessions)
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stdout=""
        )

        update = {
            "message": {
                "text": "any-session: test message",
                "from": {"first_name": "Marco"}
            }
        }

        telegram_listener.process_update(update)

        # Should send error about no sessions
        mock_send_tg.assert_called()
        error_msg = str(mock_send_tg.call_args)
        self.assertIn("no tmux sessions", error_msg.lower())

    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.send_telegram_message')
    @patch('telegram_listener.time.sleep')
    def test_message_delivery_includes_sleep(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Verify 1-second sleep before Enter (critical for tmux buffering)"""
        # Mock tmux list-sessions
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="test-session\n"
        )

        update = {
            "message": {
                "text": "test-session: hello",
                "from": {"first_name": "Marco"}
            }
        }

        telegram_listener.process_update(update)

        # Should call sleep(1) before sending Enter
        mock_sleep.assert_called_with(1)

    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.send_telegram_message')
    @patch('telegram_listener.time.sleep')
    def test_message_format_in_tmux(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Verify message format sent to tmux"""
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="test-session\n"
        )

        update = {
            "message": {
                "text": "test-session: deploy now",
                "from": {"first_name": "Marco"}
            }
        }

        telegram_listener.process_update(update)

        # Find the send-keys call
        calls = mock_subprocess.call_args_list
        send_keys_call = None
        for call in calls:
            if 'send-keys' in str(call):
                send_keys_call = call
                break

        self.assertIsNotNone(send_keys_call, "Should call tmux send-keys")

        # Verify message format
        call_str = str(send_keys_call)
        self.assertIn("[FROM USER via Telegram]", call_str)
        self.assertIn("deploy now", call_str)


class TestBackwardCompatibility(unittest.TestCase):
    """Ensure tg_agent still works after changes"""

    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.send_telegram_message')
    @patch('telegram_listener.time.sleep')
    def test_tg_agent_messages_still_route(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Messages from tg_agent should still work"""
        # tg_agent registers in outgoing.log, but new routing bypasses that
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="agent-session\n"
        )

        update = {
            "message": {
                "text": "agent-session: confirmed",
                "from": {"first_name": "Marco"}
            }
        }

        telegram_listener.process_update(update)

        # Should deliver via new routing logic (direct to tmux)
        calls = [str(call) for call in mock_subprocess.call_args_list]
        self.assertTrue(any('send-keys' in str(call) for call in calls))
        mock_send_tg.assert_called()


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.send_telegram_message')
    def test_empty_message_text(self, mock_send_tg, mock_subprocess):
        """Handle empty message text"""
        update = {
            "message": {
                "text": "",
                "from": {"first_name": "Marco"}
            }
        }

        # Should not crash, should log and ignore
        try:
            telegram_listener.process_update(update)
        except Exception as e:
            self.fail(f"Should handle empty message gracefully: {e}")

    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.send_telegram_message')
    def test_missing_text_field(self, mock_send_tg, mock_subprocess):
        """Handle message without text field"""
        update = {
            "message": {
                "from": {"first_name": "Marco"}
            }
        }

        # Should not crash
        try:
            telegram_listener.process_update(update)
        except Exception as e:
            self.fail(f"Should handle missing text field: {e}")

    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.send_telegram_message')
    def test_tmux_command_failure(self, mock_send_tg, mock_subprocess):
        """Handle tmux command failures gracefully"""
        # Mock tmux send-keys failure
        mock_subprocess.side_effect = Exception("tmux error")

        update = {
            "message": {
                "text": "test-session: message",
                "from": {"first_name": "Marco"}
            }
        }

        # Should catch exception and send error to Telegram
        telegram_listener.process_update(update)

        # Should send error notification
        mock_send_tg.assert_called()
        error_msg = str(mock_send_tg.call_args)
        self.assertIn("error", error_msg.lower())


class TestMessageIdFormat(unittest.TestCase):
    """Test that we handle session names correctly"""

    def test_session_name_alphanumeric(self):
        """Accept session names with letters and numbers"""
        result = telegram_listener.parse_message_id("agent123: message")
        self.assertEqual(result, ("agent123", "message"))

    def test_session_name_with_dash(self):
        """Accept session names with dashes"""
        result = telegram_listener.parse_message_id("my-agent-1: message")
        self.assertEqual(result, ("my-agent-1", "message"))

    def test_session_name_with_underscore(self):
        """Accept session names with underscores"""
        result = telegram_listener.parse_message_id("my_agent: message")
        self.assertEqual(result, ("my_agent", "message"))

    def test_reject_special_characters(self):
        """Reject session names with special characters"""
        result = telegram_listener.parse_message_id("my@agent: message")
        self.assertIsNone(result)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
