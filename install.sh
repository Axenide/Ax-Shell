#!/bin/bash

set -e  # Exit immediately if a command fails
set -u  # Treat unset variables as errors
set -o pipefail  # Prevent errors in a pipeline from being masked

REPO_URL="https://github.com/Axenide/Ax-Shell.git"
INSTALL_DIR="$HOME/.config/Ax-Shell"
PACKAGES=(
  brightnessctl
  cava
  fabric-cli-git
  gnome-bluetooth-3.0
  gobject-introspection
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

# Prevent running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "Please do not run this script as root."
    exit 1
fi

aur_helper="yay"

# Check if paru exists, otherwise use yay
if command -v paru &>/dev/null; then
    aur_helper="paru"
elif ! command -v yay &>/dev/null; then
    echo "Installing yay-bin..."
    tmpdir=$(mktemp -d)
    git clone --depth=1 https://aur.archlinux.org/yay-bin.git "$tmpdir/yay-bin"
    (cd "$tmpdir/yay-bin" && makepkg -si --noconfirm)
    rm -rf "$tmpdir"
fi

# Clone or update the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating Ax-Shell..."
    git -C "$INSTALL_DIR" pull
else
    echo "Cloning Ax-Shell..."
    git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
fi

# Install required packages using the detected AUR helper (only if missing)
echo "Installing required packages..."
$aur_helper -Syy --needed --devel --noconfirm "${PACKAGES[@]}" || true

echo "Installing gray-git..."
yes | $aur_helper -Syy --needed --devel --noconfirm gray-git || true

echo "Installing required fonts..."

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

python "$INSTALL_DIR/config/config.py"
echo "Starting Ax-Shell..."
killall ax-shell 2>/dev/null || true
uwsm app -- python "$INSTALL_DIR/main.py" > /dev/null 2>&1 & disown

echo "Installation complete."
