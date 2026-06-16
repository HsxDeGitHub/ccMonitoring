# Multi-Instance Fixes & Theme Toggle Design

## Issues

1. **Collapsed tab shows only one dot** — when multiple Claude Code instances exist, the collapsed tab aggregates all into a single dot, hiding instance count.
2. **Same-directory instances indistinguishable** — multiple instances from the same directory show identical names; exit code detection never flags ERROR.
3. **No theme support** — all colors are hardcoded dark mode.

## Design

### Fix 1: Multi-dot collapsed tab

**File:** `src/ccmonitor/overlay_window.py` — `CollapsedTab`

- Replace single `set_dot_color(color)` with `set_dots(instances)`.
- Render one dot per instance, side by side (4px gap), up to 8 dots.
- Tab width adjusts dynamically: `14 + count * 12 + (count-1) * 4 + 14`.
- Each dot color matches its instance state from `STATE_CONFIG`.
- `_update_tab_dot()` is replaced by `_update_tab_dots()` that passes the full instance list.

### Fix 2: Instance display & exit code

**a) Display name with PID**

**File:** `src/ccmonitor/overlay_window.py` — `_make_row()`

- Change `dir_name` display from `project` to `project (PID: 12345)`.
- Tooltip already includes PID, keep it.

**b) Exit code detection**

**File:** `src/ccmonitor/state_engine.py` — `_check_exit_code()`

- `NoSuchProcess` → process gone, can't determine exit code → COMPLETED (conservative).
- Process exists and exited with non-zero → ERROR.
- Process exists and exited with zero → COMPLETED.
- Fix: handle `NoSuchProcess` explicitly instead of catch-all returning 0.

### Feature: Dark/Light theme toggle

**Files:** `overlay_window.py`, `tray_icon.py`, `settings.py`

**Color palettes:**

| Token | Dark | Light |
|-------|------|-------|
| BG | `#1c1c1e` | `#f5f5f7` |
| HEADER_BG | `#2c2c2e` | `#e5e5ea` |
| ROW_BG_ALT | `#242426` | `#ececf0` |
| TEXT | `#f5f5f7` | `#1c1c1e` |
| TEXT_SEC | `#98989d` | `#6e6e73` |
| BORDER | `#38383a` | `#c6c6c8` |
| RUNNING | `#30d158` | `#248a3d` |
| WAITING | `#ffd60a` | `#b89b00` |
| COMPLETED | `#8e8e93` | `#6e6e73` |
| ERROR | `#ff453a` | `#cc3829` |

**Settings:** `save_theme(name: str)` / `load_theme() -> str` via QSettings.

**OverlayWindow:** Extract `build_theme(theme_name)` → returns stylesheet string. `apply_theme(name)` regenerates and applies stylesheets for window, rows, and collapsed tab. Rebuilds existing rows after theme change. `CollapsedTab` gets `apply_theme(name)` that recreates the tab with new colors.

**TrayIcon:** Add「切换主题」menu action that triggers a callback. The callback is wired by `Monitor` to toggle between `'dark'` and `'light'` and propagate to both `OverlayWindow` and `CollapsedTab`.

**Monitor:** New method `_on_toggle_theme()` — toggles theme, calls `window.apply_theme(theme)` and `settings.save_theme(theme)`. On startup, reads saved theme and applies it.

**Data flow:**
```
Tray menu「切换主题」→ tray callback → Monitor._on_toggle_theme()
  → window.apply_theme() + collapsed_tab.apply_theme()
  → settings.save_theme()
```
