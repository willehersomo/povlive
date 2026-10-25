#!/usr/bin/env python3
"""PovLive — lançador. O código fica em povlive_app/.

Uso:  python3 povlive.py [arquivo.pov ...]
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from povlive_app.janela import main

if __name__ == "__main__":
    main()
