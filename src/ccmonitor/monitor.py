#!/usr/bin/env python3
"""CC Monitor V2 — Desktop overlay for Claude Code process monitoring (PyQt6)."""

import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ccmonitor.process_scanner import ProcessScanner
from ccmonitor.state_engine import StateEngine
from ccmonitor.overlay_window import OverlayWindow
from ccmonitor.tray_icon import TrayIcon
from ccmonitor.settings import AppSettings


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
        self._theme = self.settings.load_theme()
        self._poll_timer = QTimer()
        self._blink_timer = QTimer()

    def run(self):
        # wire tray show callback
        self.tray.set_show_callback(self._on_tray_show)
        self.tray.set_theme_toggle_callback(self._on_toggle_theme)
        self.window.apply_theme(self._theme)
        self.tray.apply_theme(self._theme)

        # restore collapsed state
        if self.settings.load_collapsed():
            self.window.hide()
            self.window._collapsed = True
        else:
            self.window.show_expanded()
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(POLL_INTERVAL)

        # blink timer
        self._blink_timer.timeout.connect(self._on_blink)
        self._blink_timer.start(BLINK_INTERVAL)

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

    def _on_toggle_theme(self):
        self._theme = 'light' if self._theme == 'dark' else 'dark'
        self.window.apply_theme(self._theme)
        self.tray.apply_theme(self._theme)
        self.settings.save_theme(self._theme)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # keep running when window hidden

    monitor = Monitor()
    monitor.run()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
