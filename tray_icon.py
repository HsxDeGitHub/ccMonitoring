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
