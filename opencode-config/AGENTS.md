# Protocolo Telegram ↔ opencode

## Arquitectura

```
Telegram API ◄──────────► tg-bot (daemon)
                               │
                    escribe/lee en
                               ▼
    ~/Proyectos/tg-relay/sessions/<nombre>/
        ├── inbox/       ← mensajes desde Telegram
        ├── outbox/      ← respuestas desde opencode
        ├── files/       ← archivos adjuntos
        ├── .new         ← señal de mensaje nuevo (contiene msg id)
        └── !estado.txt  ← estado de opencode (idle | ocupado: tarea)
              ┌────┴────┐
              │         │
         tg-monitor   tg-read / tg-wait
      (inotify daemon) (inotify one-shot)
              │         │
              ▼         ▼
         /tmp/tg-new-msg  opencode (TUI)
```

## Responsabilidades

### tg-bot (daemon)
- **Único** que habla con Telegram API
- **Inbound**: recibe texto/voz/archivos, escribe en `inbox/`, verifica estado
- **Outbound**: monitoriza `outbox/` y envía respuestas a Telegram (con TTS si procede)
- **Transcripción**: voz → texto vía Groq Whisper
- **TTS**: respuestas a audio vía Kokoro (local)

### opencode (TUI)
- Nunca llama a Telegram API directamente
- Lee `inbox/` con `tg-read`
- Escribe respuestas en `outbox/`
- Gestiona estado (`!estado.txt`)
- Detecta vuelta a terminal y pregunta si cerrar sesión

### tg-monitor (daemon opcional)
- **Inotify persistente**: monitoriza `inbox/` con `inotifywait -m`
- **Notificación**: escribe la sesión en `/tmp/tg-new-msg` cuando llega un mensaje
- **Alternativa ligera**: permite a opencode vigilar un solo archivo en vez de llamar a `tg-wait`

## Flujo de mensaje entrante (Telegram → opencode)

1. Usuario envía texto/voz/archivo a bot de Telegram
2. `tg-bot` recibe el update:
   - Si es **voz**: descarga, transcribe con Groq, escribe transcripción en `inbox/`
   - Si es **texto**: escribe directamente en `inbox/<uuid>.txt`
   - Si es **archivo** (document, photo): descarga a `files/`, escribe nota en `inbox/`
3. `tg-bot` lee `!estado.txt`:
   - **idle** (o no existe): escribe `.new` con el msg id → señal para opencode
   - **ocupado: X**: responde a Telegram "⏳ Estoy ocupado: X. Tu mensaje queda en cola."
4. **Detección**: opencode bloquea con `tg-wait` (inotify) hasta que aparece un archivo en `inbox/`
   - Alternativa: opencode vigila `/tmp/tg-new-msg` (escrito por tg-monitor)
5. opencode ejecuta `tg-read` para leer y procesar mensajes pendientes
6. **Bucle**: al terminar, opencode vuelve al paso 4

## Flujo de mensaje saliente (opencode → Telegram)

1. opencode procesa mensaje y decide respuesta
2. opencode escribe respuesta en `outbox/<uuid>.txt`
3. `tg-bot` (responder thread, cada 3s) detecta el archivo, lo lee y lo borra
4. `tg-bot` envía el texto a Telegram (con TTS si el texto empieza por `!tts `)

## Gestión de estado

- opencode **siempre** actualiza `!estado.txt` automáticamente:
  - Al iniciar tarea → `echo "ocupado: descripción breve" > !estado.txt`
  - Al terminar tarea → `rm -f !estado.txt` (pasa a idle)
- **No se cambia estado desde Telegram** — opencode lo gestiona solo
- `tg-bot` solo notifica `.new` si está idle
- opencode al volver a idle debe revisar `inbox/` SIEMPRE
- **Nunca uses sleep/polling** para esperar mensajes — usa `tg-wait` (inotify) o `/tmp/tg-new-msg`

## Ciclo de vida de sesión

### Crear
```bash
tg-session create <nombre>
tg-serve start <nombre>
tg "✅ Modo remoto activado. Sesión: <nombre>"
```

### Usar (cambiar de sesión desde Telegram)
- Enviar: `usar <nombre>` o `cambiar a <nombre>`

### Cerrar
- **Desde Telegram**: "cuelgo el teléfono"
- **Desde TUI**: Preguntar "¿Cerramos sesión Telegram? (s/n)"
  - Si sí: `tg-session close <nombre>` → pregunta archivos → limpia
  - Si no: continúa normalmente
- **Por comando**: `tg-session close <nombre>`
  - Pregunta qué hacer con archivos (guardar/borrar)
  - Si guardar: mueve `files/` a `~/Descargas/tg-<nombre>-<fecha>`
  - Si borrar: elimina `files/`
  - Elimina la carpeta de sesión
  - Si no quedan sesiones: pregunta si parar tg-serve

## Inotify watcher

- `tg-monitor` es un daemon persistente que monitoriza `inbox/` via inotify
- Arrancar en background: `tg-serve start <sesion>` lo lanza automáticamente
- Requiere `inotify-tools` instalado en el sistema
- Cuando tg-bot crea un archivo en `inbox/`, el monitor escribe `/tmp/tg-new-msg` con el nombre de la sesión
- **Alternativa a tg-wait**: opencode puede vigilar `/tmp/tg-new-msg` con inotify en vez de llamar a tg-wait

## Notas técnicas

- **tg-bot** usa `/tmp/tg-last-update` para offset de Telegram API
- **tg-bot** persiste la sesión activa en `/tmp/tg-current-session`
- **tg-bot** corre con Python del venv: `tg-relay/.venv/bin/python3`
- **tg-monitor** y **tg-wait** dependen de `inotify-tools` (sistema)
- El `.new` contiene el msg id del último mensaje (se sobrescribe)
- Los mensajes en `inbox/` usan formato `<uuid>.txt` con el texto plano
- Las respuestas en `outbox/` usan formato `<uuid>.txt` con el texto a enviar
- Si se quiere respuesta con audio, el texto en outbox debe empezar con `!tts `
- **TTS local** con Kokoro (82M params, CPU, español + 9 idiomas)
