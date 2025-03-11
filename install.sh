#!/bin/bash
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Please, don't run as root."
  exit 1
fi

REPO_URL="https://github.com/Axenide/Ax-Shell"
INSTALL_DIR="$HOME/.config/Ax-Shell"
PACKAGES=(
  acpi
  brightnessctl
  cava
  fabric-cli-git
  gnome-bluetooth-3.0
  gpu-screen-recorder
  grimblast
  hypridle
  hyprlock
  hyprpicker
  hyprsunset
  imagemagick
  libnotify
  matugen-bin
  noto-fonts-emoji
  playerctl
  python-fabric-git
  python-ijson
  python-pillow
  python-psutil
  python-requests
  python-setproctitle
  python-toml
  python-watchdog
  swappy
  swww
  tesseract
  unzip
  uwsm
  wl-clipboard
  wlinhibit
)

if command -v yay >/dev/null; then
  aur_helper="yay"
elif command -v paru >/dev/null; then
  aur_helper="paru"
else
  echo "Instalando yay-bin..."
  tmpdir=$(mktemp -d)
  git clone https://aur.archlinux.org/yay-bin.git "$tmpdir/yay-bin"
  (cd "$tmpdir/yay-bin" && makepkg -si --noconfirm)
  rm -rf "$tmpdir"
  aur_helper="yay"
fi

if [ -d "$INSTALL_DIR" ]; then
  git -C "$INSTALL_DIR" pull
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

"$aur_helper" -Syy --devel --needed --noconfirm "${PACKAGES[@]}"
yes | "$aur_helper" -Syy --devel --needed --noconfirm gray-git

FONT_URL="https://github.com/zed-industries/zed-fonts/releases/download/1.2.0/zed-sans-1.2.0.zip"
FONT_DIR="$HOME/.fonts/zed-sans"
TEMP_ZIP="/tmp/zed-sans-1.2.0.zip"

# Check if fonts are already installed
if [ ! -d "$FONT_DIR" ]; then
    echo "Downloading fonts from $FONT_URL..."
    curl -L -o "$TEMP_ZIP" "$FONT_URL"

    echo "Extracting fonts to $FONT_DIR..."
    mkdir -p "$FONT_DIR"
    unzip -o "$TEMP_ZIP" -d "$FONT_DIR"

    echo "Cleaning up..."
    rm "$TEMP_ZIP"
else
    echo "Fonts are already installed. Skipping download and extraction."
fi

# Copy local fonts if not already present
if [ ! -d "$HOME/.fonts/tabler-icons" ]; then
    echo "Copying local fonts to $HOME/.fonts/tabler-icons..."
    mkdir -p "$HOME/.fonts/tabler-icons"
    cp -r "$INSTALL_DIR/assets/fonts/"* "$HOME/.fonts/tabler-icons"
else
    echo "Local fonts are already installed. Skipping copy."
fi

killall ax-shell 2>/dev/null || true
uwsm app -- python "$INSTALL_DIR/main.py" > /dev/null 2>&1 & disown

echo "Instalación completa."
