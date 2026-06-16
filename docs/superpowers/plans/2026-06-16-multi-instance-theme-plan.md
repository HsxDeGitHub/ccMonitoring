# Multi-Instance Fixes & Theme Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix collapsed tab to show multiple instances, distinguish same-directory instances by PID, fix exit code detection, and add dark/light theme toggle via tray menu.

**Architecture:** All changes are modifications to 5 existing files. Fixes are isolated per concern. Theme system uses a color token dict per theme, applied via `apply_theme()` on OverlayWindow and CollapsedTab, toggled from tray menu through Monitor.

**Tech Stack:** Python 3.12, PyQt6

---

### Task 1: Fix exit code detection

**Files:**
- Modify: `src/ccmonitor/state_engine.py:83-93`

- [ ] **Step 1: Rewrite `_check_exit_code` to handle NoSuchProcess explicitly**

Replace the entire `_check_exit_code` method (lines 83-93):

```python
def _check_exit_code(self, pid):
    """Try to get exit code for a pid.

    Returns exit code, or None if the process vanished before
    we could read it. Caller decides default for None.
    """
    try:
        import psutil
        proc = psutil.Process(pid)
        if proc.is_running():
            return None  # still running, caller shouldn't query
        ret = proc.wait(timeout=0)
        return ret if ret is not None else 0
    except psutil.NoSuchProcess:
        return None  # vanished, can't determine
    except Exception:
        return None
```

And update the caller in `update()` (lines 63-70) to use the new return value:

```python
# Inside update(), lines 63-70, replace the exit code check block:
if key not in active_keys:
    if inst.get('state') not in (InstanceState.COMPLETED, InstanceState.ERROR):
        exit_code = self._check_exit_code(pid)
        if exit_code is None:
            inst['state'] = InstanceState.COMPLETED
        elif exit_code != 0:
            inst['state'] = InstanceState.ERROR
        else:
            inst['state'] = InstanceState.COMPLETED
        inst['exit_time'] = now
```

- [ ] **Step 2: Verify the change is syntactically correct**

```bash
cd /Users/huangshengxue/code/ai/ccMonitoring && PYTHONPATH=src python3 -c "from ccmonitor.state_engine import StateEngine; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/ccmonitor/state_engine.py
git commit -m "fix: handle NoSuchProcess explicitly in exit code detection

Previously catch-all except returned 0, making all dead processes
show as COMPLETED. Now NoSuchProcess returns None, caller treats
as conservative COMPLETED. Non-zero exit codes correctly flag ERROR."
```

---

### Task 2: Show PID in instance display name

**Files:**
- Modify: `src/ccmonitor/overlay_window.py:275-276`

- [ ] **Step 1: Append PID to display name**

In `_make_row()`, change lines 275-276 from:

```python
dir_name = cwd.rstrip('/').split('/')[-1] if cwd else '?'
pid = inst.get('pid', 0)
```

to:

```python
dir_name = cwd.rstrip('/').split('/')[-1] if cwd else '?'
pid = inst.get('pid', 0)
display_name = f'{dir_name} (PID: {pid})'
```

And change line 298 from `name_lbl = QLabel(dir_name, row)` to:

```python
name_lbl = QLabel(display_name, row)
```

- [ ] **Step 2: Verify the change**

```bash
cd /Users/huangshengxue/code/ai/ccMonitoring && PYTHONPATH=src python3 -c "from ccmonitor.overlay_window import OverlayWindow; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/ccmonitor/overlay_window.py
git commit -m "feat: display PID alongside directory name in instance rows"
```

---

### Task 3: Multi-dot collapsed tab

**Files:**
- Modify: `src/ccmonitor/overlay_window.py:57-119` (CollapsedTab)
- Modify: `src/ccmonitor/overlay_window.py:319-329` (_update_tab_dot)

- [ ] **Step 1: Rewrite `CollapsedTab` to render multiple dots**

Replace the entire `CollapsedTab` class (lines 57-119) with:

