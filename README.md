# tg-relay — Telegram ↔ opencode Relay

Bidirectional relay between Telegram and [opencode](https://opencode.ai) AI coding agent. Control opencode from your phone via Telegram — send text, voice messages, and files.

## Features

- **📱 Remote control** — receive Telegram messages in opencode, send replies back
- **🎤 Voice transcription** — voice messages → text via Groq Whisper (`whisper-large-v3-turbo`)
- **🔊 Text-to-Speech** — replies as audio via local Kokoro (82M params, CPU, Spanish + 9 languages)
- **📎 File attachments** — documents and photos stored per session
- **🔄 Multi-session** — switch between sessions from Telegram (`usar nombre`)
- **🔔 Notifications** — send opencode notifications to Telegram via `tg` CLI
- **🔧 MCP server** — deterministic tools via MCP protocol, no prompt-based instructions

## Architecture

```
Telegram API ◄──────────► tg-bot (daemon)
                               │
                    inbox/ / outbox/
                               │
                         MCP Server ▲
                               │
                          opencode
```

- **tg-bot** — the ONLY component that talks to Telegram API. Writes incoming messages to `inbox/`, reads replies from `outbox/`.
- **MCP Server** — deterministic bridge. opencode calls MCP tools (never forgets them). Uses `inotify` for message detection — zero polling.
- **opencode** — calls `telegram_activate`, `telegram_wait_message`, `telegram_reply`, `telegram_ask`, etc.

### Why MCP instead of prompts?

The old version used 125 lines of natural language instructions in `AGENTS.md` for opencode to follow. opencode would forget steps, mismanage state, or miss messages.

The MCP server provides **concrete, always-available tools**. opencode doesn't need to remember HOW the relay works — it just calls tools that encapsulate all the logic.

## Quick Start

### Prerequisites

- Linux (tested on Arch/Manjaro)
- Python 3.11+
- [opencode](https://opencode.ai) installed
- `inotify-tools` (`sudo pacman -S inotify-tools` / `sudo apt install inotify-tools`)
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

Add the MCP server to `~/.config/opencode/opencode.jsonc`:

```jsonc
"mcp": {
  "telegram": {
    "type": "local",
    "command": ["/path/to/tg-relay/.venv/bin/python3", "/path/to/tg-relay/mcp_server.py"],
    "enabled": true,
    "environment": {
      "TG_RELAY_SESSIONS": "/path/to/tg-relay/sessions",
      "TG_TOKEN": "${env:TG_TOKEN}",
      "TG_CHAT_ID": "${env:TG_CHAT_ID}",
      "GROQ_API_KEY": "${env:GROQ_API_KEY}"
    }
  }
}
```

### Use

```bash
# Create a session
tg-session create my-session

# Restart opencode to load the MCP server
```

Then in opencode:

```
"Activate Telegram relay on session my-session"
→ opencode calls telegram_activate("my-session")
→ tg-bot starts, Telegram receives "🔁 Relay activado"

"Wait for Telegram messages"
→ opencode calls telegram_wait_message() in a loop
→ blocks via inotify (0% CPU)
→ when a message arrives, returns the text
→ opencode processes the task
→ opencode calls telegram_reply("Done!")
→ reply appears in Telegram
```

### From Telegram

- Send text: type normally
- Send voice: transcribed automatically
- Switch session: `usar nombre-sesion`
- Close: `cuelgo el teléfono`

## MCP Tools

| Tool | Description |
|------|-------------|
| `telegram_activate(session?)` | Start tg-bot daemon. If no session given, uses last active one. |
| `telegram_deactivate()` | Stop tg-bot. No messages will be received or sent. |
| `telegram_wait_message(timeout=300)` | Block via inotify until a message arrives. Returns text or TIMEOUT. |
| `telegram_reply(text, tts=false)` | Queue a reply. tg-bot picks it up and delivers it. |
| `telegram_ask(question, timeout=300)` | Ask yes/no question via Telegram, wait for answer. Returns YES/NO/TIMEOUT. |
| `telegram_list_files()` | List files received in the current session. |
| `telegram_read_file(filename)` | Get local filesystem path of a received file. |
| `telegram_session_status()` | Show session state: bot status, pending messages, files. |

### Tool lifecycle

```
telegram_activate("session")    ← starts tg-bot
       │
telegram_wait_message()          ← blocks via inotify, returns message
       │
telegram_reply("Done!")          ← queues reply
       │
telegram_ask("Confirm?")         ← yes/no, also via inotify
       │
telegram_deactivate()            ← stops tg-bot
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `tg <text>` | Send notification to Telegram |
| `tg-read [session]` | Read pending inbox messages |
| `tg-wait [session]` | Block until new message arrives (inotify, one-shot) |
| `tg-session create <name>` | Create a new session |
| `tg-session list` | List all sessions |
| `tg-session close <name>` | Close a session |

These CLI tools are still available for scripting but are not needed when using the MCP server — opencode calls the MCP tools directly.

## TTS (Text-to-Speech)

For audio replies via MCP:

```
telegram_reply("Hola, esto es un mensaje de voz", tts=true)
```

Uses Kokoro with Spanish voice `ef_dora` at 0.85x speed.

## Project Structure

```
tg-relay/
├── mcp_server.py          # MCP server — deterministic tools for opencode
├── scripts/               # CLI tools (tg, tg-bot, tg-read, etc.)
├── skill/SKILL.md         # opencode skill definition
├── opencode-config/       # Reference documentation (not loaded by opencode)
├── .env.example           # Environment variables template
├── requirements.txt       # Python dependencies
├── install.sh             # Automated install
└── README.md
```

## License

GNU General Public License v3.0 or later. See [LICENSE](LICENSE).