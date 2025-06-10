#!/bin/bash

set -e          # Exit immediately if a command fails
set -u          # Treat unset variables as errors
set -o pipefail # Prevent errors in a pipeline from being masked

# --- CONFIGURATION ---
REPO_URL="https://github.com/xNovyz/Ax-Shell.git"
REPO_BRANCH="animated-wallpaper"
INSTALL_DIR="$HOME/.config/Ax-Shell"
# ----------------------

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
  mpvpaper
)

# Prevent running as root
if [ "$(id -u)" -eq 0 ]; then
  echo "Please do not run this script as root."
  exit 1
fi

# Detect AUR helper
aur_helper="yay"
if command -v paru &>/dev/null; then
  aur_helper="paru"
elif ! command -v yay &>/dev/null; then
  echo "Installing yay-bin..."
  tmpdir=$(mktemp -d)
  git clone --depth=1 https://aur.archlinux.org/yay-bin.git "$tmpdir/yay-bin"
  (cd "$tmpdir/yay-bin" && makepkg -si --noconfirm)
  rm -rf "$tmpdir"
fi

# Clean if repo exists but is invalid or points to the wrong origin
if git -C "$INSTALL_DIR" rev-parse --is-inside-work-tree &>/dev/null; then
  CURRENT_REMOTE=$(git -C "$INSTALL_DIR" remote get-url origin || echo "")
  if [ "$CURRENT_REMOTE" != "$REPO_URL" ]; then
    echo "Removing old repository from $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
  fi
elif [ -d "$INSTALL_DIR" ]; then
  echo "$INSTALL_DIR exists but is not a valid git repository. Removing it..."
  rm -rf "$INSTALL_DIR"
fi


# Clone or update the repository
if [ -d "$INSTALL_DIR" ]; then
  echo "Updating Ax-Shell..."
  git -C "$INSTALL_DIR" pull
  git -C "$INSTALL_DIR" checkout "$REPO_BRANCH"
else
  echo "Cloning Ax-Shell from $REPO_URL..."
  git clone --depth=1 --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

# Install required packages
echo "Installing required packages..."
$aur_helper -Syy --needed --devel --noconfirm "${PACKAGES[@]}" || true

echo "Installing gray-git..."
yes | $aur_helper -Syy --needed --devel --noconfirm gray-git || true

# Install fonts
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

if [ ! -d "$HOME/.fonts/tabler-icons" ]; then
  echo "Copying local fonts to $HOME/.fonts/tabler-icons..."
  mkdir -p "$HOME/.fonts/tabler-icons"
  cp -r "$INSTALL_DIR/assets/fonts/"* "$HOME/.fonts"
else
  echo "Local fonts are already installed. Skipping copy."
fi

# Start Ax-Shell
python "$INSTALL_DIR/config/config.py"
echo "Starting Ax-Shell..."
killall ax-shell 2>/dev/null || true
uwsm app -- python "$INSTALL_DIR/main.py" >/dev/null 2>&1 &
disown

echo "Installation complete."
