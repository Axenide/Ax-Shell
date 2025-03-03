#!/bin/bash

# Optional slurp arguments
SLURP_ARGS="${1:-}"

# Temporary file name
TMP_IMG="tmp.png"

# Select area with slurp and capture with grim
grim -g "$(slurp $SLURP_ARGS)" "$TMP_IMG" && \
tesseract -l eng "$TMP_IMG" - | wl-copy && \


if [ -f "${TMP_IMG}" ]; then
    notify-send -a "Ax-Shell" -i "${full_path}" "OCR Sucess" "Text Copied to Clipboard"
else
    notify-send -a "Ax-Shell" "OCR Aborted"
fi
rm "$TMP_IMG"