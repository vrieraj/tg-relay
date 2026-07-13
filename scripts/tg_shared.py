#!/usr/bin/env python3
"""Shared utilities for tg-relay scripts. Must be in the same directory as scripts."""

import os
import subprocess
import tempfile
import time


def load_env(env_file=None):
    """Parse .env file, return dict. Environment variables take precedence."""
    path = env_file or os.environ.get(
        "TG_RELAY_ENV_FILE",
        os.path.expanduser("~/.config/opencode/.env"),
    )
    cfg = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k] = v
    return cfg


def get_token():
    return os.environ.get("TG_TOKEN") or load_env().get("TG_TOKEN") or ""


def get_chat_id():
    return os.environ.get("TG_CHAT_ID") or load_env().get("TG_CHAT_ID") or ""


def get_groq_key():
    return os.environ.get("GROQ_API_KEY") or load_env().get("GROQ_API_KEY") or ""


def get_base_dir():
    return os.path.expanduser(
        os.environ.get("TG_RELAY_SESSIONS", "~/Proyectos/tg-relay/sessions")
    )


def get_current_session():
    current_file = "/tmp/tg-current-session"
    if os.path.exists(current_file):
        with open(current_file) as f:
            return f.read().strip()
    return os.environ.get("TG_CURRENT_SESSION") or ""


def drain_inbox(inbox_path):
    """Read and delete all .txt files from inbox, return list of contents."""
    messages = []
    if not os.path.isdir(inbox_path):
        return messages
    for fname in sorted(os.listdir(inbox_path)):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(inbox_path, fname)
        try:
            with open(fpath) as f:
                content = f.read().strip()
            os.remove(fpath)
            if content:
                messages.append(content)
        except FileNotFoundError:
            continue
    return messages


def wait_inotify(inbox_path, timeout):
    """Block via inotify until a file is created. Returns True if file created."""
    proc = subprocess.run(
        [
            "inotifywait",
            "-q",
            "-e",
            "create",
            "--format",
            "%f",
            "--timeout",
            str(timeout),
            inbox_path,
        ],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def has_inotify():
    import shutil
    return shutil.which("inotifywait") is not None