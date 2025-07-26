#!/bin/bash

set -e  # Exit immediately if a command fails
set -u  # Treat unset variables as errors
set -o pipefail  # Prevent errors in a pipeline from being masked

REPO_URL="https://github.com/tr1xem/hyprfabricated.git"
INSTALL_DIR="$HOME/.config/hyprfabricated"
PACKAGES=(
    brightnessctl
    cava
    cliphist
    fabric-cli-git
    gnome-bluetooth-3.0
    gobject-introspection
    gpu-screen-recorder
    hypridle
    hyprlock
    hyprpicker
    hyprshot
    hyprsunset
    imagemagick
    libnotify
    matugen-bin
    noto-fonts-emoji
    nvtop
    playerctl
    power-profiles-daemon
    python-fabric-git
    python-gobject
    python-ijson
    python-numpy
    python-pillow
    python-psutil
    python-pywayland
    python-requests
    python-setproctitle
    python-toml
    python-watchdog
    swappy
    swww-git
    tesseract
    tmux
    ttf-nerd-fonts-symbols-mono
    unzip
    upower
    uwsm
    vte3
    webp-pixbuf-loader
    wl-clipboard
    wlinhibit
    cantarell-fonts
    ttf-jost
    vte3
    otf-nothing-font-git
)

# Prevent running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "Please do not run this script as root."
    exit 1
fi

aur_helper="paru"

PARU_EXISTS_INITIALLY=1

# Check if yay exists, otherwise use paru
if command -v yay &>/dev/null; then
    aur_helper="yay"
elif ! command -v paru &>/dev/null; then
    PARU_EXISTS_INITIALLY=0
    echo "Installing paru-bin..."
    tmpdir=$(mktemp -d)
    git clone --depth=1 https://aur.archlinux.org/paru-bin.git "$tmpdir/paru-bin"
    sudo pacman -S --needed --noconfirm base-devel
    (cd "$tmpdir/paru-bin" && makepkg -si --noconfirm)
    rm -rf "$tmpdir"
fi

# Clone or update the repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating hyprfabricated..."
    git -C "$INSTALL_DIR" pull
else
    echo "Cloning hyprfabricated..."
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
    cp -r "$INSTALL_DIR/assets/fonts/"* "$HOME/.fonts"
else
    echo "Local fonts are already installed. Skipping copy."
fi

python "$INSTALL_DIR/config/config.py"
echo "Starting hyprfabricated..."
killall hyprfabricated 2>/dev/null || true
uwsm app -- python "$INSTALL_DIR/main.py" > /dev/null 2>&1 & disown

echo "Doing Fallback Image..."
cp "$INSTALL_DIR/assets/wallpapers_example/example-1.jpg" ~/.current.wall

if [ $PARU_EXISTS_INITIALLY -eq 0 ]; then
    echo "The script installed paru-bin. Do you want to keep it? (y/n)"
    read -r choice
    if [[ "$choice" =~ ^[Nn]$ ]]; then
        echo "Uninstalling paru-bin..."
        sudo pacman -Rns --noconfirm paru-bin
    else
        echo "Keeping paru-bin."
    fi
fi

echo "If you see a transparent bar change the wallpaper from the notch"
echo "Backup your hypridle and hyprlock config before accepting in config"

echo "Installation complete."
