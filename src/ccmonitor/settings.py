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
