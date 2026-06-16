"""Scan system for running Claude Code processes."""

import psutil


class ProcessScanner:
    """Finds and tracks Claude Code processes on the system."""

    def __init__(self):
        self._proc_cache = {}  # pid -> psutil.Process (for cpu_percent tracking)

    def scan(self):
        """Scan for claude processes and return list of process info dicts.

        Returns:
            list[dict]: Each dict has keys: pid, cwd, cpu_percent, create_time.
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
