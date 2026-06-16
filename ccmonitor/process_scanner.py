"""Scan system for running Claude Code processes."""

import logging
import os
import psutil

logger = logging.getLogger(__name__)


class ProcessScanner:
    """Finds and tracks Claude Code processes on the system."""

    @staticmethod
    def _get_tree_cpu(proc):
        """Sum CPU percent of all descendants of proc (not including proc itself)."""
        total = 0.0
        try:
            for child in proc.children(recursive=True):
                try:
                    total += child.cpu_percent(interval=0.05) or 0.0
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        return total

    @staticmethod
    def _basename(cmdline):
        """Extract the process basename from command line (first token without path)."""
        if not cmdline:
            return ''
        return os.path.basename(cmdline[0])

    def scan(self):
        """Scan for claude processes and return list of process info dicts.

        Returns:
            list[dict]: Each dict has keys: pid, cwd, cpu_percent, tree_cpu_percent, create_time.
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

                # Skip subagent processes: if parent is also a claude process,
                # this is a child/subagent, not a top-level session.
                # Only skip when the parent's binary basename contains 'claude'
                # — a parent that merely has '.claude' in a path is not a claude process.
                try:
                    parent = proc.parent()
                    if parent:
                        parent_cmdline = ' '.join(parent.cmdline())
                        parent_base = self._basename(parent.cmdline())
                        if 'claude' in parent_base.lower():
                            logger.debug(
                                'scan: skip subagent pid=%d cmd=%s parent_pid=%d parent_cmd=%s',
                                info['pid'], cmdline_str[:120],
                                parent.pid, parent_cmdline[:120],
                            )
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

                # On Unix, only include processes attached to a terminal
                # or whose binary basename is exactly "claude" — catches
                # Claude Code instances that psutil cannot associate with
                # a TTY (e.g. IDE terminals, some launchers).
                if hasattr(proc, 'terminal'):
                    if not proc.terminal():
                        proc_base = self._basename(info['cmdline'])
                        if 'claude' not in proc_base.lower():
                            logger.debug(
                                'scan: skip no-tty non-claude pid=%d cmd=%s',
                                info['pid'], cmdline_str[:120],
                            )
                            continue

                # Get accurate CPU usage (blocks 0.25s per process)
                cpu_pct = proc.cpu_percent(interval=0.25) or 0.0
                tree_cpu = cpu_pct + self._get_tree_cpu(proc)

                instances.append({
                    'pid': info['pid'],
                    'cwd': info['cwd'] or '',
                    'cpu_percent': cpu_pct,
                    'tree_cpu_percent': tree_cpu,
                    'create_time': info['create_time'] or 0,
                })

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return instances
