> [!WARNING]
> Ax-Shell has been deprecated in favor of [Ambxst](https://axeni.de/ambxst) and will not receive any more updates.
>
> Ambxst is more performant, customizable and feature-rich, and has feature parity with Ax-Shell. Go check it out!

---

<p align="center">
<a href="https://github.com/Axenide/Ax-Shell">
  <img src="assets/cover.png">
  </a>
</p>

<p align="center">
  <sub><sup><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Telegram-Animated-Emojis/main/Activity/Sparkles.webp" alt="Sparkles" width="25" height="25"/></sup></sub>
  <a href="https://github.com/hyprwm/Hyprland">
    <img src="https://img.shields.io/badge/A%20hackable%20shell%20for-Hyprland-0092CD?style=for-the-badge&logo=linux&color=0092CD&logoColor=D9E0EE&labelColor=000000" alt="A hackable shell for Hyprland">
  </a>
  <a href="https://github.com/Fabric-Development/fabric/">
    <img src="https://img.shields.io/badge/Powered%20by-Fabric-FAFAFA?style=for-the-badge&logo=python&color=FAFAFA&logoColor=D9E0EE&labelColor=000000" alt="Powered by Fabric">
  <sub><sup><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Telegram-Animated-Emojis/main/Activity/Sparkles.webp" alt="Sparkles" width="25" height="25"/></sup></sub>
  </a>
  </p>

  <p align="center">
  <a href="https://github.com/Axenide/Ax-Shell/stargazers">
    <img src="https://img.shields.io/github/stars/Axenide/Ax-Shell?style=for-the-badge&logo=github&color=E3B341&logoColor=D9E0EE&labelColor=000000" alt="GitHub stars">
  </a>
  <a href="https://ko-fi.com/Axenide">
    <img src="https://img.shields.io/badge/Support me on-Ko--fi-FF6433?style=for-the-badge&logo=kofi&logoColor=white&labelColor=000000" alt="Ko-Fi">
  </a>
  <a href="https://discord.com/invite/gHG9WHyNvH">
    <img src="https://img.shields.io/discord/669048311034150914?style=for-the-badge&logo=discord&logoColor=D9E0EE&labelColor=000000&color=5865F2&label=Discord" alt="Discord">
  </a>
</p>

---

<h2><sub><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Camera%20with%20Flash.png" alt="Camera with Flash" width="25" height="25" /></sub> Screenshots</h2>
<table align="center">
  <tr>
    <td colspan="4"><img src="assets/screenshots/1.png"></td>
  </tr>
  <tr>
    <td colspan="1"><img src="assets/screenshots/2.png"></td>
    <td colspan="1"><img src="assets/screenshots/3.png"></td>
    <td colspan="1" align="center"><img src="assets/screenshots/4.png"></td>
    <td colspan="1" align="center"><img src="assets/screenshots/5.png"></td>
  </tr>
</table>

<h2><sub><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Package.png" alt="Package" width="25" height="25" /></sub> Installation</h2>

> [!NOTE]
> You need a functioning Hyprland installation.
> This will also enable NetworkManager if it is not already enabled.

### Arch Linux

> [!TIP]
> This command also works for updating an existing installation!

**Run the following command in your terminal once logged into Hyprland:**
```bash
curl -fsSL get.axeni.de/ax-shell | bash
```

**Alternative:**
```bash
curl -fsSL https://raw.githubusercontent.com/Axenide/Ax-Shell/main/install.sh | bash
```

### NixOS
[poogas](https://github.com/poogas) has created a flake for Ax-Shell.
👉 [Try it out!](https://github.com/poogas/Ax-Shell) 👈

### Manual Installation
1. Install dependencies:
    - [Fabric](https://github.com/Fabric-Development/fabric)
    - [fabric-cli](https://github.com/Fabric-Development/fabric-cli)
    - [Gray](https://github.com/Fabric-Development/gray)
    - [Matugen](https://github.com/InioX/matugen)
    - `awww`
    - `brightnessctl`
    - `cava`
    - `cliphist`
    - `ddcutil`
    - `gnome-bluetooth-3.0`
    - `gobject-introspection`
    - `gpu-screen-recorder`
    - `grimblast`
    - `hypridle`
    - `hyprlock`
    - `hyprpicker`
    - `hyprshot`
    - `hyprsunset`
    - `imagemagick`
    - `libnotify`
    - `networkmanager`
    - `network-manager-applet`
    - `nm-connection-editor`
    - `noto-fonts-emoji`
    - `nvtop`
    - `playerctl`
    - `swappy`
    - `tesseract`
    - `tesseract-data-eng`
    - `tesseract-data-spa`
    - `tmux`
    - `unzip`
    - `upower`
    - `uwsm`
    - `vte3`
    - `webp-pixbuf-loader`
    - `wl-clipboard`
    - Python dependencies:
        - PyGObject
        - ijson
        - numpy
        - pillow
        - psutil
        - pywayland
        - requests
        - setproctitle
        - toml
        - watchdog
    - Fonts (automated on first run):
        - Zed Sans
        - Tabler Icons

2. Download and run Ax-Shell:
    ```bash
    git clone https://github.com/Axenide/Ax-Shell.git ~/.config/Ax-Shell
    uwsm -- app python ~/.config/Ax-Shell/main.py > /dev/null 2>&1 & disown
    ```

<h2><sub><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Travel%20and%20places/Rocket.png" alt="Rocket" width="25" height="25" /></sub> Roadmap</h2>

- [x] App Launcher
- [x] Bluetooth Manager
- [x] Calculator
- [x] Calendar
- [x] Clipboard Manager
- [x] Color Picker
- [x] Customizable UI
- [x] Dashboard
- [x] Dock
- [x] Emoji Picker
- [x] Kanban Board
- [x] Network Manager
- [x] Notifications
- [x] OCR
- [x] Pins
- [x] Power Manager
- [x] Power Menu
- [x] Screen Recorder
- [x] Screenshot
- [x] Settings
- [x] System Tray
- [x] Terminal
- [x] Tmux Session Manager
- [x] Update checker
- [x] Vertical Layout
- [x] Wallpaper Selector
- [x] Workspaces Overview
- [x] Multi-monitor support
- [ ] Multimodal AI Assistant
- [ ] OSD
- [ ] OTP Manager

---

<table align="center">
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Telegram-Animated-Emojis/main/Activity/Sparkles.webp" alt="Sparkles" width="16" height="16" /><sup> sᴜᴘᴘᴏʀᴛ ᴛʜᴇ ᴘʀᴏᴊᴇᴄᴛ </sup><img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Telegram-Animated-Emojis/main/Activity/Sparkles.webp" alt="Sparkles" width="16" height="16" /></td>
  </tr>
  <tr>
    <td align="center">
      <a href='https://ko-fi.com/Axenide' target='_blank'>
        <img style='border:0px;height:128px;'
             src='https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExc3N4NzlvZWs2Z2tsaGx4aHgwa3UzMWVpcmNwZTNraTM2NW84ZDlqbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/PaF9a1MpqDzovyqVKj/giphy.gif'
             border='0' alt='Support me on Ko-fi!' />
      </a>
    </td>
  </tr>
</table>
