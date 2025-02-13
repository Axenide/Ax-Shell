#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error
set -o pipefail  # Prevent errors in a pipeline from being masked

REPO_URL="https://github.com/Axenide/Ax-Shell"
INSTALL_DIR="$HOME/.config/Ax-Shell"
PACKAGES=(
    fabric-cli-git
    gnome-bluetooth-3.0
    grimblast
    hypridle
    hyprlock
    hyprpicker
    imagemagick
    libnotify
    matugen-bin
    python-fabric-git
    python-pillow
    python-setproctitle
    python-toml
    python-watchdog
    swww
    uwsm
    vte3
)

# Optional: Prevent running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "Please do not run this script as root."
    exit 1
fi

# Install yay-bin if not installed
if ! command -v yay &>/dev/null; then
    echo "Installing yay-bin..."
    tmpdir=$(mktemp -d)
    git clone https://aur.archlinux.org/yay-bin.git "$tmpdir/yay-bin"
    cd "$tmpdir/yay-bin"
    makepkg -si --noconfirm
    cd - > /dev/null
    rm -rf "$tmpdir"
fi

# Clone or update the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating Ax-Shell..."
    git -C "$INSTALL_DIR" pull
else
    echo "Cloning Ax-Shell..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

echo "Installing gray-git..."
yes | yay -S --needed --noconfirm gray-git || true

# Install required packages using yay
echo "Installing required packages..."
yay -S --needed --noconfirm "${PACKAGES[@]}" || true

# Launch Ax-Shell without terminal output
echo "Starting Ax-Shell..."
killall ax-shell 2>/dev/null || true; uwsm app -- python "$INSTALL_DIR/main.py" > /dev/null 2>&1 & disown

echo "Installation complete."
