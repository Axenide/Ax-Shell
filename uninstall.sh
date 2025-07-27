#!/bin/bash

echo "This will permanently delete Ax-Shell cache, configuration, and remove its entry from hyprland.conf."
read -p "Are you sure you want to continue? [y/N] " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 1
fi

rm -rf ~/.cache/ax-shell
rm -rf ~/.config/Ax-Shell

conf_file=~/.config/hypr/hyprland.conf
tmp_file=$(mktemp)

awk '
BEGIN { found_comment=0 }
{
    if ($0 ~ /# Ax-Shell/) {
        found_comment=1
        next
    }
    if (found_comment && $0 ~ /source[[:space:]]*=[[:space:]]*~\/\.config\/Ax-Shell\/config\/hypr\/ax-shell\.conf/) {
        found_comment=0
        next
    }
    print
}' "$conf_file" > "$tmp_file" && mv "$tmp_file" "$conf_file"

echo "Ax-Shell data and config removed successfully."
