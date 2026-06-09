---
name: tg-relay
description: Telegram <-> opencode relay daemon with voice transcription (Groq Whisper), TTS (Kokoro), file attachments, and multi-session management
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  audience: opencode users
  workflow: telegram
---

## What it does

- **Remote control**: receive Telegram messages in opencode's inbox and send replies
- **Voice transcription**: voice messages transcribed via Groq Whisper (`whisper-large-v3-turbo`)
- **TTS**: replies can be sent as audio via local Kokoro TTS (Spanish + 9 languages)
- **File attachments**: documents and photos stored per session
- **Multi-session**: switch between sessions from Telegram (`usar nombre`)
- **Notifications**: send opencode notifications to Telegram via `tg` CLI

## Architecture

```
Telegram API <--> tg-bot (daemon) <--> inbox/outbox <--> opencode
```

- `tg-bot` is the **only** component that talks to Telegram API
- opencode reads `inbox/` via `tg-read` and writes responses to `outbox/`
- Session directories at `~/Proyectos/tg-relay/sessions/<nombre>/`

## Commands

| Command | Function |
|---------|----------|
| `tg <texto>` | Send notification to Telegram |
| `tg-read [sesion]` | Read pending inbox messages |
| `tg-wait [sesion]` | Block until a new message arrives |
| `tg-session {create\|list\|close}` | Manage sessions |
| `tg-serve {start\|stop} <nombre>` | Start/stop session server |

## Workflow

1. **Start session**: `tg-session create mysession && tg-serve start mysession`
2. **Notify**: `tg "✅ Modo remoto activado"`
3. **Process**: `tg-wait mysession` -> `tg-read mysession` -> process -> write to `outbox/`
4. **Close**: "cuelgo el telefono" from Telegram, or `tg-session close mysession`
