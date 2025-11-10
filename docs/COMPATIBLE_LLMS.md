# Compatible LLM CLIs

TeleMux works with **any** LLM CLI that runs in tmux. Here are some tested examples:

## Confirmed Working

### Claude Code
```bash
claude  # Anthropic's Claude Code
cc      # Short alias
```

### GitHub Copilot CLI  
```bash
gh copilot  # GitHub Copilot in the CLI
codex       # Codex CLI
```

### Google Gemini CLI
```bash
gemini-cli  # Google's Gemini CLI
```

### OpenAI CLI
```bash
openai      # OpenAI's official CLI
```

### Custom LLM Wrappers
Any script or CLI that:
- Runs in a tmux session
- Can execute shell functions
- Accepts user input

## Usage Pattern

Same for all LLMs:

```bash
# In your LLM CLI session
tg_agent "my-session" "Question for the user?"

# User replies on Telegram:
# my-session: Here's my answer

# Reply appears in your LLM session:
# [FROM USER via Telegram] Here's my answer
```

## Adding Your Own

To integrate a new LLM CLI:

1. Ensure it runs in tmux
2. Source the shell functions:
   ```bash
   source ~/.zshrc  # or ~/.bashrc
   ```
3. Use the functions:
   ```bash
   tg_alert "message"
   tg_agent "name" "question"
   ```

That's it! TeleMux is LLM-agnostic.

## Examples by LLM

### Claude Code Session
```bash
tmux new-session -s claude-session
claude

# Inside Claude:
tg_agent "claude" "Should I deploy this code?"
```

### Codex Session
```bash
tmux new-session -s codex-session
codex

# Inside Codex:
tg_agent "codex" "Review this implementation?"
```

### Gemini CLI Session
```bash
tmux new-session -s gemini-session
gemini-cli

# Inside Gemini:
tg_agent "gemini" "Optimize this query?"
```

---

**Note:** The LLM CLI itself doesn't need to know about Telegram. TeleMux provides shell functions that work in any bash/zsh session.
