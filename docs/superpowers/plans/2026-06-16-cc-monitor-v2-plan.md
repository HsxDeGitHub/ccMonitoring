# CC Monitor V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite CC Monitor UI layer with PyQt6 for native macOS look, add menu bar icon, keyboard shortcuts, tooltips, position memory, and auto-start.

**Architecture:** PyQt6 replaces tkinter for the window layer. Backend (ProcessScanner, StateEngine) stays unchanged. New modules: settings.py (QSettings persistence), tray_icon.py (QSystemTrayIcon). Monitor main loop adapts to PyQt6's event-driven model via QTimer.

**Tech Stack:** Python 3, PyQt6, psutil

---

### Task 1: Update dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**

```text
psutil>=5.9.0
PyQt6>=6.5.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install PyQt6`
Expected: PyQt6 installed successfully

- [ ] **Step 3: Verify imports**

Run: `python3 -c "from PyQt6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu; from PyQt6.QtCore import QTimer, QSettings, Qt; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "deps: add PyQt6 for V2 UI rewrite"
```

---

### Task 2: Settings module

**Files:**
- Create: `settings.py`

- [ ] **Step 1: Write settings.py**

```python
"""Persistent settings via QSettings."""

from PyQt6.QtCore import QSettings, QByteArray


class AppSettings:
    """Wrap QSettings for CC Monitor."""

    def __init__(self):
        self._s = QSettings('ccmonitor', 'ccmonitor')

    def save_window_geometry(self, geometry_bytes: QByteArray):
        self._s.setValue('window/geometry', geometry_bytes)

    def load_window_geometry(self) -> QByteArray | None:
        val = self._s.value('window/geometry')
        return val if isinstance(val, QByteArray) else None

    def save_window_position(self, x: int, y: int):
        self._s.setValue('window/x', x)
        self._s.setValue('window/y', y)

    def load_window_position(self) -> tuple[int, int] | None:
        x = self._s.value('window/x')
        y = self._s.value('window/y')
        if x is not None and y is not None:
            return int(x), int(y)
        return None

    def save_collapsed(self, collapsed: bool):
        self._s.setValue('window/collapsed', collapsed)

    def load_collapsed(self) -> bool:
        val = self._s.value('window/collapsed', False)
        return str(val).lower() == 'true'
```

- [ ] **Step 2: Verify**

Run: `python3 -c "from settings import AppSettings; s = AppSettings(); s.save_collapsed(True); assert s.load_collapsed() == True; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add settings.py
git commit -m "feat: add QSettings persistence module"
```

---

### Task 3: PyQt6 Overlay Window

**Files:**
- Create: `overlay_window.py` (full rewrite)

- [ ] **Step 1: Write overlay_window.py**

