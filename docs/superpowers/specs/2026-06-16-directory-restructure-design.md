# Directory Restructure Design

## Goal

Reorganize the ccMonitoring project from a flat root-directory layout to a standard `src/` layout so the project structure follows Python conventions.

## Target Structure

```
ccMonitoring/
├── src/
│   └── ccmonitor/
│       ├── __init__.py
│       ├── monitor.py
│       ├── overlay_window.py
│       ├── process_scanner.py
│       ├── state_engine.py
│       ├── tray_icon.py
│       └── settings.py
├── scripts/
│   ├── install_autostart.py
│   └── com.ccmonitor.plist
├── docs/
│   ├── prompt.md
│   └── superpowers/
│       ├── plans/
│       └── specs/
├── requirements.txt
└── .gitignore
```

## Changes

1. **Create `src/ccmonitor/` package** — move all `.py` source files into it, add `__init__.py`.
2. **Create `scripts/`** — move `install_autostart.py` and `com.ccmonitor.plist` into it.
3. **Move `prompt.md`** from root to `docs/`.
4. **Update imports** — change flat imports (`from process_scanner import ...`) to package imports (`from ccmonitor.process_scanner import ...`) in `monitor.py` and any cross-module imports.
5. **Update `.gitignore`** — ensure `src/ccmonitor/__pycache__/` is covered.

## Not changing

- `requirements.txt` stays at root.
- `docs/superpowers/` keeps its existing structure.
