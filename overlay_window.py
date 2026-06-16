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
        self._last_tab_side = None

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
        self._keep_on_top()

    def _keep_on_top(self):
        """Force window to stay on top (macOS workaround)."""
        if not self._collapsed:
            self._expanded.attributes('-topmost', True)
            self._expanded.lift()
        else:
            self._collapsed_win.attributes('-topmost', True)
            self._collapsed_win.lift()

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
        self._last_tab_side = None
        self._keep_on_top()

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
        self._keep_on_top()

    # ---------- expand / collapse ----------

    def collapse(self):
        self._expanded.withdraw()
        self._snap_tab_to_edge()
        self._collapsed_win.deiconify()
        self._collapsed = True
        self._keep_on_top()

    def expand(self):
        self._collapsed_win.withdraw()
        tx = self._collapsed_win.winfo_x()
        ty = self._collapsed_win.winfo_y()
        self._expanded.geometry(f'+{tx}+{ty}')
        self._expanded.deiconify()
        self._collapsed = False
        self._keep_on_top()

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
        self._keep_on_top()

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
        self._keep_on_top()

    # ---------- lifecycle ----------

    def show(self):
        """Show the expanded window and start main loop."""
        self._expanded.deiconify()
        self._collapsed = False
        self._keep_on_top()

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
        self._keep_on_top()

    def quit(self):
        """Clean shutdown."""
        try:
            self.root.destroy()
        except tk.TclError:
            pass
