# Fabric Configuration Troubleshooting Guide

## Problem: SUPER+ALT+B Keybind Not Working / Fabric Bar Not Loading

### Quick Diagnosis Steps

1. **Test the keybind manually first:**
   ```bash
   killall ax-shell; uwsm-app $(python /home/caden/.config/CC-Ax-Shell/main.py)
   ```

2. **Check for import errors:**
   ```bash
   python /home/caden/.config/CC-Ax-Shell/main.py 2>&1 | head -10
   ```

### Common Root Causes & Solutions

#### 1. **Fabric API Changes (Most Common)**
**Symptoms:** ImportError messages like:
```
ImportError: cannot import name 'HyprlandLanguage' from 'fabric.hyprland.widgets'
```

**Cause:** Upstream Fabric library updates change class names

**Solution:** Update import statements in affected modules:
- `HyprlandLanguage` → `Language`
- `HyprlandWorkspaces` → `Workspaces` 
- `HyprlandActiveWindow` → `ActiveWindow`

**Files to check:**
- `modules/bar.py`
- `modules/notch.py`
- Any other modules importing from `fabric.hyprland.widgets`

**How to find affected files:**
```bash
grep -r "from fabric\.hyprland\.widgets import.*Hyprland" modules/
```

#### 2. **Path Mismatch Issues**
**Symptoms:** 
- Keybind triggers but nothing happens
- "No such file or directory" errors

**Check for:**
- Hardcoded paths in `config/hypr/ax-shell.conf`
- Symlink integrity: `ls -la ~/.config/ | grep Ax-Shell`
- Current working directory vs expected paths

#### 3. **Key Modifier Conflicts**
**Symptoms:** Other custom keybinds work but Fabric ones don't

**Check:**
- `$mod = LSUPER` vs `SUPER` in override vs main config
- Verify keybind registration: `hyprctl binds | grep "killall ax-shell"`

### Debugging Process

1. **Verify configuration loading:**
   ```bash
   echo $AXENIDE_OVERRIDES_WORK  # Should return "true"
   ```

2. **Check current keybinds:**
   ```bash
   hyprctl binds | grep "killall ax-shell"
   ```

3. **Test Fabric installation:**
   ```bash
   python -c "import fabric; print('Fabric installed')"
   ```

4. **Check available Fabric classes:**
   ```bash
   python -c "from fabric.hyprland.widgets import *; print([x for x in dir() if 'Language' in x])"
   ```

### Fix Template

When Fabric API changes occur:

1. **Identify the error:** Look for `ImportError: cannot import name 'HyprlandXXX'`
2. **Find new class name:** `python -c "from fabric.hyprland.widgets import *; print([x for x in dir() if 'XXX' in x])"`
3. **Update imports:** Remove `Hyprland` prefix from class names
4. **Test:** Run main.py to verify no more import errors
5. **Reload:** `hyprctl reload` to apply changes

### Files That Commonly Need Updates
- `modules/bar.py` - Language and Workspaces widgets
- `modules/notch.py` - ActiveWindow widget  
- Any custom modules using Hyprland widgets

### Prevention
- Always test `python main.py` after upstream merges
- Keep a backup of working import statements
- Document custom API adaptations in your overrides

This troubleshooting approach: **Check keybind → Test manual execution → Fix import errors → Reload config**