```python
"""PyQt6 overlay window for displaying Claude Code instance statuses."""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame, QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QFont, QMouseEvent

from state_engine import InstanceState
from settings import AppSettings

# Layout
WINDOW_WIDTH = 240
ROW_HEIGHT = 34
HEADER_HEIGHT = 32
MAX_VISIBLE_ROWS = 8
TAB_W = 28
TAB_H = 56

# Colors (macOS dark palette)
BG = '#1c1c1e'
HEADER_BG = '#2c2c2e'
TEXT = '#f5f5f7'
TEXT_SEC = '#98989d'
BORDER = '#38383a'

STATE_CONFIG = {
    InstanceState.RUNNING:  {'color': '#30d158', 'bg': 'rgba(48,209,88,0.15)', 'label': '运行中'},
    InstanceState.WAITING:  {'color': '#ffd60a', 'bg': 'rgba(255,214,10,0.15)', 'label': '等待确认'},
    InstanceState.COMPLETED:{'color': '#8e8e93', 'bg': 'rgba(142,142,147,0.10)', 'label': '已完成'},
    InstanceState.ERROR:    {'color': '#ff453a', 'bg': 'rgba(255,69,58,0.15)', 'label': '出错'},
}

STYLE = f"""
QWidget#expanded {{
    background-color: {BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QWidget#titleBar {{
    background-color: {HEADER_BG};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
"""


class CollapsedTab(QWidget):
    """Small tab on screen edge when window is collapsed."""
    expand_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(TAB_W + 2, TAB_H + 2)
        self.setStyleSheet(f'background-color: {BORDER}; border-radius: 6px;')
        self._dot_color = '#8e8e93'
        self._drag_pos = None
        self._build()

    def _build(self):
        inner = QFrame(self)
        inner.setObjectName('tabInner')
        inner.setGeometry(1, 1, TAB_W, TAB_H)
        inner.setStyleSheet(f'QFrame#tabInner {{ background-color: {BG}; border-radius: 5px; }}')

        self._dot = QLabel(inner)
        self._dot.setGeometry(7, 6, 14, 14)
        self._dot.setStyleSheet(f'background-color: {self._dot_color}; border-radius: 7px;')

        arrow = QLabel('▶', inner)
        arrow.setGeometry(7, 30, 14, 16)
        arrow.setStyleSheet(f'color: {TEXT_SEC}; font-size: 10px;')
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Positioned in _snap_to_edge later
        self.move(0, 200)

    def set_dot_color(self, color: str):
        self._dot_color = color
        self._dot.setStyleSheet(f'background-color: {color}; border-radius: 7px;')

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
            new_x = screen.width() - TAB_W - 3
        new_y = max(0, min(ref_y, screen.height() - TAB_H))
        self.move(new_x, new_y)


class OverlayWindow(QWidget):
    """PyQt6 always-on-top floating window."""

    def __init__(self):
        super().__init__()
        self.setObjectName('expanded')
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(STYLE)
        self.setFixedWidth(WINDOW_WIDTH)

        self._instances = []
        self._blink_state = True
        self._drag_pos = None
        self._collapsed = False
        self._settings = AppSettings()

        self._build_title_bar()
        self._build_list_area()

        # keyboard shortcut: ESC to collapse
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # restore position or use default
        saved_pos = self._settings.load_window_position()
        if saved_pos:
            self.move(*saved_pos)
        else:
            self._center()

        self._update_height(0)

    def _build_title_bar(self):
        bar = QFrame(self)
        bar.setObjectName('titleBar')
        bar.setFixedHeight(HEADER_HEIGHT)
        bar.setGeometry(0, 0, WINDOW_WIDTH, HEADER_HEIGHT)

        title = QLabel('CC Monitor', bar)
        title.setStyleSheet(f'color: {TEXT}; font-size: 10px; font-weight: bold; background: transparent;')
        title.move(12, 8)

        # close button (red)
        close_btn = QLabel(bar)
        close_btn.setGeometry(WINDOW_WIDTH - 26, 10, 12, 12)
        close_btn.setStyleSheet('background-color: #ff453a; border-radius: 6px;')
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self._on_close()

        # collapse button (yellow)
        coll_btn = QLabel(bar)
        coll_btn.setGeometry(WINDOW_WIDTH - 44, 10, 12, 12)
        coll_btn.setStyleSheet('background-color: #ffd60a; border-radius: 6px;')
        coll_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        coll_btn.mousePressEvent = lambda e: self._on_collapse_click()

        self._title_bar = bar

    def _build_list_area(self):
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f'QScrollArea {{ border: none; background: {BG}; }}')
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setGeometry(0, HEADER_HEIGHT, WINDOW_WIDTH, 100)

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet(f'background: {BG};')
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._list_widget)

    # -- drag --

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= HEADER_HEIGHT:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_pos is not None:
            self._settings.save_window_position(self.x(), self.y())
        self._drag_pos = None

    # -- keyboard --

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._on_collapse_click()

    # -- collapse / expand --

    def _on_collapse_click(self):
        self._collapsed = True
        self._settings.save_window_position(self.x(), self.y())
        self._settings.save_collapsed(True)
        self.hide()
        self._tab = CollapsedTab()
        self._tab.snap_to_edge(self.x(), self.y())
        self._tab.expand_requested.connect(self._on_expand)
        if self._instances:
            self._update_tab_dot()
        self._tab.show()

    def _on_expand(self):
        self._tab.hide()
        self._tab.deleteLater()
        self._tab = None
        self._collapsed = False
        self._settings.save_collapsed(False)
        self.show()

    def _on_close(self):
        if self._collapsed and hasattr(self, '_tab') and self._tab:
            self._tab.hide()
        QApplication.quit()

    # -- display --

    def update_instances(self, instances):
        self._instances = instances

        # clear old rows (keep stretch at end)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, inst in enumerate(instances[:MAX_VISIBLE_ROWS]):
            self._list_layout.insertWidget(i, self._make_row(i, inst))

        self._update_height(min(len(instances), MAX_VISIBLE_ROWS))

    def _make_row(self, i: int, inst: dict) -> QFrame:
        state = inst['state']
        cfg = STATE_CONFIG.get(state, STATE_CONFIG[InstanceState.RUNNING])
        cwd = inst.get('cwd', '')
        dir_name = cwd.rstrip('/').split('/')[-1] if cwd else '?'
        pid = inst.get('pid', 0)

        row = QFrame()
        row.setFixedHeight(ROW_HEIGHT)
        row_bg = BG if i % 2 == 0 else '#242426'
        row.setStyleSheet(f'background-color: {row_bg};')

        # status dot
        dot = QLabel(row)
        dot.setFixedSize(8, 8)
        dot.move(10, (ROW_HEIGHT - 8) // 2)
        dot_color = cfg['color']
        if state == InstanceState.WAITING and not self._blink_state:
            dot_color = row_bg
        dot.setStyleSheet(f'background-color: {dot_color}; border-radius: 4px;')

        # directory name
        name_lbl = QLabel(dir_name, row)
        name_lbl.setStyleSheet(f'color: {TEXT}; font-size: 11px; background: transparent;')
        name_lbl.move(26, 8)
        name_lbl.setFixedWidth(140)

        # state label
        state_lbl = QLabel(cfg['label'], row)
        state_lbl.setStyleSheet(f'color: {cfg["color"]}; font-size: 9px; background: transparent;')
        state_lbl.move(WINDOW_WIDTH - 60, 10)

        # tooltip: full path + PID
        row.setToolTip(f'{cwd}\nPID: {pid}')

        return row

    def _update_height(self, row_count):
        rows = max(1, row_count)
        h = HEADER_HEIGHT + rows * ROW_HEIGHT
        self.setFixedHeight(h)
        self._scroll.setGeometry(0, HEADER_HEIGHT, WINDOW_WIDTH, rows * ROW_HEIGHT)

    def _update_tab_dot(self):
        if not hasattr(self, '_tab') or not self._tab:
            return
        priority = [InstanceState.ERROR, InstanceState.WAITING,
                    InstanceState.RUNNING, InstanceState.COMPLETED]
        color = '#8e8e93'
        for s in priority:
            if any(i['state'] == s for i in self._instances):
                color = STATE_CONFIG[s]['color']
                break
        self._tab.set_dot_color(color)

    def toggle_blink(self):
        self._blink_state = not self._blink_state
        if self._instances:
            self.update_instances(self._instances)

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - WINDOW_WIDTH - 20, 60)

    # -- lifecycle --

    def show_expanded(self):
        self.show()

    def is_collapsed(self):
        return self._collapsed
```