```python
class CollapsedTab(QWidget):
    """Small tab on screen edge when window is collapsed. Shows one dot per instance."""
    expand_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(f'background-color: {BORDER}; border-radius: 6px;')
        self._drag_pos = None
        self._dragged = False
        self._instances = []
        self._build()

    def _build(self):
        self._inner = QFrame(self)
        self._inner.setObjectName('tabInner')
        self._inner.setStyleSheet(f'QFrame#tabInner {{ background-color: {BG}; border-radius: 5px; }}')

        self._dots_widget = QWidget(self._inner)
        self._dots_widget.setStyleSheet('background: transparent;')

        arrow = QLabel('▶', self._inner)
        arrow.setStyleSheet(f'color: {TEXT_SEC}; font-size: 10px;')
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._arrow = arrow
        self._resize()

    def set_dots(self, instances):
        """Render one dot per instance, max 8."""
        self._instances = instances[:8]
        # clear old dots
        for child in self._dots_widget.children():
            if isinstance(child, QLabel):
                child.deleteLater()
        count = len(self._instances)
        priority = [InstanceState.ERROR, InstanceState.WAITING,
                    InstanceState.RUNNING, InstanceState.COMPLETED]
        dot_instances = sorted(self._instances,
                               key=lambda i: priority.index(i['state']) if i['state'] in priority else 99)
        for idx, inst in enumerate(dot_instances):
            cfg = STATE_CONFIG.get(inst['state'], STATE_CONFIG[InstanceState.RUNNING])
            dot = QLabel(self._dots_widget)
            dot.setFixedSize(10, 10)
            dot.move(idx * 14 + 8, 8)
            dot.setStyleSheet(f'background-color: {cfg["color"]}; border-radius: 5px;')
        self._resize()

    def _resize(self):
        count = max(len(self._instances), 1)
        w = 14 + count * 14 + (count - 1) * 4 + 8
        h = TAB_H + 2
        self.setFixedSize(w, h)
        self._inner.setGeometry(1, 1, w - 2, TAB_H)
        self._dots_widget.setGeometry(0, 6, w - 2, 18)
        self._arrow.setGeometry(8, 30, w - 18, 16)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            self._dragged = False

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            if abs(delta.x()) > 2 or abs(delta.y()) > 2:
                self._dragged = True
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and not self._dragged:
            self.expand_requested.emit()
        self._drag_pos = None

    def snap_to_edge(self, ref_x: int, ref_y: int):
        screen = QApplication.primaryScreen().availableGeometry()
        if ref_x < screen.width() // 2:
            new_x = 0
        else:
            new_x = screen.width() - self.width()
        new_y = max(0, min(ref_y, screen.height() - TAB_H))
        self.move(new_x, new_y)
```

- [ ] **Step 2: Replace `_update_tab_dot` with `_update_tab_dots`**

Replace `_update_tab_dot()` (lines 319-329) with:

```python
def _update_tab_dots(self):
    if not self._tab:
        return
    self._tab.set_dots(self._instances)
```

And update the caller in `_on_collapse_click()` (line 233): change `self._update_tab_dot()` to `self._update_tab_dots()`.

- [ ] **Step 3: Verify import**

```bash
cd /Users/huangshengxue/code/ai/ccMonitoring && PYTHONPATH=src python3 -c "from ccmonitor.overlay_window import OverlayWindow, CollapsedTab; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/ccmonitor/overlay_window.py
git commit -m "feat: show one dot per instance in collapsed tab"
```

---

### Task 4: Theme save/load in settings

**Files:**
- Modify: `src/ccmonitor/settings.py`

- [ ] **Step 1: Add theme methods to `AppSettings`**

Add these two methods at the end of the class (before the file ends):

```python
def save_theme(self, name: str):
    self._s.setValue('appearance/theme', name)

def load_theme(self) -> str:
    val = self._s.value('appearance/theme', 'dark')
    return str(val) if val else 'dark'
```

- [ ] **Step 2: Verify**

