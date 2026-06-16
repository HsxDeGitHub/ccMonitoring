# CC Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a macOS always-on-top floating window that monitors all running Claude Code instances and displays their status (running/waiting/completed/error).

**Architecture:** Four-module Python app: ProcessScanner finds claude processes via psutil, StateEngine maps process data to instance states, OverlayWindow renders a tkinter floating window with expand/collapse, and monitor.py ties them together with a 1.5s polling loop.

**Tech Stack:** Python 3, psutil, tkinter (built-in)

---

### Task 1: Project setup

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```text
psutil>=5.9.0
```

- [ ] **Step 2: Install dependency**

Run: `pip install -r requirements.txt`
Expected: psutil installed successfully

- [ ] **Step 3: Verify Python and tkinter availability**

Run: `python3 -c "import tkinter; import psutil; print('OK')"`
Expected: `OK`

---

### Task 2: Process Scanner

**Files:**
- Create: `process_scanner.py`

- [ ] **Step 1: Write process_scanner.py**

```python
"""Scan system for running Claude Code processes."""

import psutil


class ProcessScanner:
    """Finds and tracks Claude Code processes on the system."""

    def __init__(self):
        self._proc_cache = {}  # pid -> psutil.Process (for cpu_percent tracking)

    def scan(self):
        """Scan for claude processes and return list of process info dicts.

        Returns:
            list[dict]: Each dict has keys: pid, cwd, cpu_percent, create_time, cmdline.
            cpu_percent is 0.0 on first scan, meaningful on subsequent scans.
        """
        found_pids = set()
        instances = []

        for proc in psutil.process_iter(['pid', 'cmdline', 'cwd', 'create_time']):
            try:
                info = proc.info
                if not info['cmdline']:
                    continue

                cmdline_str = ' '.join(info['cmdline'])
                if 'claude' not in cmdline_str.lower():
                    continue
                # Exclude our own monitor process
                if 'monitor.py' in cmdline_str:
                    continue

                pid = info['pid']
                found_pids.add(pid)

                # Get cpu_percent for this process
                if pid in self._proc_cache:
                    cached_proc = self._proc_cache[pid]
                    cpu_pct = cached_proc.cpu_percent() or 0.0
                else:
                    self._proc_cache[pid] = proc
                    proc.cpu_percent()  # prime the measurement
                    cpu_pct = 0.0

                instances.append({
                    'pid': pid,
                    'cwd': info['cwd'] or '',
                    'cpu_percent': cpu_pct,
                    'create_time': info['create_time'] or 0,
                })

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Clean up dead processes from cache
        for pid in list(self._proc_cache.keys()):
            if pid not in found_pids:
                del self._proc_cache[pid]

        return instances
```

- [ ] **Step 2: Verify scanner runs without error**

Run: `python3 -c "from process_scanner import ProcessScanner; s = ProcessScanner(); print(s.scan())"`
Expected: Returns a list (possibly empty if no claude process running).

---

### Task 3: State Engine

**Files:**
- Create: `state_engine.py`

- [ ] **Step 1: Write state_engine.py**

