"""Tkinter overlay window for displaying Claude Code instance statuses."""

import tkinter as tk
from state_engine import InstanceState

# Layout
WINDOW_WIDTH = 240
ROW_HEIGHT = 34
HEADER_HEIGHT = 32
MAX_VISIBLE_ROWS = 8
TAB_W = 28
TAB_H = 56
BTN_SIZE = 12

# Colors (macOS dark palette)
BG = '#1c1c1e'
HEADER_BG = '#2c2c2e'
TEXT = '#f5f5f7'
TEXT_SEC = '#98989d'
BORDER = '#38383a'

STATE_CONFIG = {
    InstanceState.RUNNING:  {'color': '#30d158', 'label': '运行中'},
    InstanceState.WAITING:  {'color': '#ffd60a', 'label': '等待确认'},
    InstanceState.COMPLETED:{'color': '#8e8e93', 'label': '已完成'},
    InstanceState.ERROR:    {'color': '#ff453a', 'label': '出错'},
}


class OverlayWindow:
    """Always-on-top floating window with expand/collapse modes."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self._collapsed = False
        self._instances = []
        self._blink_state = True
        self._saved_x = None
        self._saved_y = None
        self._saved_w = None
        self._saved_h = None
        self._tab_side = 'right'  # 'left' or 'right'

        self._build_expanded()
        self._build_collapsed()
        self._center_window()

    # ==================================================================
    # expanded window
    # ==================================================================

    def _build_expanded(self):
        w = self._expanded = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes('-topmost', True)
        w.attributes('-alpha', 0.95)
        w.configure(bg=BG)

        # -- title bar --
        tb = tk.Frame(w, bg=HEADER_BG, height=HEADER_HEIGHT,
                      highlightthickness=1, highlightbackground=BORDER)
        tb.pack(fill=tk.X, side=tk.TOP)
        tb.pack_propagate(False)

        title = tk.Label(tb, text='CC Monitor', fg=TEXT, bg=HEADER_BG,
                         font=('SF Pro Text', 10, 'bold'))
        title.place(x=12, y=7)

        # close button (red circle)
        cb = tk.Canvas(tb, width=BTN_SIZE, height=BTN_SIZE,
                       bg=HEADER_BG, highlightthickness=0, cursor='hand2')
        cb.place(x=WINDOW_WIDTH - 26, y=10)
        cb.create_oval(1, 1, BTN_SIZE - 1, BTN_SIZE - 1,
                       fill='#ff453a', outline='')
        cb.bind('<ButtonRelease-1>', self._on_close_click)

        # collapse button (yellow circle)
        mb = tk.Canvas(tb, width=BTN_SIZE, height=BTN_SIZE,
                       bg=HEADER_BG, highlightthickness=0, cursor='hand2')
        mb.place(x=WINDOW_WIDTH - 44, y=10)
        mb.create_oval(1, 1, BTN_SIZE - 1, BTN_SIZE - 1,
                       fill='#ffd60a', outline='')
        mb.bind('<ButtonRelease-1>', self._on_collapse_click)

        # drag
        tb.bind('<Button-1>', self._drag_start)
        tb.bind('<B1-Motion>', self._drag_move)
        title.bind('<Button-1>', self._drag_start)
        title.bind('<B1-Motion>', self._drag_move)

        # instance list
        self._list_frame = tk.Frame(w, bg=BG)
        self._list_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self._resize_expanded(0)
        w.withdraw()

    def _resize_expanded(self, row_count):
        rows = max(1, min(row_count, MAX_VISIBLE_ROWS))
        h = HEADER_HEIGHT + rows * ROW_HEIGHT + 2
        self._expanded.geometry(f'{WINDOW_WIDTH}x{h}')
        self._lift()

    # ==================================================================
    # collapsed tab
    # ==================================================================

    def _build_collapsed(self):
        w = self._collapsed_win = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes('-topmost', True)
        w.attributes('-alpha', 0.93)
        w.configure(bg=BG)

        # outer frame with border
        outer = tk.Frame(w, bg=BORDER, width=TAB_W + 2, height=TAB_H + 2)
        outer.pack_propagate(False)
        outer.pack()

        # inner frame (content area)
        inner = tk.Frame(outer, bg=BG, width=TAB_W, height=TAB_H)
        inner.place(x=1, y=1)

        # status dot
        dot_size = 14
        self._tab_dot = tk.Canvas(inner, width=dot_size, height=dot_size,
                                  bg=BG, highlightthickness=0, cursor='hand2')
        self._tab_dot.place(x=(TAB_W - dot_size) // 2, y=6)

        # separator line
        sep = tk.Frame(inner, bg=BORDER, width=16, height=1)
        sep.place(x=(TAB_W - 16) // 2, y=24)

        # expand arrow
        self._tab_arrow = tk.Label(inner, text='▶', fg=TEXT_SEC, bg=BG,
                                   font=('SF Pro Text', 10), cursor='hand2')
        self._tab_arrow.place(x=(TAB_W - 10) // 2, y=30)

        # click to expand — entire inner area
        for child in (inner, self._tab_dot, self._tab_arrow):
            child.bind('<Button-1>', lambda e: self.expand())

        # drag — bind on inner + arrow (dot is for expand only)
        inner.bind('<B1-Motion>', self._tab_drag_move)
        inner.bind('<Button-1>', self._tab_drag_start)
        self._tab_arrow.bind('<B1-Motion>', self._tab_drag_move)
        self._tab_arrow.bind('<Button-1>', self._tab_drag_start)

        w.withdraw()

    # ==================================================================
    # drag — expanded
    # ==================================================================

    def _drag_start(self, event):
        self._drag_x = event.x_root
        self._drag_y = event.y_root

    def _drag_move(self, event):
        dx = event.x_root - self._drag_x
        dy = event.y_root - self._drag_y
        x = self._expanded.winfo_x() + dx
        y = self._expanded.winfo_y() + dy
        self._expanded.geometry(f'+{x}+{y}')
        self._drag_x = event.x_root
        self._drag_y = event.y_root
        self._lift()

    # ==================================================================
    # drag — collapsed tab
    # ==================================================================

    def _tab_drag_start(self, event):
        self._drag_x = event.x_root
        self._drag_y = event.y_root

    def _tab_drag_move(self, event):
        dx = event.x_root - self._drag_x
        dy = event.y_root - self._drag_y
        x = self._collapsed_win.winfo_x() + dx
        y = self._collapsed_win.winfo_y() + dy
        self._collapsed_win.geometry(f'+{x}+{y}')
        self._drag_x = event.x_root
        self._drag_y = event.y_root
        self._lift()

    # ==================================================================
    # button handlers
    # ==================================================================

    def _on_collapse_click(self, event):
        self.collapse()

    def _on_close_click(self, event):
        self.quit()

    # ==================================================================
    # expand / collapse
    # ==================================================================

    def collapse(self):
        self._saved_x = self._expanded.winfo_x()
        self._saved_y = self._expanded.winfo_y()
        self._saved_w = self._expanded.winfo_width()
        self._saved_h = self._expanded.winfo_height()
        self._expanded.withdraw()
        self._snap_tab_to_edge()
        self._collapsed_win.deiconify()
        self._collapsed = True
        self._update_tab_arrow()
        self._lift()

    def expand(self):
        self._collapsed_win.withdraw()
        if self._saved_x is not None:
            self._expanded.geometry(
                f'{self._saved_w}x{self._saved_h}+{self._saved_x}+{self._saved_y}')
        self._expanded.deiconify()
        self._collapsed = False
        self._lift()

    def _snap_tab_to_edge(self):
        sw = self._collapsed_win.winfo_screenwidth()
        sh = self._collapsed_win.winfo_screenheight()
        cx = self._saved_x or (sw - WINDOW_WIDTH - 20)
        cy = self._saved_y or 60

        if cx < sw / 2:
            self._tab_side = 'left'
            new_x = 0
        else:
            self._tab_side = 'right'
            new_x = sw - TAB_W - 3

        new_y = max(0, min(cy, sh - TAB_H))
        self._collapsed_win.geometry(f'+{new_x}+{new_y}')
        self._lift()

    def _update_tab_arrow(self):
        """Update arrow direction to point toward screen center."""
        self._tab_arrow.configure(text='▶' if self._tab_side == 'left' else '◀')

    # ==================================================================
    # display
    # ==================================================================

    def update_instances(self, instances):
        self._instances = instances

        for w in self._list_frame.winfo_children():
            w.destroy()

        count = min(len(instances), MAX_VISIBLE_ROWS)
        self._resize_expanded(count)

        for i, inst in enumerate(instances[:MAX_VISIBLE_ROWS]):
            self._draw_row(i, inst)

        self._update_tab_dot(instances)

    def _draw_row(self, i, inst):
        state = inst['state']
        cfg = STATE_CONFIG.get(state, STATE_CONFIG[InstanceState.RUNNING])
        cwd = inst.get('cwd', '')
        dir_name = cwd.rstrip('/').split('/')[-1] if cwd else '?'

        row_bg = BG if i % 2 == 0 else '#242426'

        row = tk.Frame(self._list_frame, bg=row_bg, height=ROW_HEIGHT)
        row.pack(fill=tk.X, side=tk.TOP)
        row.pack_propagate(False)

        # status dot
        dot_color = cfg['color']
        if state == InstanceState.WAITING and not self._blink_state:
            dot_color = row_bg

        dot = tk.Canvas(row, width=22, height=ROW_HEIGHT,
                        bg=row_bg, highlightthickness=0)
        dot.pack(side=tk.LEFT)
        dot.create_oval(6, (ROW_HEIGHT - 8) // 2,
                        14, (ROW_HEIGHT + 8) // 2,
                        fill=dot_color, outline='')

        # directory name
        lbl = tk.Label(row, text=dir_name, fg=TEXT, bg=row_bg,
                       font=('SF Pro Text', 11), anchor=tk.W)
        lbl.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        # state badge
        badge = tk.Label(row, text=cfg['label'], fg=cfg['color'], bg=row_bg,
                         font=('PingFang SC', 9))
        badge.pack(side=tk.RIGHT, padx=8)

    def _update_tab_dot(self, instances):
        priority = [InstanceState.ERROR, InstanceState.WAITING,
                    InstanceState.RUNNING, InstanceState.COMPLETED]
        color = '#8e8e93'
        for s in priority:
            if any(i['state'] == s for i in instances):
                color = STATE_CONFIG[s]['color']
                break
        self._tab_dot.delete('all')
        self._tab_dot.create_oval(1, 1, 13, 13, fill=color, outline='')

    def toggle_blink(self):
        self._blink_state = not self._blink_state
        if self._instances:
            self.update_instances(self._instances)

    # ==================================================================
    # helpers
    # ==================================================================

    def _lift(self):
        if self._collapsed:
            self._collapsed_win.attributes('-topmost', True)
            self._collapsed_win.lift()
        else:
            self._expanded.attributes('-topmost', True)
            self._expanded.lift()

    def _center_window(self):
        sw = self._expanded.winfo_screenwidth()
        x = sw - WINDOW_WIDTH - 20
        y = 60
        self._expanded.geometry(
            f'{WINDOW_WIDTH}x{HEADER_HEIGHT + ROW_HEIGHT + 2}+{x}+{y}')
        self._lift()

    # ==================================================================
    # lifecycle
    # ==================================================================

    def show(self):
        self._expanded.deiconify()
        self._collapsed = False
        self._lift()

    def is_collapsed(self):
        return self._collapsed

    def is_alive(self):
        try:
            return self.root.winfo_exists()
        except tk.TclError:
            return False

    def process_events(self):
        try:
            self.root.update()
        except tk.TclError:
            return
        if not self.is_alive():
            return
        self._lift()

    def quit(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