- [ ] **Step 2: Verify import**

Run: `python3 -c "from overlay_window import OverlayWindow, CollapsedTab; print('OK')"`
Expected: `OK` (No Qt window will appear without QApplication)

- [ ] **Step 3: Commit**

```bash
git add overlay_window.py
git commit -m "feat: rewrite overlay window with PyQt6"
```

---

### Task 4: Tray Icon

**Files:**
- Create: `tray_icon.py`

- [ ] **Step 1: Write tray_icon.py**

```python
"""System tray icon with dropdown menu."""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import Qt

from state_engine import InstanceState

STATE_CONFIG = {
    InstanceState.RUNNING:  '#30d158',
    InstanceState.WAITING:  '#ffd60a',
    InstanceState.COMPLETED:'#8e8e93',
    InstanceState.ERROR:    '#ff453a',
}


class TrayIcon:
    """Menu bar icon with instance list dropdown."""

    def __init__(self):
        self._tray = QSystemTrayIcon()
        self._tray.setToolTip('CC Monitor')
        self._update_icon('#8e8e93')

        self._menu = QMenu()
        self._tray.setContextMenu(self._menu)

    def _update_icon(self, color: str):
        """Draw a circle with 'CC' text as tray icon."""
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 20, 20)
        painter.setPen(QColor('#1c1c1e'))
        painter.setFont(painter.font())
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, 'CC')
        painter.end()
        self._tray.setIcon(QIcon(pixmap))

    def update_instances(self, instances):
        self._menu.clear()

        # Instance list
        priority = [InstanceState.ERROR, InstanceState.WAITING,
                    InstanceState.RUNNING, InstanceState.COMPLETED]
        tray_color = '#8e8e93'

        for s in priority:
            for inst in instances:
                if inst['state'] == s:
                    cwd = inst.get('cwd', '')
                    dir_name = cwd.rstrip('/').split('/')[-1] if cwd else '?'
                    color = STATE_CONFIG.get(s, '#8e8e93')
                    action = QAction(f'  {dir_name}', self._menu)
                    action.setEnabled(False)
                    # color indicator via styled action (simplified)
                    self._menu.addAction(action)
                    if tray_color == '#8e8e93':
                        tray_color = color

        self._menu.addSeparator()

        show_action = QAction('显示窗口', self._menu)
        show_action.triggered.connect(self._on_show)
        self._menu.addAction(show_action)

        quit_action = QAction('退出', self._menu)
        quit_action.triggered.connect(QApplication.quit)
        self._menu.addAction(quit_action)

        self._update_icon(tray_color)

    def set_show_callback(self, callback):
        self._on_show = callback

    def show(self):
        self._tray.show()

    def hide(self):
        self._tray.hide()
```