```python
"""Determine Claude Code instance state from process data."""

from enum import Enum
import time


class InstanceState(Enum):
    RUNNING = 'running'
    WAITING = 'waiting'
    COMPLETED = 'completed'
    ERROR = 'error'


# CPU threshold: above this means actively working, below means idle/waiting
CPU_ACTIVE_THRESHOLD = 5.0
# How long to keep dead instances visible (seconds)
GHOST_TTL = 30


class StateEngine:
    """Tracks Claude Code instances and determines their current state."""

    def __init__(self):
        # instance_key -> {state, cwd, create_time, exit_time, exit_code, last_seen_pid}
        self._instances = {}
        # pid -> exit_code tracking
        self._exit_codes = {}

    def _make_key(self, info):
        """Generate a stable key from pid + cwd + create_time."""
        return f"{info['pid']}:{info['cwd']}:{info.get('create_time', 0)}"

    def update(self, active_processes):
        """Update instance states based on current active processes.

        Args:
            active_processes: list of dicts from ProcessScanner.scan()

        Returns:
            list[dict]: Current instances with state info, sorted by state priority.
            Each dict: {key, cwd, state, cpu_percent, pid}
        """
        now = time.time()
        active_keys = set()

        for proc in active_processes:
            key = self._make_key(proc)
            active_keys.add(key)

            inst = self._instances.get(key, {})
            inst['pid'] = proc['pid']
            inst['cwd'] = proc['cwd']
            inst['cpu_percent'] = proc['cpu_percent']
            inst['last_seen'] = now

            if proc['cpu_percent'] > CPU_ACTIVE_THRESHOLD:
                inst['state'] = InstanceState.RUNNING
            else:
                inst['state'] = InstanceState.WAITING

            # Store exiting pid -> key mapping for exit code lookup
            self._exit_codes[proc['pid']] = key
            self._instances[key] = inst

        # Mark dead instances
        for key, inst in list(self._instances.items()):
            if key not in active_keys:
                if inst.get('state') not in (InstanceState.COMPLETED, InstanceState.ERROR):
                    # Process just died — check exit code
                    pid = inst.get('pid')
                    exit_code = self._check_exit_code(pid)
                    if exit_code == 0:
                        inst['state'] = InstanceState.COMPLETED
                    else:
                        inst['state'] = InstanceState.ERROR
                    inst['exit_time'] = now

                # Remove ghosts older than TTL
                exit_time = inst.get('exit_time', 0)
                if now - exit_time > GHOST_TTL:
                    del self._instances[key]
                    continue

                self._instances[key] = inst

        return self._get_sorted_list()

    def _check_exit_code(self, pid):
        """Try to get exit code for a pid. Returns 0 if can't determine."""
        try:
            proc = __import__('psutil').Process(pid)
            # psutil may still have exit code info briefly
            if not proc.is_running():
                ret = proc.wait(timeout=0)
                return ret if ret is not None else 0
        except Exception:
            pass
        return 0

    def _get_sorted_list(self):
        """Return instances sorted by state priority: ERROR > WAITING > RUNNING > COMPLETED."""
        priority = {
            InstanceState.ERROR: 0,
            InstanceState.WAITING: 1,
            InstanceState.RUNNING: 2,
            InstanceState.COMPLETED: 3,
        }
        result = []
        for key, inst in self._instances.items():
            result.append({
                'key': key,
                'pid': inst.get('pid', 0),
                'cwd': inst.get('cwd', ''),
                'state': inst.get('state', InstanceState.RUNNING),
                'cpu_percent': inst.get('cpu_percent', 0.0),
            })
        result.sort(key=lambda x: priority.get(x['state'], 99))
        return result
```

- [ ] **Step 2: Verify state engine runs without error**

Run: `python3 -c "from state_engine import StateEngine; e = StateEngine(); result = e.update([]); print('States:', result)"`
Expected: `States: []`

- [ ] **Step 3: Manual unit test — verify state transitions**

Run:
```bash
python3 -c "
from state_engine import StateEngine, InstanceState

e = StateEngine()

# Simulate active process
active = [{'pid': 99999, 'cwd': '/test', 'cpu_percent': 10.0, 'create_time': 1}]
result = e.update(active)
assert result[0]['state'] == InstanceState.RUNNING, f'Expected RUNNING, got {result[0][\"state\"]}'
print('PASS: active process -> RUNNING')

# Simulate idle process
active[0]['cpu_percent'] = 1.0
result = e.update(active)
assert result[0]['state'] == InstanceState.WAITING, f'Expected WAITING, got {result[0][\"state\"]}'
print('PASS: idle process -> WAITING')

# Simulate process gone
result = e.update([])
assert result[0]['state'] in (InstanceState.COMPLETED, InstanceState.ERROR)
print(f'PASS: dead process -> {result[0][\"state\"].value}')

print('All tests passed')
"
```
Expected: `All tests passed`

---

### Task 4: Overlay Window

**Files:**
- Create: `overlay_window.py`

- [ ] **Step 1: Write overlay_window.py**