```bash
cd /Users/huangshengxue/code/ai/ccMonitoring && PYTHONPATH=src python3 -c "from ccmonitor.settings import AppSettings; s = AppSettings(); print(s.load_theme())"
```

Expected: `dark`

- [ ] **Step 3: Commit**

```bash
git add src/ccmonitor/settings.py
git commit -m "feat: add theme save/load to AppSettings"
```

---

### Task 5: Theme system in overlay_window.py

**Files:**
- Modify: `src/ccmonitor/overlay_window.py`

- [ ] **Step 1: Replace hardcoded color constants with theme dict and add `build_theme()` / `apply_theme()`**

Replace lines 20-31 (BG through STATE_CONFIG) with:

```python
# Layout
WINDOW_WIDTH = 240
ROW_HEIGHT = 34
HEADER_HEIGHT = 32
MAX_VISIBLE_ROWS = 8
TAB_W = 28
TAB_H = 56

# Theme color palettes
THEMES = {
    'dark': {
        'BG': '#1c1c1e',
        'HEADER_BG': '#2c2c2e',
        'ROW_BG_ALT': '#242426',
        'TEXT': '#f5f5f7',
        'TEXT_SEC': '#98989d',
        'BORDER': '#38383a',
        'RUNNING': '#30d158',
        'WAITING': '#ffd60a',
        'COMPLETED': '#8e8e93',
        'ERROR': '#ff453a',
    },
    'light': {
        'BG': '#f5f5f7',
        'HEADER_BG': '#e5e5ea',
        'ROW_BG_ALT': '#ececf0',
        'TEXT': '#1c1c1e',
        'TEXT_SEC': '#6e6e73',
        'BORDER': '#c6c6c8',
        'RUNNING': '#248a3d',
        'WAITING': '#b89b00',
        'COMPLETED': '#6e6e73',
        'ERROR': '#cc3829',
    },
}

# Module-level references updated by apply_theme()
BG = THEMES['dark']['BG']
HEADER_BG = THEMES['dark']['HEADER_BG']
TEXT = THEMES['dark']['TEXT']
TEXT_SEC = THEMES['dark']['TEXT_SEC']
BORDER = THEMES['dark']['BORDER']

STATE_CONFIG = {
    InstanceState.RUNNING:  {'color': THEMES['dark']['RUNNING'],  'label': '运行中'},
    InstanceState.WAITING:  {'color': THEMES['dark']['WAITING'],  'label': '等待确认'},
    InstanceState.COMPLETED:{'color': THEMES['dark']['COMPLETED'],'label': '已完成'},
    InstanceState.ERROR:    {'color': THEMES['dark']['ERROR'],    'label': '出错'},
}


def build_stylesheet(theme_name: str) -> str:
    t = THEMES[theme_name]
    return f"""
    QWidget#expanded {{
        background-color: {t['BG']};
        border: 1px solid {t['BORDER']};
        border-radius: 8px;
    }}
    QWidget#titleBar {{
        background-color: {t['HEADER_BG']};
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}
    """
```

Rename `STYLE` to `build_stylesheet` and reference it accordingly.

- [ ] **Step 2: Add `apply_theme` method to `OverlayWindow`**

Add to `OverlayWindow` class:

```python
def apply_theme(self, theme_name: str):
    global BG, HEADER_BG, TEXT, TEXT_SEC, BORDER, STATE_CONFIG
    t = THEMES[theme_name]
    BG = t['BG']
    HEADER_BG = t['HEADER_BG']
    TEXT = t['TEXT']
    TEXT_SEC = t['TEXT_SEC']
    BORDER = t['BORDER']
    STATE_CONFIG = {
        InstanceState.RUNNING:  {'color': t['RUNNING'],  'label': '运行中'},
        InstanceState.WAITING:  {'color': t['WAITING'],  'label': '等待确认'},
        InstanceState.COMPLETED:{'color': t['COMPLETED'],'label': '已完成'},
        InstanceState.ERROR:    {'color': t['ERROR'],    'label': '出错'},
    }

    # Update window stylesheet
    self.setStyleSheet(build_stylesheet(theme_name))

    # Update title bar
    for child in self._title_bar.children():
        if isinstance(child, ClickableLabel):
            continue
        if isinstance(child, QLabel):
            child.setStyleSheet(
                f'color: {TEXT}; font-size: 10px; font-weight: bold; background: transparent;'
            )

    # Rebuild list area background
    self._list_widget.setStyleSheet(f'background: {BG};')
    self._scroll.setStyleSheet(f'QScrollArea {{ border: none; background: {BG}; }}')

    # Rebuild existing rows
    if self._instances:
        self.update_instances(self._instances)

    # Update collapsed tab if visible
    if self._tab:
        self._tab.set_dots(self._instances)

def _current_theme(self) -> str:
    return self._theme_name
```

