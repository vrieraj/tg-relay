---
name: tg-relay
description: Telegram ↔ opencode relay via MCP. Deterministic tools: activate, wait for messages (inotify), reply, ask yes/no, file management.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  audience: opencode users
  workflow: telegram
---

## What it does

- **Remote control**: receive Telegram messages and send replies via MCP tools
- **Voice transcription**: voice messages transcribed via Groq Whisper (`whisper-large-v3-turbo`)
- **TTS**: replies as audio via local Kokoro TTS (Spanish + 9 languages)
- **File attachments**: documents and photos stored per session
- **Multi-session**: switch between sessions from Telegram (`usar nombre`)
- **Notifications**: send opencode notifications to Telegram via `tg` CLI

## Architecture

```
Telegram ◄──► tg-bot (daemon) ◄──► inbox/outbox/ ◄──► MCP Server ◄──► opencode
```

## MCP Tools (deterministic — no prompts needed)

| Tool | What it does |
|------|-------------|
| `telegram_activate(session?)` | Start the relay bot daemon |
| `telegram_deactivate()` | Stop the relay bot |
| `telegram_wait_message(timeout=300)` | Block via inotify until message arrives |
| `telegram_reply(text, tts=false)` | Queue a reply for delivery |
| `telegram_ask(question, timeout=300)` | Ask yes/no, wait for answer via inotify |
| `telegram_list_files()` | List session files with sizes |
| `telegram_read_file(filename)` | Get local path of a received file |
| `telegram_session_status()` | Session state and message counts |

## Setup

```bash
# Install
git clone https://github.com/vrieraj/tg-relay.git && cd tg-relay && bash install.sh

# Create session
tg-session create my-session

# Add to ~/.config/opencode/opencode.jsonc (see AGENTS.md for full config)
```

## Usage flow

```
telegram_activate("my-session")
  → tg-bot starts
  → loop:
      telegram_wait_message()
        → inotify blocks (0% CPU)
        → message arrives, returns text
      ... process task ...
      telegram_ask("Confirm?")   ← if permission needed
      telegram_reply("Done!", tts=true)
telegram_deactivate()
```

## Dependencies

- `inotify-tools` (system package)
- `mcp` (Python, pip)
- `kokoro`, `soundfile`, `numpy` (Python, for TTS)
- `requests` (Python, for API calls)