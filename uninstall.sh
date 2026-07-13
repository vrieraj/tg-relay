#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
VENV_DIR="${VENV_DIR:-$REPO_DIR/.venv}"
CONFIG_DIR="${CONFIG_DIR:-$HOME/.config/opencode}"
ENV_FILE="${ENV_FILE:-$CONFIG_DIR/.env}"

echo "==> tg-relay uninstaller"
echo ""

# Stop services
echo "==> Parando servicios..."
tg-serve stop 2>/dev/null || true

# Remove scripts
echo "==> Eliminando scripts de $INSTALL_DIR..."
for script in tg tg-ask tg-bot tg-monitor tg-read tg-serve tg-session tg-wait; do
    if [ -f "$INSTALL_DIR/$script" ]; then
        rm -f "$INSTALL_DIR/$script"
        echo "    $INSTALL_DIR/$script"
    fi
done

# Remove venv
if [ -d "$VENV_DIR" ]; then
    echo ""
    echo "==> ¿Eliminar entorno virtual? ($VENV_DIR)"
    echo -n "    (s/n): "
    read -r ans
    if [[ "$ans" =~ ^[sS] ]]; then
        rm -rf "$VENV_DIR"
        echo "    Eliminado"
    fi
fi

# Remove sessions
if [ -d "$REPO_DIR/sessions" ]; then
    echo ""
    echo "==> ¿Eliminar sesiones y archivos? ($REPO_DIR/sessions)"
    echo -n "    (s/n): "
    read -r ans
    if [[ "$ans" =~ ^[sS] ]]; then
        ls "$REPO_DIR/sessions/"
        rm -rf "$REPO_DIR/sessions"
        echo "    Eliminado"
    fi
fi

# Remove opencode config files
echo ""
echo "==> ¿Eliminar config de opencode? (AGENTS.md, SKILL.md, instrucciones)"
echo -n "    (s/n): "
read -r ans
if [[ "$ans" =~ ^[sS] ]]; then
    rm -f "$CONFIG_DIR/AGENTS.md"
    rm -f "$CONFIG_DIR/skills/tg-relay/SKILL.md"
    rmdir "$CONFIG_DIR/skills/tg-relay" 2>/dev/null || true
    echo "    Eliminado"
fi

# .env
if [ -f "$ENV_FILE" ]; then
    echo ""
    echo "==> ¿Eliminar .env con tokens? ($ENV_FILE)"
    echo -n "    (s/n): "
    read -r ans
    if [[ "$ans" =~ ^[sS] ]]; then
        rm -f "$ENV_FILE"
        echo "    Eliminado"
    fi
fi

# Temp files
echo ""
echo "==> Limpiando archivos temporales..."
rm -f /tmp/tg-last-update /tmp/tg-current-session /tmp/tg-new-msg /tmp/tg-serve.pid /tmp/tg-bot.pid /tmp/tg-monitor.pid

echo ""
echo "✅ tg-relay desinstalado"
