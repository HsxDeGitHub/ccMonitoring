"""Determine Claude Code instance state from process data."""

from enum import Enum
import time


class InstanceState(Enum):
    RUNNING = 'running'
    WAITING = 'waiting'
    COMPLETED = 'completed'
    ERROR = 'error'


# CPU threshold: above this means actively working, below means idle/waiting
CPU_ACTIVE_THRESHOLD = 3.0
# How long to keep dead instances visible (seconds)
GHOST_TTL = 30


class StateEngine:
    """Tracks Claude Code instances and determines their current state."""

    def __init__(self):
        # instance_key -> {state, cwd, create_time, exit_time, last_seen}
        self._instances = {}

    def _make_key(self, info):
        """Generate a stable key from pid + cwd + create_time."""
        return f"{info['pid']}:{info['cwd']}:{info.get('create_time', 0)}"

    def update(self, active_processes):
        """Update instance states based on current active processes.

        Args:
            active_processes: list of dicts from ProcessScanner.scan()

        Returns:
            list[dict]: Current instances with state info, sorted by state priority.
            Each dict: {key, cwd, state, cpu_percent, pid}
        """
        now = time.time()
        active_keys = set()

        for proc in active_processes:
            key = self._make_key(proc)
            active_keys.add(key)

            inst = self._instances.get(key, {})
            inst['pid'] = proc['pid']
            inst['cwd'] = proc['cwd']
            inst['cpu_percent'] = proc['cpu_percent']
            inst['last_seen'] = now

            effective_cpu = proc.get('tree_cpu_percent', proc['cpu_percent'])
            if effective_cpu > CPU_ACTIVE_THRESHOLD:
                inst['state'] = InstanceState.RUNNING
            else:
                inst['state'] = InstanceState.WAITING
            self._instances[key] = inst

        # Mark dead instances
        for key, inst in list(self._instances.items()):
            if key not in active_keys:
                if inst.get('state') not in (InstanceState.COMPLETED, InstanceState.ERROR):
                    # Process just died — check exit code
                    pid = inst.get('pid')
                    exit_code = self._check_exit_code(pid)
                    if exit_code is None:
                        inst['state'] = InstanceState.COMPLETED
                    elif exit_code != 0:
                        inst['state'] = InstanceState.ERROR
                    else:
                        inst['state'] = InstanceState.COMPLETED
                    inst['exit_time'] = now

                # Remove ghosts older than TTL
                exit_time = inst.get('exit_time', 0)
                if now - exit_time > GHOST_TTL:
                    del self._instances[key]
                    continue

                self._instances[key] = inst

        return self._get_sorted_list()

    def _check_exit_code(self, pid):
        """Try to get exit code for a pid.

        Returns exit code, or None if the process vanished before
        we could read it. Caller decides default for None.
        """
        try:
            import psutil
            proc = psutil.Process(pid)
            if proc.is_running():
                return None  # still running, caller shouldn't query
            ret = proc.wait(timeout=0)
            return ret if ret is not None else 0
        except psutil.NoSuchProcess:
            return None  # vanished, can't determine
        except Exception:
            return None

    def _get_sorted_list(self):
        """Return instances sorted by state priority: ERROR > WAITING > RUNNING > COMPLETED."""
        priority = {
            InstanceState.ERROR: 0,
            InstanceState.WAITING: 1,
            InstanceState.RUNNING: 2,
            InstanceState.COMPLETED: 3,
        }
        result = []
        for key, inst in self._instances.items():
            result.append({
                'key': key,
                'pid': inst.get('pid', 0),
                'cwd': inst.get('cwd', ''),
                'state': inst.get('state', InstanceState.RUNNING),
                'cpu_percent': inst.get('cpu_percent', 0.0),
            })
        result.sort(key=lambda x: priority.get(x['state'], 99))
        return result
