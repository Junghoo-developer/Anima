"""Project tools package.

This file exists to make the repo-root `tools` directory win module
resolution ahead of `Core/tools.py` when individual Core modules are run
directly (for example `python -m Core.midnight`).
"""
