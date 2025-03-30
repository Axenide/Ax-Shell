#!/bin/bash

# Check if XDG_VIDEOS_DIR is not set
if [ -z "$XDG_VIDEOS_DIR" ]; then
  XDG_VIDEOS_DIR="$HOME/Videos"
fi

# Directorio donde se guardarán las grabaciones
SAVE_DIR="$XDG_VIDEOS_DIR/Recordings"
mkdir -p "$SAVE_DIR"

# Si ya está corriendo gpu-screen-recorder, se envía SIGINT para detenerlo correctamente
if pgrep -f "gpu-screen-recorder" >/dev/null; then
  pkill -SIGINT -f "gpu-screen-recorder"

  # Espera un momento para asegurarse de que la grabación se haya detenido y el archivo esté listo
  sleep 1

  # Obtiene el último archivo grabado
  LAST_VIDEO=$(ls -t "$SAVE_DIR"/*.mp4 2>/dev/null | head -n 1)

  # Notificación con acciones: "View" abre el archivo, "Open folder" abre la carpeta
  ACTION=$(notify-send -a "Ax-Shell" "⬜ Recording stopped" \
    -A "view=View" -A "open=Open folder")

  if [ "$ACTION" = "view" ] && [ -n "$LAST_VIDEO" ]; then
    xdg-open "$LAST_VIDEO"
  elif [ "$ACTION" = "open" ]; then
    xdg-open "$SAVE_DIR"
  fi
  exit 0
fi

# Nombre del archivo de salida para la nueva grabación
OUTPUT_FILE="$SAVE_DIR/$(date +%Y-%m-%d-%H-%M-%S).mp4"

# Iniciar la grabación
notify-send -a "Ax-Shell" "🔴 Recording started"
gpu-screen-recorder -w screen -q ultra -a default_output -ac opus -cr full -f 60 -o "$OUTPUT_FILE"