```python
"""Tkinter overlay window for displaying Claude Code instance statuses."""

import tkinter as tk
from state_engine import InstanceState


# Constants
WINDOW_WIDTH = 380
ROW_HEIGHT = 32
HEADER_HEIGHT = 30
MAX_VISIBLE_ROWS = 8
TAB_WIDTH = 36
TAB_HEIGHT = 80

STATE_CONFIG = {
    InstanceState.RUNNING: {'color': '#22c55e', 'label': 'RUN'},
    InstanceState.WAITING: {'color': '#eab308', 'label': 'WAIT'},
    InstanceState.COMPLETED: {'color': '#6b7280', 'label': 'DONE'},
    InstanceState.ERROR: {'color': '#ef4444', 'label': 'ERR'},
}


class OverlayWindow:
    """Always-on-top floating window with expand/collapse modes."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # hide until fully built

        self._collapsed = False
        self._drag_x = 0
        self._drag_y = 0
        self._instances = []
        self._blink_state = True

        self._build_expanded()
        self._build_collapsed()
        self._center_window()

    # ---------- expanded view ----------

    def _build_expanded(self):
        self._expanded = tk.Toplevel(self.root)
        self._expanded.overrideredirect(True)
        self._expanded.attributes('-topmost', True)
        self._expanded.attributes('-alpha', 0.88)
        self._expanded.configure(bg='#1e1e2e')

        # Title bar
        title_bar = tk.Frame(self._expanded, bg='#181825', height=HEADER_HEIGHT)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        title_bar.pack_propagate(False)

        title = tk.Label(title_bar, text='CC Monitor', fg='#cdd6f4',
                         bg='#181825', font=('Menlo', 11, 'bold'))
        title.pack(side=tk.LEFT, padx=10)

        collapse_btn = tk.Label(title_bar, text='−', fg='#a6adc8',
                                bg='#181825', font=('Menlo', 14),
                                cursor='hand2')
        collapse_btn.pack(side=tk.RIGHT, padx=4)
        collapse_btn.bind('<Button-1>', lambda e: self.collapse())

        close_btn = tk.Label(title_bar, text='×', fg='#a6adc8',
                             bg='#181825', font=('Menlo', 14),
                             cursor='hand2')
        close_btn.pack(side=tk.RIGHT, padx=4)
        close_btn.bind('<Button-1>', lambda e: self.quit())

        # Drag support on title bar
        for w in (title_bar, title):
            w.bind('<Button-1>', self._start_drag)
            w.bind('<B1-Motion>', self._on_drag)

        # Instance list area (scrollable via canvas)
        self._list_frame = tk.Frame(self._expanded, bg='#1e1e2e')
        self._list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        self._list_frame.pack_propagate(False)

        self._update_window_height(0)
        self._expanded.withdraw()

    def _update_window_height(self, row_count):
        rows = max(1, min(row_count, MAX_VISIBLE_ROWS))
        h = HEADER_HEIGHT + rows * ROW_HEIGHT + 4
        self._expanded.geometry(f'{WINDOW_WIDTH}x{h}')

    # ---------- collapsed tab ----------

    def _build_collapsed(self):
        self._collapsed_win = tk.Toplevel(self.root)
        self._collapsed_win.overrideredirect(True)
        self._collapsed_win.attributes('-topmost', True)
        self._collapsed_win.attributes('-alpha', 0.85)
        self._collapsed_win.configure(bg='#181825')

        self._tab_frame = tk.Frame(self._collapsed_win, bg='#181825',
                                   width=TAB_WIDTH, height=TAB_HEIGHT)
        self._tab_frame.pack_propagate(False)
        self._tab_frame.pack()

        self._tab_dot = tk.Canvas(self._tab_frame, width=16, height=16,
                                  bg='#181825', highlightthickness=0)
        self._tab_dot.place(x=10, y=12)

        self._tab_arrow = tk.Label(self._tab_frame, text='◀▶', fg='#6c7086',
                                   bg='#181825', font=('Menlo', 8),
                                   cursor='hand2')
        self._tab_arrow.place(x=6, y=55)

        self._tab_frame.bind('<Button-1>', lambda e: self.expand())
        self._tab_dot.bind('<Button-1>', lambda e: self.expand())
        self._tab_arrow.bind('<Button-1>', lambda e: self.expand())

        # Drag tab frame
        self._tab_frame.bind('<B1-Motion>', self._on_tab_drag)
        self._tab_frame.bind('<Button-1>', self._start_tab_drag)

        self._collapsed_win.withdraw()

    def _on_tab_drag(self, event):
        x = self._collapsed_win.winfo_x() + event.x - self._drag_x
        y = self._collapsed_win.winfo_y() + event.y - self._drag_y
        self._collapsed_win.geometry(f'+{x}+{y}')
        self._last_tab_side = None  # user positioned manually

    def _start_tab_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y
        self._last_tab_side = None

    # ---------- drag support ----------

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self._expanded.winfo_x() + event.x - self._drag_x
        y = self._expanded.winfo_y() + event.y - self._drag_y
        self._expanded.geometry(f'+{x}+{y}')

    # ---------- expand / collapse ----------

    def collapse(self):
        self._expanded.withdraw()
        self._snap_tab_to_edge()
        self._collapsed_win.deiconify()
        self._collapsed = True

    def expand(self):
        self._collapsed_win.withdraw()
        # Position expanded window near the tab
        tx = self._collapsed_win.winfo_x()
        ty = self._collapsed_win.winfo_y()
        self._expanded.geometry(f'+{tx}+{ty}')
        self._expanded.deiconify()
        self._collapsed = False

    def _snap_tab_to_edge(self):
        """Snap collapsed tab to left or right screen edge."""
        screen_w = self._collapsed_win.winfo_screenwidth()
        screen_h = self._collapsed_win.winfo_screenheight()
        current_x = self._expanded.winfo_x()
        current_y = self._expanded.winfo_y()

        if current_x < screen_w / 2:
            new_x = 0
        else:
            new_x = screen_w - TAB_WIDTH

        new_y = max(0, min(current_y, screen_h - TAB_HEIGHT))
        self._collapsed_win.geometry(f'+{new_x}+{new_y}')

    # ---------- display update ----------

    def update_instances(self, instances):
        """Refresh the instance list display."""
        self._instances = instances

        # Clear current rows
        for w in self._list_frame.winfo_children():
            w.destroy()

        visible_count = min(len(instances), MAX_VISIBLE_ROWS)
        self._update_window_height(visible_count)

        for i, inst in enumerate(instances[:MAX_VISIBLE_ROWS]):
            self._draw_instance_row(i, inst)

        # Update collapsed tab dot color
        self._update_tab_dot(instances)

    def _draw_instance_row(self, i, inst):
        state = inst['state']
        cfg = STATE_CONFIG.get(state, STATE_CONFIG[InstanceState.RUNNING])
        cwd = inst.get('cwd', '')
        # Extract short label from last directory component
        dir_name = cwd.rstrip('/').split('/')[-1] if cwd else '?'
        # Shorten cwd for display
        if len(cwd) > 40:
            cwd = '...' + cwd[-37:]

        row = tk.Frame(self._list_frame, bg='#1e1e2e', height=ROW_HEIGHT)
        row.pack(fill=tk.X, side=tk.TOP)
        row.pack_propagate(False)

        # Status dot
        dot_size = 10
        dot = tk.Canvas(row, width=dot_size + 4, height=ROW_HEIGHT,
                        bg='#1e1e2e', highlightthickness=0)
        dot.pack(side=tk.LEFT)

        color = cfg['color']
        if state == InstanceState.WAITING and self._blink_state:
            color = '#1e1e2e'  # blink off

        dot.create_oval(2, (ROW_HEIGHT - dot_size) // 2,
                        dot_size + 2, (ROW_HEIGHT + dot_size) // 2,
                        fill=color, outline='')

        # CWD label with directory name as prefix
        display_text = f'{cwd}  ({dir_name})'
        cwd_label = tk.Label(row, text=display_text, fg='#cdd6f4', bg='#1e1e2e',
                             font=('Menlo', 10), anchor=tk.W)
        cwd_label.pack(side=tk.LEFT, padx=4)

        # State label
        state_label = tk.Label(row, text=cfg['label'], fg=cfg['color'],
                               bg='#1e1e2e', font=('Menlo', 9))
        state_label.pack(side=tk.RIGHT, padx=6)

    def _update_tab_dot(self, instances):
        """Set tab dot color to the highest-priority state."""
        priority_order = [InstanceState.ERROR, InstanceState.WAITING,
                          InstanceState.RUNNING, InstanceState.COMPLETED]
        color = '#6b7280'  # default gray
        for state in priority_order:
            if any(i['state'] == state for i in instances):
                color = STATE_CONFIG[state]['color']
                break

        self._tab_dot.delete('all')
        self._tab_dot.create_oval(2, 2, 14, 14, fill=color, outline='')

    def toggle_blink(self):
        """Toggle blink state for WAITING instances. Call from timer."""
        self._blink_state = not self._blink_state
        if self._instances:
            self.update_instances(self._instances)

    def _center_window(self):
        screen_w = self._expanded.winfo_screenwidth()
        screen_h = self._expanded.winfo_screenheight()
        x = screen_w - WINDOW_WIDTH - 20
        y = 60
        self._expanded.geometry(f'{WINDOW_WIDTH}x{HEADER_HEIGHT + ROW_HEIGHT + 4}+{x}+{y}')

    # ---------- lifecycle ----------

    def show(self):
        """Show the expanded window and start main loop."""
        self._expanded.deiconify()
        self._collapsed = False

    def is_collapsed(self):
        return self._collapsed

    def is_alive(self):
        """Check if the user has closed the window."""
        try:
            return self.root.winfo_exists()
        except tk.TclError:
            return False

    def process_events(self):
        """Process pending tkinter events (non-blocking)."""
        self.root.update()

    def quit(self):
        """Clean shutdown."""
        try:
            self.root.destroy()
        except tk.TclError:
            pass
```