- [ ] **Step 2: Verify import**

Run: `python3 -c "from tray_icon import TrayIcon; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tray_icon.py
git commit -m "feat: add system tray icon with instance dropdown"
```

---

### Task 5: Update Monitor (PyQt6 event loop)

**Files:**
- Modify: `monitor.py`

- [ ] **Step 1: Rewrite monitor.py**

```python
#!/usr/bin/env python3
"""CC Monitor V2 — Desktop overlay for Claude Code process monitoring (PyQt6)."""

import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from process_scanner import ProcessScanner
from state_engine import StateEngine
from overlay_window import OverlayWindow
from tray_icon import TrayIcon
from settings import AppSettings


POLL_INTERVAL = 1500  # ms
BLINK_INTERVAL = 600  # ms


class Monitor:
    """Main controller — PyQt6 event-driven loop."""

    def __init__(self):
        self.scanner = ProcessScanner()
        self.engine = StateEngine()
        self.window = OverlayWindow()
        self.tray = TrayIcon()
        self.settings = AppSettings()
        self._blink_timer = QTimer()

    def run(self):
        # wire tray show callback
        self.tray.set_show_callback(self._on_tray_show)

        # restore collapsed state
        if self.settings.load_collapsed():
            self.window.hide()
            self.window._collapsed = True
            # The collapsed tab will be created on first poll

        # poll timer
        poll_timer = QTimer()
        poll_timer.timeout.connect(self._poll)
        poll_timer.start(POLL_INTERVAL)

        # blink timer
        self._blink_timer.timeout.connect(self._on_blink)
        self._blink_timer.start(BLINK_INTERVAL)

        # show
        self.window.show_expanded()
        self.tray.show()
        self._poll()  # immediate first scan

    def _poll(self):
        active = self.scanner.scan()
        instances = self.engine.update(active)
        self.window.update_instances(instances)
        self.tray.update_instances(instances)

    def _on_blink(self):
        self.window.toggle_blink()

    def _on_tray_show(self):
        self.window.show_expanded()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # keep running when window hidden

    monitor = Monitor()
    monitor.run()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Make executable**

Run: `chmod +x monitor.py`

- [ ] **Step 3: Verify startup (run briefly then close)**

Run: `python3 monitor.py`
Expected: Window appears, tray icon appears. Close via tray menu or red button.

- [ ] **Step 4: Commit**

```bash
git add monitor.py
git commit -m "feat: update monitor to PyQt6 event-driven loop with tray icon"
```

---

### Task 6: Auto-start via LaunchAgent

**Files:**
- Create: `install_autostart.py` (utility script)
- Create: `com.ccmonitor.plist` (template)

- [ ] **Step 1: Write com.ccmonitor.plist**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ccmonitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>SCRIPT_PATH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
```

