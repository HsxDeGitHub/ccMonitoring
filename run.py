#!/usr/bin/env python3
"""CC Monitor — launch entry point."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ccmonitor.monitor import main

if __name__ == '__main__':
    main()
