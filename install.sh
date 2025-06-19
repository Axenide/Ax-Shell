#!/bin/bash

# Ax-Shell Installation Script
# Ported by:

# ________  ________  ___  __        ___    ___ _____ ______   ________  ________     
#|\   __  \|\   __  \|\  \|\  \     |\  \  /  /|\   _ \  _   \|\   __  \|\   ____\    
#\ \  \|\  \ \  \|\  \ \  \/  /|_   \ \  \/  / | \  \\\__\ \  \ \  \|\  \ \  \___|    
# \ \  \\\  \ \   __  \ \   ___  \   \ \    / / \ \  \\|__| \  \ \   __  \ \  \       
#  \ \  \\\  \ \  \ \  \ \  \\ \  \   \/  /  /   \ \  \    \ \  \ \  \ \  \ \  \____  
#   \ \_______\ \__\ \__\ \__\\ \__\__/  / /      \ \__\    \ \__\ \__\ \__\ \_______\
#    \|_______|\|__|\|__|\|__| \|__|\___/ /        \|__|     \|__|\|__|\|__|\|_______|
#                                  \|___|/                                            
# https://gh.io/SufremOak
# https://youtube.com/@OakyMac


set -e
set -u
set -o pipefail

REPO_URL="https://github.com/Axenide/Ax-Shell.git"
INSTALL_DIR="$HOME/.config/Ax-Shell"
PACKAGES=(
    brightnessctl
    cava
    gnome-bluetooth
    gir1.2-gtk-3.0
    imagemagick
    libnotify-bin
    fonts-noto-color-emoji
    nvtop
    playerctl
    python3
    python3-gi
    python3-numpy
    python3-pil
    python3-psutil
    python3-requests
    python3-toml
    python3-venv
    python3-watchdog
    tesseract-ocr
    tmux
    unzip
    upower
    webp
    wl-clipboard
    curl
    git
)

# Prevent running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "Please do not run this script as root."
    exit 1
fi

# Update and install required packages
echo "Updating package lists..."
sudo apt update

echo "Installing required packages..."
sudo apt install -y "${PACKAGES[@]}"

# Clone or update the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating Ax-Shell..."
    git -C "$INSTALL_DIR" pull
else
    echo "Cloning Ax-Shell..."
    git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
fi

echo "Installing required fonts..."

FONT_URL="https://github.com/zed-industries/zed-fonts/releases/download/1.2.0/zed-sans-1.2.0.zip"
FONT_DIR="$HOME/.fonts/zed-sans"
TEMP_ZIP="/tmp/zed-sans-1.2.0.zip"

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
    cp -r "$INSTALL_DIR/assets/fonts/." "$HOME/.fonts/tabler-icons"
else
    echo "Local fonts are already installed. Skipping copy."
fi

# Update font cache
fc-cache -fv

echo "Starting Python Enviroment Configuration..."
python3 -m venv $INSTALL_DIR/venv
source $INSTALL_DIR/venv/bin/activate
pip install --upgrade pip
pip install git+https://github.com/Fabric-Development/fabric.git

python3 "$INSTALL_DIR/config/config.py"
echo "Starting Ax-Shell..."
killall ax-shell 2>/dev/null || true
# 'uwsm' is not available on Debian/Ubuntu, so we run directly
python3 "$INSTALL_DIR/main.py" > /dev/null 2>&1 & disown

echo "Installation complete."

