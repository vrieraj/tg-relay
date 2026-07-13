#!/usr/bin/env python3
"""MCP server for Telegram relay — deterministic tools for opencode.

Replaces the old prompt-based protocol with concrete, always-available tools.
Uses inotify for message detection — zero polling, zero CPU waste.
"""
import asyncio
import atexit
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid

from mcp.server.fastmcp import FastMCP

# ── Configuration ────────────────────────────────────────────────────────────

BASE = os.path.expanduser(
    os.environ.get("TG_RELAY_SESSIONS", "~/Proyectos/tg-relay/sessions")
)
CURRENT_FILE = "/tmp/tg-current-session"
TG_BOT_PATH = os.path.expanduser(
    os.environ.get("TG_BOT_PATH", "~/.local/bin/tg-bot")
)
VENV_PYTHON = os.path.expanduser(
    os.environ.get("TG_RELAY_VENV_PYTHON", "~/Proyectos/tg-relay/.venv/bin/python3")
)
PID_FILE = "/tmp/tg-bot.pid"

mcp = FastMCP("tg-relay")

bot_process: subprocess.Popen | None = None

_INOTIFY_AVAILABLE = shutil.which("inotifywait") is not None


# ── Bot lifecycle ────────────────────────────────────────────────────────────

def _bot_running() -> bool:
    """Check if tg-bot is currently running (by PID file)."""
    if bot_process is not None and bot_process.poll() is None:
        return True
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            try:
                os.remove(PID_FILE)
            except FileNotFoundError:
                pass
    return False


def _stop_bot() -> None:
    """Stop the tg-bot daemon and its process group."""
    global bot_process

    if bot_process is not None and bot_process.poll() is None:
        try:
            os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
        except (OSError, ProcessLookupError, ValueError):
            pass
        try:
            bot_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(bot_process.pid), signal.SIGKILL)
            except (OSError, ProcessLookupError, ValueError):
                pass
        bot_process = None

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
        except (OSError, ValueError, FileNotFoundError):
            pass
        try:
            os.remove(PID_FILE)
        except FileNotFoundError:
            pass


def _start_bot(session: str) -> None:
    """Start the tg-bot daemon for the given session."""
    global bot_process

    _stop_bot()

    env = os.environ.copy()
    env["TG_CURRENT_SESSION"] = session
    env["TG_RELAY_SESSIONS"] = BASE

    session_dir = os.path.join(BASE, session)
    for sub in ("inbox", "outbox", "files"):
        os.makedirs(os.path.join(session_dir, sub), exist_ok=True)

    bot_process = subprocess.Popen(
        [VENV_PYTHON, "-u", TG_BOT_PATH],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    with open(PID_FILE, "w") as f:
        f.write(str(bot_process.pid))
    with open(CURRENT_FILE, "w") as f:
        f.write(session)

    time.sleep(0.5)

    if bot_process.poll() is not None:
        _, stderr = bot_process.communicate()
        _stop_bot()
        err_msg = stderr.decode().strip() if stderr else f"exit code {bot_process.returncode}"
        raise RuntimeError(
            f"tg-bot failed to start: {err_msg}. "
            "Check TG_TOKEN and TG_CHAT_ID in ~/.config/opencode/.env"
        )


def _read_current_session() -> str | None:
    if os.path.exists(CURRENT_FILE):
        with open(CURRENT_FILE) as f:
            return f.read().strip()
    return None


# ── Cleanup ──────────────────────────────────────────────────────────────────

def _require_inotify() -> str | None:
    """Check that inotifywait is available. Returns error message or None."""
    if not _INOTIFY_AVAILABLE:
        return "ERROR: inotifywait not found. Install inotify-tools package."
    return None

def _cleanup() -> None:
    _stop_bot()


atexit.register(_cleanup)
signal.signal(signal.SIGTERM, lambda *_: (_cleanup(), sys.exit(0)))
signal.signal(signal.SIGINT, lambda *_: (_cleanup(), sys.exit(0)))


# ── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def telegram_activate(session: str | None = None) -> str:
    """Start the Telegram relay bot for a session. Creates inbox/outbox/files
    directories if needed. If no session given, uses the last active one.

    Args:
        session: Session name. If omitted, uses the current or last active session.
    """
    if session is None:
        session = _read_current_session()

    if session is None:
        if os.path.isdir(BASE):
            sessions = sorted(
                d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))
            )
            if sessions:
                return (
                    f"No session specified. Available sessions: {', '.join(sessions)}"
                )
        return "No sessions found. Create one in terminal: tg-session create <name>"

    session_dir = os.path.join(BASE, session)
    if not os.path.isdir(session_dir):
        if os.path.isdir(BASE):
            sessions = sorted(
                d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))
            )
            avail = f"\nAvailable: {', '.join(sessions)}" if sessions else ""
        else:
            avail = ""
        return f"Session '{session}' does not exist.{avail}"

    if _bot_running():
        old = _read_current_session()
        if old != session:
            try:
                _start_bot(session)
            except RuntimeError as e:
                return f"ERROR: {e}"
            return f"Switched to session '{session}' (bot restarted)"
        return f"Already active on session '{session}'"

    try:
        _start_bot(session)
    except RuntimeError as e:
        return f"ERROR: {e}"
    return f"Telegram relay activated — session '{session}'"


