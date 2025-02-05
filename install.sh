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
    swww
    ttf-tabler-icons
    uwsm
    vte3
)

# Optional: Prevent running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "Please do not run this script as root."
    exit 1
fi

# Install yay-bin if not installed
if ! command -v yay &>/dev/null && ! command -v paru &>/dev/null; then
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

if command -v yay &>/dev/null; then
    # Install gray-git and required packages using yay
    yay -S --needed --noconfirm gray-git || exit 1
    echo "Installing required packages with yay..."
    yay -S --needed --noconfirm "${PACKAGES[@]}" || exit 1
else command -v paru &>/dev/null; then
    # Install gray-git and required packages using paru
    paru -S --needed --noconfirm gray-git || exit 1
    echo "Installing required packages with paru..."
    paru -S --needed --noconfirm "${PACKAGES[@]}" || exit 1
fi

# Launch Ax-Shell without terminal output
echo "Starting Ax-Shell..."
uwsm app -- python "$INSTALL_DIR/main.py" > /dev/null 2>&1 & disown

echo "Installation complete."
