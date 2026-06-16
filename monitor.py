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

            # Keep UI responsive: short sleeps with event processing
            elapsed = time.time() - loop_start
            deadline = loop_start + POLL_INTERVAL
            while time.time() < deadline and self.window.is_alive():
                self.window.process_events()
                time.sleep(0.05)


def main():
    monitor = Monitor()
    monitor.run()


if __name__ == '__main__':
    main()
