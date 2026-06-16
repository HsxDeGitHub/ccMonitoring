"""PyQt6 overlay window for displaying Claude Code instance statuses."""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QScrollArea, QFrame, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent

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
    InstanceState.RUNNING:  {'color': '#30d158', 'label': '运行中'},
    InstanceState.WAITING:  {'color': '#ffd60a', 'label': '等待确认'},
    InstanceState.COMPLETED:{'color': '#8e8e93', 'label': '已完成'},
    InstanceState.ERROR:    {'color': '#ff453a', 'label': '出错'},
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


class ClickableLabel(QLabel):
    """QLabel that emits clicked signal on mouse press."""
    clicked = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


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
        self._dragged = False
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
        self._tab = None
        self._settings = AppSettings()

        self._build_title_bar()
        self._build_list_area()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

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
            self._update_tab_dot()
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

        for i, inst in enumerate(instances[:MAX_VISIBLE_ROWS]):
            self._list_layout.insertWidget(i, self._make_row(i, inst))

        self._update_height(min(len(instances), MAX_VISIBLE_ROWS))
        self._keep_on_top()

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

        # tooltip
        row.setToolTip(f'{cwd}\nPID: {pid}')

        return row

    def _update_height(self, row_count):
        rows = max(1, row_count)
        h = HEADER_HEIGHT + rows * ROW_HEIGHT
        self.setFixedHeight(h)
        self._scroll.setGeometry(0, HEADER_HEIGHT, WINDOW_WIDTH, rows * ROW_HEIGHT)

    def _update_tab_dot(self):
        if not self._tab:
            return
        priority = [InstanceState.ERROR, InstanceState.WAITING,
                    InstanceState.RUNNING, InstanceState.COMPLETED]
        color = '#8e8e93'
        for s in priority:
            if any(i['state'] == s for i in self._instances):
                color = STATE_CONFIG[s]['color']
                break
        self._tab.set_dot_color(color)

    def _keep_on_top(self):
        """Force window to top on macOS."""
        self.raise_()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

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
        self._keep_on_top()

    def is_collapsed(self):
        return self._collapsed