Add `self._theme_name = 'dark'` to `__init__`.

- [ ] **Step 3: Add `apply_theme` to `CollapsedTab`**

Add to `CollapsedTab` class:

```python
def apply_theme(self, theme_name: str):
    global BG, BORDER, TEXT_SEC
    t = THEMES[theme_name]
    BG = t['BG']
    BORDER = t['BORDER']
    TEXT_SEC = t['TEXT_SEC']
    self.setStyleSheet(f'background-color: {BORDER}; border-radius: 6px;')
    self._inner.setStyleSheet(f'QFrame#tabInner {{ background-color: {BG}; border-radius: 5px; }}')
    self._arrow.setStyleSheet(f'color: {TEXT_SEC}; font-size: 10px;')
    if self._instances:
        self.set_dots(self._instances)
```

- [ ] **Step 4: Update `OverlayWindow.__init__` and references**

In `__init__`, replace `self.setStyleSheet(STYLE)` with `self.setStyleSheet(build_stylesheet('dark'))`.

Replace all module-level references to `STYLE` with `build_stylesheet` calls where appropriate.

- [ ] **Step 5: Verify syntax**

```bash
cd /Users/huangshengxue/code/ai/ccMonitoring && PYTHONPATH=src python3 -c "from ccmonitor.overlay_window import OverlayWindow, CollapsedTab, build_stylesheet; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/ccmonitor/overlay_window.py
git commit -m "feat: add dark/light theme system with apply_theme()"
```

---

### Task 6: Theme toggle in tray menu + wire in Monitor

**Files:**
- Modify: `src/ccmonitor/tray_icon.py`
- Modify: `src/ccmonitor/monitor.py`

- [ ] **Step 1: Add theme toggle to `TrayIcon`**

In `TrayIcon.update_instances()`, add after the separator (after line 66, before the「显示窗口」action):

```python
theme_action = QAction('切换主题', self._menu)
theme_action.triggered.connect(self._on_toggle_theme)
self._menu.addAction(theme_action)
```

And in `__init__`, add `self._on_toggle_theme = lambda: None`.

Add method to `TrayIcon`:

```python
def set_theme_toggle_callback(self, callback):
    self._on_toggle_theme = callback
```

- [ ] **Step 2: Wire theme toggle in `Monitor`**

In `Monitor.__init__`, after `self.tray = TrayIcon()`, add:

```python
self._theme = self.settings.load_theme()
```

In `Monitor.run()`, after `self.tray.set_show_callback(self._on_tray_show)`, add:

```python
self.tray.set_theme_toggle_callback(self._on_toggle_theme)
# Apply saved theme on startup
if self._theme != 'dark':
    self.window.apply_theme(self._theme)
```

Add method to `Monitor`:

```python
def _on_toggle_theme(self):
    self._theme = 'light' if self._theme == 'dark' else 'dark'
    self.window.apply_theme(self._theme)
    self.settings.save_theme(self._theme)
```

- [ ] **Step 3: Verify full import chain**

```bash
cd /Users/huangshengxue/code/ai/ccMonitoring && PYTHONPATH=src python3 -c "from ccmonitor.monitor import Monitor; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/ccmonitor/tray_icon.py src/ccmonitor/monitor.py
git commit -m "feat: add theme toggle via tray menu"
```
