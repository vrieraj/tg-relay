# tg-relay — Telegram ↔ opencode Relay

Bidirectional relay between Telegram and [opencode](https://opencode.ai) AI coding agent. Control opencode from your phone via Telegram — send text, voice messages, and files.

## Features

- **📱 Remote control** — receive Telegram messages in opencode's inbox, send replies back
- **🎤 Voice transcription** — voice messages → text via Groq Whisper (`whisper-large-v3-turbo`)
- **🔊 Text-to-Speech** — replies as audio via local Kokoro (82M params, CPU, Spanish + 9 languages)
- **📎 File attachments** — documents and photos stored per session
- **🔄 Multi-session** — switch between sessions from Telegram (`usar nombre`)
- **🔔 Notifications** — send opencode notifications to Telegram via `tg` CLI

## Architecture

```
Telegram API ◄──────────► tg-bot (daemon)
                               │
                    escribe/lee en
                               ▼
             sessions/<nombre>/
                ├── inbox/       ← mensajes desde Telegram
                ├── outbox/      ← respuestas desde opencode
                ├── files/       ← archivos adjuntos
                ├── .new         ← señal de mensaje nuevo
                └── !estado.txt  ← estado de opencode
                       │
                  tg-read / tg-wait
                       │
                       ▼
                 opencode (TUI)
```

Only `tg-bot` talks to Telegram API. opencode reads/writes via simple file-based IPC.

## Quick Start

### Prerequisites

- Linux (tested on Arch/Manjaro)
- Python 3.11+
- [opencode](https://opencode.ai) installed
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Your Telegram Chat ID

### Install

```bash
git clone https://github.com/vrieraj/tg-relay.git
cd tg-relay
bash install.sh
```

### Configure

Edit `~/.config/opencode/.env`:

```env
TG_TOKEN=your_bot_token_from_botfather
TG_CHAT_ID=your_chat_id
GROQ_API_KEY=your_groq_api_key    # for voice transcription
```

### Use

```bash
# Create session
tg-session create mysession

# Start server
tg-serve start mysession

# Notify
tg "✅ Modo remoto activado. Sesión: mysession"

# In opencode, wait for messages
tg-wait mysession
# ...process...
tg-read mysession
```

### From Telegram

- Send text: type normally
- Send voice: transcribed automatically
- Switch session: `usar nombre-sesion`
- Close: `cuelgo el teléfono`

## Commands

| Command | Description |
|---------|-------------|
| `tg <text>` | Send notification to Telegram |
| `tg-read [session]` | Read pending inbox messages |
| `tg-wait [session]` | Block until new message arrives (inotify) |
| `tg-session create <name>` | Create a new session |
| `tg-session list` | List all sessions |
| `tg-session close <name>` | Close a session |
| `tg-serve start <name>` | Start session server (opencode + bot + monitor) |
| `tg-serve stop` | Stop all services |

## TTS (Text-to-Speech)

For audio replies, start the outbox message with `!tts `:

```bash
echo "!tts Hola, esto es un mensaje de voz" > outbox/uuid.txt
```

Uses Kokoro with Spanish voice `ef_dora` at 0.85x speed.

## opencode Skill

This repo includes an opencode skill. Place in `~/.config/opencode/skills/tg-relay/SKILL.md` or reference via `skills.urls` in opencode.json.

## Project Structure

```
tg-relay/
├── scripts/              # CLI tools (tg, tg-bot, tg-read, etc.)
├── skill/SKILL.md        # opencode skill definition
├── opencode-config/      # AGENTS.md protocol + instructions
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
├── install.sh            # Automated install
└── README.md
```

## License

MIT
