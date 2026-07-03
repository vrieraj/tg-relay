#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
VENV_DIR="${VENV_DIR:-$REPO_DIR/.venv}"
CONFIG_DIR="${CONFIG_DIR:-$HOME/.config/opencode}"
ENV_FILE="${ENV_FILE:-$CONFIG_DIR/.env}"

echo "==> tg-relay installer"
echo "    Install dir: $INSTALL_DIR"
echo "    Venv dir:    $VENV_DIR"
echo "    Config dir:  $CONFIG_DIR"

# 1. Create venv and install dependencies
if [ ! -d "$VENV_DIR" ]; then
    echo "==> Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi
echo "==> Installing Python dependencies..."
"$VENV_DIR/bin/pip" install -U pip
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt"

# 2. Install torch (CPU) for Kokoro
"$VENV_DIR/bin/pip" install torch --index-url https://download.pytorch.org/whl/cpu 2>/dev/null || echo "    (torch already installed or skipped)"

# 3. Copy scripts to INSTALL_DIR
echo "==> Installing scripts to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
for script in "$REPO_DIR"/scripts/*; do
    name="$(basename "$script")"
    cp "$script" "$INSTALL_DIR/$name"
    chmod +x "$INSTALL_DIR/$name"
    echo "    $INSTALL_DIR/$name"
done

# 4. Create .env from example if not exists
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$REPO_DIR/.env.example" ]; then
        echo "==> Creating $ENV_FILE from .env.example"
        echo "# Copy this from .env.example and fill in your tokens" > "$ENV_FILE"
        cat "$REPO_DIR/.env.example" >> "$ENV_FILE"
        echo ""
        echo "⚠️  Edit $ENV_FILE and add your Telegram token and Chat ID"
    fi
else
    echo "==> $ENV_FILE already exists, skipping"
fi
chmod 600 "$ENV_FILE" 2>/dev/null || true

# 5. Check system dependencies
if ! command -v inotifywait &>/dev/null; then
    echo ""
    echo "⚠️  inotify-tools not found. Install it:"
    echo "   Arch:  sudo pacman -S inotify-tools"
    echo "   Debian: sudo apt install inotify-tools"
fi

if ! command -v espeak-ng &>/dev/null; then
    echo ""
    echo "⚠️  espeak-ng not found. Install it:"
    echo "   Arch:  sudo pacman -S espeak-ng"
    echo "   Debian: sudo apt install espeak-ng"
fi

# 6. Copy opencode skill and config
echo "==> Copying opencode skill..."
mkdir -p "$CONFIG_DIR/skills/tg-relay"
cp -f "$REPO_DIR/skill/SKILL.md" "$CONFIG_DIR/skills/tg-relay/SKILL.md" 2>/dev/null || true

echo ""
echo "✅ tg-relay installed!"
echo ""
echo "Next steps:"
echo "  1. Install inotify-tools: sudo pacman -S inotify-tools"
echo "  2. Edit $ENV_FILE with your tokens"
echo "  3. Add MCP config to $CONFIG_DIR/opencode.jsonc (see README.md)"
echo "  4. Create a session: tg-session create my-session"
echo "  5. Restart opencode → MCP server loads automatically"
echo "  6. In opencode: 'Activate Telegram relay on session my-session'"
