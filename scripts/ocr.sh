#!/usr/bin/env bash

# Take a screenshot and perform OCR
ocr_text=$(hyprshot -m region -z -r -s  | tesseract -l eng+rus+chi_sim - - 2>/dev/null)

# Comprueba si Tesseract devolvió algo
if [[ -n "$ocr_text" ]]; then
    # Copia el texto reconocido al portapapeles
    echo -n "$ocr_text" | wl-copy
    notify-send -a "Ax-Shell" "OCR Success" "Text Copied to Clipboard"
else
    notify-send -a "Ax-Shell" "OCR Failed" "No text recognized or operation failed"
fi
