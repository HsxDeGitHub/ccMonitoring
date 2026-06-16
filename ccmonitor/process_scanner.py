"""Scan system for running Claude Code processes."""

import psutil


class ProcessScanner:
    """Finds and tracks Claude Code processes on the system."""

    def scan(self):
        """Scan for claude processes and return list of process info dicts.

        Returns:
            list[dict]: Each dict has keys: pid, cwd, cpu_percent, create_time.
        """
        instances = []

        for proc in psutil.process_iter(['pid', 'cmdline', 'cwd', 'create_time']):
            try:
                info = proc.info
                if not info['cmdline']:
                    continue

                cmdline_str = ' '.join(info['cmdline'])
                if 'claude' not in cmdline_str.lower():
                    continue
                if 'monitor.py' in cmdline_str:
                    continue

                # On Unix, only include processes attached to a terminal.
                # terminal() is Unix-only; Windows skips this check.
                if hasattr(proc, 'terminal'):
                    if not proc.terminal():
                        continue

                # Get accurate CPU usage (blocks 0.1s per process)
                cpu_pct = proc.cpu_percent(interval=0.25) or 0.0

                instances.append({
                    'pid': info['pid'],
                    'cwd': info['cwd'] or '',
                    'cpu_percent': cpu_pct,
                    'create_time': info['create_time'] or 0,
                })

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return instances
