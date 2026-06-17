"""Convenience launcher.

Usage:
    python run.py

Place this file in the SAME directory as the ``obsyde/`` package folder.
Equivalent to running ``python -m obsyde``.

Set OBSYDE_DEBUG=1 to keep Qt / FFmpeg diagnostic output visible.
"""
import os, sys

if not os.environ.get("OBSYDE_DEBUG"):
    os.environ.setdefault(
        "QT_LOGGING_RULES",
        "*.debug=false;*.info=false;*.warning=false;qt.multimedia.*=false;qt.*.warning=false",
    )
    try:
        _fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(_fd, 2)
    except Exception:
        pass

from obsyde.app import main

if __name__ == "__main__":
    main()
