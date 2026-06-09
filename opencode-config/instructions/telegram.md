# Telegram integration

## Sending notifications
Use `tg` for any notification:
- `tg "✅ Paso completado"`
- `tg "❌ Error: ..."`
- `tg "⏳ Progreso: 3/10"`

## Reading instructions
- `tg-read` — consulta única de mensajes nuevos
- `tg-wait` — bloquea hasta que llegue un mensaje (polla cada 60s)

## 📱 Modo remoto con servidor
Activa opencode serve + bot relay para control total desde el móvil.

**Bot relay (tg-bot):** recibe texto/voz por Telegram, transcribe con Groq Whisper, pasa el mensaje a opencode, y devuelve respuesta con Kokoro TTS opcional.

Las sesiones se guardan en `~/Proyectos/tg-relay/sessions/<nombre>/`:
- `inbox/` ← mensajes desde Telegram
- `outbox/` ← respuestas desde opencode
- `files/` ← archivos adjuntos

**Uso:**

1. **Crear sesión**: `tg-session create nombre-sesion`
2. **Arrancar**: `tg-serve start nombre-sesion`
3. **Notifica**: `tg "✅ Modo remoto activado. Sesión: nombre-sesion"`
4. **Bucle**: monitorear la sesión -> leer `inbox/`, procesar, escribir en `outbox/`
5. **Telegram**: "usar nombre-sesion" para cambiar de sesión, envía texto/audio normal

Cerrar:
- Telegram: "cuelgo el teléfono" o `tg-session close nombre-sesion`
- Al cerrar, pregunta qué hacer con los archivos (guardar/borrar)
- Limpia `tg-serve stop` si no hay más sesiones

## ⏭️ Cambiar a servidor estando en TUI

1. Crea sesión: `tg-session create mi-sesion`
2. Arranca: `tg-serve start mi-sesion`
3. Tu TUI + bot comparten el mismo servidor
4. Desde Telegram, cambias de sesión con "usar mi-sesion"

## 📋 Protocolo completo
Ver `opencode-config/AGENTS.md` para el protocolo detallado.