- [ ] **Step 2: Verify overlay module imports without error**

Run: `python3 -c "from overlay_window import OverlayWindow; print('OK')"`
Expected: `OK` (no GUI will appear because we call withdraw)

---

### Task 5: Main Controller + Entry Point

**Files:**
- Create: `monitor.py`

- [ ] **Step 1: Write monitor.py**

```python
#!/usr/bin/env python3
"""CC Monitor — Desktop overlay for Claude Code process monitoring."""

import time

from process_scanner import ProcessScanner
from state_engine import StateEngine
from overlay_window import OverlayWindow


POLL_INTERVAL = 1.5  # seconds
BLINK_INTERVAL = 0.6  # seconds


class Monitor:
    """Main controller that ties process scanning, state engine, and GUI."""

    def __init__(self):
        self.scanner = ProcessScanner()
        self.engine = StateEngine()
        self.window = OverlayWindow()
        self._last_blink = time.time()

    def run(self):
        """Start the monitoring loop."""
        self.window.show()

        while self.window.is_alive():
            loop_start = time.time()

            # Poll processes
            active = self.scanner.scan()
            instances = self.engine.update(active)
            self.window.update_instances(instances)

            # Blink effect for WAITING state
            now = time.time()
            if now - self._last_blink > BLINK_INTERVAL:
                self.window.toggle_blink()
                self._last_blink = now

            # Process GUI events (non-blocking)
            self.window.process_events()

            # Sleep for remaining interval
            elapsed = time.time() - loop_start
            remaining = POLL_INTERVAL - elapsed
            if remaining > 0:
                time.sleep(remaining)


def main():
    monitor = Monitor()
    monitor.run()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Make monitor.py executable**

Run: `chmod +x monitor.py`

- [ ] **Step 3: Verify the app starts without crashing**

Run: `python3 monitor.py`
Expected: Window appears in the top-right corner. Press `×` to close.

If no claude process is running, the window will show empty (just the title bar).

- [ ] **Step 4: Test with an actual Claude Code instance**

1. Open a terminal and run `claude` (or just `node -e "setInterval(() => {}, 1000)"` as a stand-in process since that won't match the claude keyword... actually let's think about this — the scanner looks for "claude" in the command line).

To test: start a dummy process with "claude" in its name:
```bash
python3 -c "import sys; sys.argv = ['claude', '--test']; import time; time.sleep(60)" &
```
Then run `python3 monitor.py` — the dummy process should show as WAITING (yellow dot).
Expected: Monitor shows one instance.

---

### Task 6: Final verification

- [ ] **Step 1: End-to-end test**

1. Start the monitor: `python3 monitor.py`
2. In another terminal, start `claude` (or a real Claude Code session)
3. Verify the monitor shows the instance with a green dot when Claude is actively responding
4. Verify the dot turns yellow when Claude is waiting for input
5. Click `−` to collapse to side tab — verify tab shows correct color
6. Click the tab to expand back
7. Stop the Claude Code process — verify the state changes to COMPLETED or ERROR
8. Click `×` to close the monitor

- [ ] **Step 2: Confirm no residual processes**

After closing the monitor, run: `ps aux | grep monitor.py`
Expected: No monitor process remaining.
