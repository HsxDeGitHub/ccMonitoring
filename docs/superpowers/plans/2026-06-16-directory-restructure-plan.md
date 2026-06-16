# Directory Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the ccMonitoring project from a flat root-directory layout to a standard `src/` layout.

**Architecture:** Move all Python sources into `src/ccmonitor/` package, auxiliary scripts into `scripts/`, docs into `docs/`. Update inter-module imports from flat to package-qualified.

**Tech Stack:** Python 3.12, git

---

### Task 1: Create directory structure

**Files:**
- Create: `src/ccmonitor/__init__.py`
- Create: `scripts/.gitkeep`

- [ ] **Step 1: Create directories and `__init__.py`**

```bash
mkdir -p src/ccmonitor scripts
touch src/ccmonitor/__init__.py scripts/.gitkeep
```

- [ ] **Step 2: Move Python source files into `src/ccmonitor/`**

```bash
git mv monitor.py src/ccmonitor/monitor.py
git mv overlay_window.py src/ccmonitor/overlay_window.py
git mv process_scanner.py src/ccmonitor/process_scanner.py
git mv state_engine.py src/ccmonitor/state_engine.py
git mv tray_icon.py src/ccmonitor/tray_icon.py
git mv settings.py src/ccmonitor/settings.py
```

- [ ] **Step 3: Move auxiliary files**

```bash
git mv install_autostart.py scripts/install_autostart.py
git mv com.ccmonitor.plist scripts/com.ccmonitor.plist
git mv prompt.md docs/prompt.md
```

- [ ] **Step 4: Verify directory structure looks correct**

```bash
find . -not -path './.git/*' -not -path './__pycache__/*' -not -name '.DS_Store' | sort
```

Expected output matches the target structure from the design spec.

---

### Task 2: Update imports in moved source files

**Files:**
- Modify: `src/ccmonitor/monitor.py:10-14`
- Modify: `src/ccmonitor/overlay_window.py:9-10`
- Modify: `src/ccmonitor/tray_icon.py:7`

- [ ] **Step 1: Update imports in `monitor.py`**

In `src/ccmonitor/monitor.py`, replace lines 10-14:

```python
# old — flat imports
from process_scanner import ProcessScanner
from state_engine import StateEngine
from overlay_window import OverlayWindow
from tray_icon import TrayIcon
from settings import AppSettings
```

with:

```python
from ccmonitor.process_scanner import ProcessScanner
from ccmonitor.state_engine import StateEngine
from ccmonitor.overlay_window import OverlayWindow
from ccmonitor.tray_icon import TrayIcon
from ccmonitor.settings import AppSettings
```

- [ ] **Step 2: Update imports in `overlay_window.py`**

In `src/ccmonitor/overlay_window.py`, replace lines 9-10:

```python
# old
from state_engine import InstanceState
from settings import AppSettings
```

with:

```python
from ccmonitor.state_engine import InstanceState
from ccmonitor.settings import AppSettings
```

- [ ] **Step 3: Update import in `tray_icon.py`**

In `src/ccmonitor/tray_icon.py`, replace line 7:

```python
# old
from state_engine import InstanceState
```

with:

```python
from ccmonitor.state_engine import InstanceState
```

- [ ] **Step 4: Verify no old flat imports remain**

```bash
grep -rn "from process_scanner\|from state_engine\|from overlay_window\|from tray_icon\|from settings" src/ccmonitor/
```

Expected: empty output (no matches).

---

### Task 3: Update `.gitignore`

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Update `.gitignore` to cover new paths**

Add `src/ccmonitor/__pycache__/` to `.gitignore`:

```
# current content
__pycache__/
*.pyc
*.pyo
.DS_Store

# add
src/ccmonitor/__pycache__/
```

Note: The existing `__pycache__/` pattern already covers any `__pycache__` directory at any level. Since `__pycache__/` is already there, the new path is already covered. Verify this is the case — if so, no change needed.

- [ ] **Step 2: Verify `.gitignore` coverage**

```bash
cat .gitignore
```

Confirm `__pycache__/` is listed (it matches recursively).

---

### Task 4: Verify the project still works

**Files:** None

- [ ] **Step 1: Run Python import check from project root**

```bash
cd /Users/huangshengxue/code/ai/ccMonitoring && python -c "import sys; sys.path.insert(0, 'src'); from ccmonitor.state_engine import StateEngine; from ccmonitor.process_scanner import ProcessScanner; from ccmonitor.settings import AppSettings; print('All imports OK')"
```

Expected: `All imports OK`

- [ ] **Step 2: Dry-run `monitor.py` import check**

```bash
cd /Users/huangshengxue/code/ai/ccMonitoring && PYTHONPATH=src python -c "from ccmonitor.monitor import Monitor; print('Monitor import OK')"
```

Expected: `Monitor import OK` (no GUI needed, just import check).

---

### Task 5: Commit the restructuring

**Files:** All changed files

- [ ] **Step 1: Review the staged changes**

```bash
git status
git diff --staged --stat
```

- [ ] **Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
refactor: restructure project to src/ layout

Move source files to src/ccmonitor/, scripts to scripts/,
prompt.md to docs/. Update imports to use package-qualified paths.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```
