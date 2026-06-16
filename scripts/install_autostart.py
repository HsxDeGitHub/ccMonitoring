#!/usr/bin/env python3
"""Install or remove auto-start LaunchAgent for CC Monitor."""

import os
import sys
import shutil

PLIST_NAME = 'com.ccmonitor.plist'
PLIST_DIR = os.path.expanduser('~/Library/LaunchAgents')
PLIST_PATH = os.path.join(PLIST_DIR, PLIST_NAME)
SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'ccmonitor', 'monitor.py'))


def install():
    os.makedirs(PLIST_DIR, exist_ok=True)
    template = os.path.join(os.path.dirname(__file__), PLIST_NAME)
    with open(template) as f:
        content = f.read()
    content = content.replace('SCRIPT_PATH', SCRIPT_PATH)
    with open(PLIST_PATH, 'w') as f:
        f.write(content)
    print(f'Installed: {PLIST_PATH}')


def uninstall():
    if os.path.exists(PLIST_PATH):
        os.remove(PLIST_PATH)
        print(f'Removed: {PLIST_PATH}')
    else:
        print('Not installed.')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--uninstall':
        uninstall()
    else:
        install()