@mcp.tool()
async def telegram_deactivate() -> str:
    """Stop the Telegram relay bot. No messages will be received or sent."""
    _stop_bot()
    try:
        os.remove(CURRENT_FILE)
    except FileNotFoundError:
        pass
    return "Telegram relay deactivated"


@mcp.tool()
async def telegram_wait_message(timeout: int = 300) -> str:
    """Wait for a new Telegram message using inotify (kernel-level filesystem watch).
    Blocks efficiently until a message arrives or the timeout expires.

    Args:
        timeout: Maximum seconds to wait. Default 300 (5 minutes).

    Returns the message text, or 'TIMEOUT' if nothing arrived.
    """
    session = _read_current_session()
    if not session:
        return "ERROR: No active session. Use telegram_activate first."

    if not _bot_running():
        return "ERROR: Bot is not running. Use telegram_activate first."

    if error := _require_inotify():
        return error

    inbox = os.path.join(BASE, session, "inbox")
    os.makedirs(inbox, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "inotifywait",
        "-q",
        "-e",
        "create",
        "--format",
        "%f",
        "--timeout",
        str(timeout),
        inbox,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()

    # Read and drain all pending messages
    messages: list[str] = []
    try:
        for fname in sorted(os.listdir(inbox)):
            if not fname.endswith(".txt"):
                continue
            fpath = os.path.join(inbox, fname)
            try:
                with open(fpath) as f:
                    content = f.read().strip()
                os.remove(fpath)
                if content:
                    messages.append(content)
            except FileNotFoundError:
                continue
    except FileNotFoundError:
        pass

    if not messages:
        return "TIMEOUT: No message received"

    if len(messages) == 1:
        return messages[0]

    return "\n---\n".join(messages)


@mcp.tool()
async def telegram_reply(text: str, tts: bool = False) -> str:
    """Send a reply to Telegram. The running bot daemon picks it up and delivers it.

    Args:
        text: The message text to send.
        tts: If True, the reply will be sent as a voice message (Kokoro TTS).
    """
    session = _read_current_session()
    if not session:
        return "ERROR: No active session. Use telegram_activate first."

    if not _bot_running():
        return "ERROR: Bot is not running. Use telegram_activate first."

    if tts:
        text = f"!tts {text}"

    mid = str(uuid.uuid4())[:8]
    out_dir = os.path.join(BASE, session, "outbox")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{mid}.txt")

    with open(out_file, "w") as f:
        f.write(text)

    return "Reply queued for delivery"


@mcp.tool()
async def telegram_ask(question: str, timeout: int = 300) -> str:
    """Ask a yes/no question via Telegram and wait for the answer using inotify.

    Args:
        question: The yes/no question to send.
        timeout: Maximum seconds to wait for an answer. Default 300 (5 min).

    Returns:
        'YES' if the user replied 'si' (yes).
        'NO' if the user replied 'no'.
        'TIMEOUT' if no answer was received within the timeout.
    """
    session = _read_current_session()
    if not session:
        return "ERROR: No active session. Use telegram_activate first."

    if not _bot_running():
        return "ERROR: Bot is not running. Use telegram_activate first."

    if error := _require_inotify():
        return error

    # Write question to outbox so tg-bot sends it to Telegram
    out_id = str(uuid.uuid4())[:8]
    out_dir = os.path.join(BASE, session, "outbox")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{out_id}.txt")
    with open(out_file, "w") as f:
        f.write(
            f"❓ {question}\n\n"
            f"Responde 'si' para confirmar o 'no' para cancelar."
        )

    inbox = os.path.join(BASE, session, "inbox")
    os.makedirs(inbox, exist_ok=True)

    deadline = time.time() + timeout

    while time.time() < deadline:
        remaining = max(1, int(deadline - time.time()))

        proc = await asyncio.create_subprocess_exec(
            "inotifywait",
            "-q",
            "-e",
            "create",
            "--format",
            "%f",
            "--timeout",
            str(remaining),
            inbox,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        answer = ""
        try:
            for fname in sorted(os.listdir(inbox)):
                if not fname.endswith(".txt"):
                    continue
                fpath = os.path.join(inbox, fname)
                try:
                    with open(fpath) as f:
                        content = f.read().strip()
                    os.remove(fpath)
                    answer = content.lower()
                except FileNotFoundError:
                    continue
        except FileNotFoundError:
            continue

        if "si" in answer:
            with open(out_file, "w") as f:
                f.write("✅ Autorizado.")
            return "YES: User confirmed"
        elif "no" in answer:
            with open(out_file, "w") as f:
                f.write("❌ Denegado.")
            return "NO: User denied"

    with open(out_file, "w") as f:
        f.write("⏱️ Tiempo de espera agotado.")
    return "TIMEOUT: No response received"


@mcp.tool()
async def telegram_list_files() -> str:
    """List files received in the current Telegram session."""
    session = _read_current_session()
    if not session:
        return "ERROR: No active session. Use telegram_activate first."

    files_dir = os.path.join(BASE, session, "files")
    if not os.path.isdir(files_dir):
        return "(no files directory)"

    entries = sorted(os.listdir(files_dir))
    if not entries:
        return "(no files)"

    lines = []
    for fname in entries:
        fpath = os.path.join(files_dir, fname)
        try:
            size = os.path.getsize(fpath)
            lines.append(f"{fname}  ({_fmt_size(size)})")
        except OSError:
            lines.append(f"{fname}  (unreadable)")

    return "\n".join(lines)


@mcp.tool()
async def telegram_read_file(filename: str) -> str:
    """Get the local filesystem path of a file received via Telegram.
    opencode can then read it directly.

    Args:
        filename: Exact filename (use telegram_list_files to see available files).

    Returns the absolute path to the file, or an error string.
    """
    session = _read_current_session()
    if not session:
        return "ERROR: No active session. Use telegram_activate first."

    filename = os.path.basename(filename)
    fpath = os.path.join(BASE, session, "files", filename)
    if not os.path.isfile(fpath):
        return f"ERROR: File '{filename}' not found in session '{session}'"

    return str(fpath)


@mcp.tool()
async def telegram_session_status() -> str:
    """Show current Telegram relay status: active session, bot state, message counts."""
    session = _read_current_session()
    running = _bot_running()

    if not session and not running:
        sessions = []
        if os.path.isdir(BASE):
            sessions = sorted(
                d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))
            )
        if sessions:
            return f"Status: inactive\nSessions available: {', '.join(sessions)}"
        return "Status: inactive (no sessions)"

    if not session:
        return "Status: bot running but no active session file"

    inbox_dir = os.path.join(BASE, session, "inbox")
    outbox_dir = os.path.join(BASE, session, "outbox")
    files_dir = os.path.join(BASE, session, "files")

    inbox_n = (
        len([f for f in os.listdir(inbox_dir) if f.endswith(".txt")])
        if os.path.isdir(inbox_dir)
        else 0
    )
    outbox_n = (
        len([f for f in os.listdir(outbox_dir) if f.endswith(".txt")])
        if os.path.isdir(outbox_dir)
        else 0
    )
    files_n = len(os.listdir(files_dir)) if os.path.isdir(files_dir) else 0

    bot_line = "running" if running else "stopped"
    return (
        f"Session: {session}\n"
        f"Bot: {bot_line}\n"
        f"Pending messages: {inbox_n}\n"
        f"Queued replies: {outbox_n}\n"
        f"Files: {files_n}"
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size} {unit}"
        size //= 1024
    return f"{size} TB"


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()