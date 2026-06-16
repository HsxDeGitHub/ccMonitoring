"""PyQt6 overlay window for displaying Claude Code instance statuses."""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QScrollArea, QFrame, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent

from ccmonitor.state_engine import InstanceState
from ccmonitor.settings import AppSettings

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

# Module-level references — initialized to dark, updated by apply_theme()
BG = THEMES['dark']['BG']
HEADER_BG = THEMES['dark']['HEADER_BG']
TEXT = THEMES['dark']['TEXT']
TEXT_SEC = THEMES['dark']['TEXT_SEC']
BORDER = THEMES['dark']['BORDER']
ROW_BG_ALT = THEMES['dark']['ROW_BG_ALT']

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


class ClickableLabel(QLabel):
    """QLabel that emits clicked signal on mouse press."""
    clicked = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


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

    def snap_to_edge(self, ref_x: int, ref_y: int):
        screen = QApplication.primaryScreen().availableGeometry()
        if ref_x < screen.width() // 2:
            new_x = 0
        else:
            new_x = screen.width() - self.width()
        new_y = max(0, min(ref_y, screen.height() - TAB_H))
        self.move(new_x, new_y)


class OverlayWindow(QWidget):
    """PyQt6 always-on-top floating window."""

    def __init__(self):
        super().__init__()
        self.setObjectName('expanded')
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(build_stylesheet('dark'))
        self.setFixedWidth(WINDOW_WIDTH)

        self._instances = []
        self._blink_state = True
        self._drag_pos = None
        self._collapsed = False
        self._tab = None
        self._theme_name = 'dark'
        self._settings = AppSettings()

        self._build_title_bar()
        self._build_list_area()

        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

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

        # Close button (red) — using ClickableLabel
        close_btn = ClickableLabel(bar)
        close_btn.setGeometry(WINDOW_WIDTH - 26, 10, 12, 12)
        close_btn.setStyleSheet('background-color: #ff453a; border-radius: 6px;')
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._on_close)

        # Collapse button (yellow) — using ClickableLabel
        coll_btn = ClickableLabel(bar)
        coll_btn.setGeometry(WINDOW_WIDTH - 44, 10, 12, 12)
        coll_btn.setStyleSheet('background-color: #ffd60a; border-radius: 6px;')
        coll_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        coll_btn.clicked.connect(self._on_collapse_click)

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
        if self._collapsed:
            return
        self._collapsed = True
        self._settings.save_window_position(self.x(), self.y())
        self._settings.save_collapsed(True)
        self.hide()
        self._tab = CollapsedTab()
        self._tab.snap_to_edge(self.x(), self.y())
        self._tab.expand_requested.connect(self._on_expand)
        if self._instances:
            self._update_tab_dots()
        self._tab.show()

    def _on_expand(self):
        if self._tab:
            self._tab.hide()
            self._tab.deleteLater()
            self._tab = None
        self._collapsed = False
        self._settings.save_collapsed(False)
        self.show()
        self._keep_on_top()

    def _on_close(self):
        if self._collapsed and self._tab:
            self._tab.hide()
        QApplication.quit()

    # -- display --

    def update_instances(self, instances):
        self._instances = instances

        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._row_dots = []
        self._row_state_labels = []
        for i, inst in enumerate(instances[:MAX_VISIBLE_ROWS]):
            row, dot, state_lbl = self._make_row(i, inst)
            self._list_layout.insertWidget(i, row)
            self._row_dots.append((dot, i))
            self._row_state_labels.append((state_lbl, inst))

        self._update_height(min(len(instances), MAX_VISIBLE_ROWS))
        self._list_widget.update()

    def _make_row(self, i: int, inst: dict) -> tuple:
        state = inst['state']
        cfg = STATE_CONFIG.get(state, STATE_CONFIG[InstanceState.RUNNING])
        cwd = inst.get('cwd', '')
        dir_name = cwd.rstrip('/').split('/')[-1] if cwd else '?'
        pid = inst.get('pid', 0)
        display_name = f'{dir_name} (PID: {pid})'

        row = QFrame()
        row.setFixedHeight(ROW_HEIGHT)
        row_bg = BG if i % 2 == 0 else ROW_BG_ALT
        row.setStyleSheet(f'background-color: {row_bg};')
        row._row_bg = row_bg  # store for blink

        # status dot
        dot = QLabel(row)
        dot.setFixedSize(8, 8)
        dot.move(10, (ROW_HEIGHT - 8) // 2)
        dot_color = cfg['color']
        if state == InstanceState.WAITING and not self._blink_state:
            dot_color = row_bg
        dot.setStyleSheet(f'background-color: {dot_color}; border-radius: 4px;')
        dot._color = cfg['color']
        dot._row_bg = row_bg  # for blink off state

        # directory name
        name_lbl = QLabel(display_name, row)
        name_lbl.setStyleSheet(f'color: {TEXT}; font-size: 11px; background: transparent;')
        name_lbl.move(26, 8)
        name_lbl.setFixedWidth(148)

        # state label
        state_lbl = QLabel(cfg['label'], row)
        state_lbl.setStyleSheet(f'color: {cfg["color"]}; font-size: 9px; background: transparent;')
        state_lbl.move(WINDOW_WIDTH - 52, 10)
        state_lbl._color = cfg['color']

        # tooltip
        row.setToolTip(f'{cwd}\nPID: {pid}')

        return row, dot, state_lbl

    def _update_height(self, row_count):
        rows = max(1, row_count)
        h = HEADER_HEIGHT + rows * ROW_HEIGHT
        self.setFixedHeight(h)
        self._scroll.setGeometry(0, HEADER_HEIGHT, WINDOW_WIDTH, rows * ROW_HEIGHT)

    def _update_tab_dots(self):
        if not self._tab:
            return
        self._tab.set_dots(self._instances)

    def _keep_on_top(self):
        """Re-assert stays-on-top without activating window."""
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

    def toggle_blink(self):
        self._blink_state = not self._blink_state
        for dot, i in getattr(self, '_row_dots', []):
            if i < len(self._instances):
                inst = self._instances[i]
                if inst['state'] == InstanceState.WAITING:
                    color = dot._color if self._blink_state else dot._row_bg
                    dot.setStyleSheet(f'background-color: {color}; border-radius: 4px;')

    def apply_theme(self, theme_name: str):
        global BG, HEADER_BG, TEXT, TEXT_SEC, BORDER, ROW_BG_ALT, STATE_CONFIG
        t = THEMES[theme_name]
        BG = t['BG']
        HEADER_BG = t['HEADER_BG']
        TEXT = t['TEXT']
        TEXT_SEC = t['TEXT_SEC']
        BORDER = t['BORDER']
        ROW_BG_ALT = t['ROW_BG_ALT']
        STATE_CONFIG = {
            InstanceState.RUNNING:  {'color': t['RUNNING'],  'label': '运行中'},
            InstanceState.WAITING:  {'color': t['WAITING'],  'label': '等待确认'},
            InstanceState.COMPLETED:{'color': t['COMPLETED'],'label': '已完成'},
            InstanceState.ERROR:    {'color': t['ERROR'],    'label': '出错'},
        }

        self._theme_name = theme_name
        self.setStyleSheet(build_stylesheet(theme_name))
        self._list_widget.setStyleSheet(f'background: {BG};')
        self._scroll.setStyleSheet(f'QScrollArea {{ border: none; background: {BG}; }}')

        # Update title bar label
        for child in self._title_bar.children():
            if isinstance(child, QLabel):
                child.setStyleSheet(
                    f'color: {TEXT}; font-size: 10px; font-weight: bold; background: transparent;'
                )
                break

        # Rebuild existing rows
        if self._instances:
            self.update_instances(self._instances)

        # Update collapsed tab
        if self._tab:
            self._tab.set_dots(self._instances)

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - WINDOW_WIDTH - 20, 60)

    # -- lifecycle --

    def show_expanded(self):
        if self._tab:
            self._tab.hide()
            self._tab.deleteLater()
            self._tab = None
        self._collapsed = False
        self.show()
        self._keep_on_top()

    def is_collapsed(self):
        return self._collapsed