- [ ] **Step 2: Write install_autostart.py**

```python
#!/usr/bin/env python3
"""Install or remove auto-start LaunchAgent for CC Monitor."""

import os
import sys
import shutil

PLIST_NAME = 'com.ccmonitor.plist'
PLIST_DIR = os.path.expanduser('~/Library/LaunchAgents')
PLIST_PATH = os.path.join(PLIST_DIR, PLIST_NAME)
SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'monitor.py'))


def install():
    os.makedirs(PLIST_DIR, exist_ok=True)
    template = os.path.join(os.path.dirname(__file__), PLIST_NAME)
    with open(template) as f:
        content = f.read()
    content = content.replace('SCRIPT_PATH', SCRIPT_PATH)
    with open(PLIST_PATH, 'w') as f:
        f.write(content)
    print(f'Installed: {PLIST_PATH}')


def uninstall():
    if os.path.exists(PLIST_PATH):
        os.remove(PLIST_PATH)
        print(f'Removed: {PLIST_PATH}')
    else:
        print('Not installed.')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--uninstall':
        uninstall()
    else:
        install()
```

- [ ] **Step 3: Verify install**

Run: `python3 install_autostart.py && ls ~/Library/LaunchAgents/com.ccmonitor.plist`
Expected: File exists at `~/Library/LaunchAgents/com.ccmonitor.plist`

- [ ] **Step 4: Clean up and commit**

Run: `python3 install_autostart.py --uninstall`
Then:
```bash
git add install_autostart.py com.ccmonitor.plist
git commit -m "feat: add macOS LaunchAgent auto-start support"
```

---

### Task 7: Final verification

- [ ] **Step 1: Install dependencies and run**

```bash
pip install -r requirements.txt
python3 monitor.py
```

Verify:
1. Window appears in top-right, always on top
2. Shows real Claude Code instances with correct states
3. Hover over instance → tooltip shows full path + PID
4. Click yellow dot → collapses to side tab
5. Click side tab → expands back
6. ESC key → collapse/expand
7. Tray icon in menu bar → click shows dropdown with instances
8. "显示窗口" in tray menu → shows window
9. "退出" in tray menu → quits cleanly
10. Red close button → quits cleanly

- [ ] **Step 2: Confirm no residual processes**

After closing, run: `ps aux | grep monitor.py | grep -v grep`
Expected: No output.

- [ ] **Step 3: Remove old tkinter code**

Delete any lingering references if needed. The old overlay_window.py has been fully replaced.
