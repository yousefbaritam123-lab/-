#!/usr/bin/env python3
"""Maven Toon launcher: python toon.py <command> <project> [options]  (python toon.py --help)"""
import os
import sys

for _s in (sys.stdout, sys.stderr):                    # Arabic in messages must not crash a cp125x console
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if os.path.isdir(os.path.join(HERE, '.deps')):          # optional: pip install --target .deps -r requirements.txt
    sys.path.insert(0, os.path.join(HERE, '.deps'))

from engine.cli import main

if __name__ == '__main__':
    sys.exit(main())
