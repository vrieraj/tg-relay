# tg-relay MCP Server — Reference

The Telegram relay is now integrated via **MCP (Model Context Protocol)**. opencode does NOT need to follow prompt-based instructions — it calls deterministic tools.

## Architecture

```
Telegram API ◄──► tg-bot (daemon) ◄──► inbox/outbox/ ◄──► MCP Server ◄──► opencode
```

- `tg-bot` — talks to Telegram API, manages inbox/outbox
- `MCP Server` — `mcp_server.py`, exposes 8 tools via stdio
- `opencode` — calls MCP tools, never touches files directly

## Tools

| Tool | What it does |
|------|-------------|
| `telegram_activate(session?)` | Starts tg-bot daemon. Auto-creates inbox/outbox/files dirs. |
| `telegram_deactivate()` | Stops tg-bot, cleans up PID file. |
| `telegram_wait_message(timeout=300)` | Blocks via inotify (kernel-level, 0% CPU) until message arrives. Drains all pending messages from inbox. Returns text or "TIMEOUT". |
| `telegram_reply(text, tts=false)` | Writes reply to outbox. tg-bot's responder thread picks it up within 3 seconds. |
| `telegram_ask(question, timeout=300)` | Sends question to Telegram, waits for yes/no via inotify. Returns "YES", "NO", or "TIMEOUT". |
| `telegram_list_files()` | Lists files in current session with sizes. |
| `telegram_read_file(filename)` | Returns absolute path to a received file. opencode reads it directly. |
| `telegram_session_status()` | Shows session name, bot state (running/stopped), pending messages, queued replies, file count. |

## Lifecycle

1. User tells opencode: "Activate Telegram on session X"
2. opencode calls `telegram_activate("X")` → tg-bot starts
3. opencode calls `telegram_wait_message()` in a loop → blocks via inotify
4. Message arrives → tool returns text → opencode processes
5. opencode calls `telegram_reply(text)` → reply appears in Telegram
6. If confirmation needed: `telegram_ask("¿Ejecuto migración?")`

## Internals

- Session state: `/tmp/tg-current-session`
- Bot PID: `/tmp/tg-bot.pid`
- Sessions dir: `~/Proyectos/tg-relay/sessions/<name>/`
- Bot auto-starts/cleanup on MCP server start/stop
- Health check: if tg-bot crashes on start (< 0.5s), error returned
- Inotify required: checks at startup, tools return error if missing

## Configuration

In `~/.config/opencode/opencode.jsonc`:

```jsonc
"telegram": {
  "type": "local",
  "command": ["/path/to/tg-relay/.venv/bin/python3", "/path/to/tg-relay/mcp_server.py"],
  "enabled": true,
  "environment": {
    "TG_RELAY_SESSIONS": "/home/vencejo/Proyectos/tg-relay/sessions",
    "TG_TOKEN": "${env:TG_TOKEN}",
    "TG_CHAT_ID": "${env:TG_CHAT_ID}",
    "GROQ_API_KEY": "${env:GROQ_API_KEY}"
  }
}
```

Required env vars in `~/.config/opencode/.env`:
- `TG_TOKEN` — Telegram bot token from @BotFather
- `TG_CHAT_ID` — your Telegram chat ID
- `GROQ_API_KEY` — (optional) for voice transcription