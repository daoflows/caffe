#!/usr/bin/env python
"""PyCaffe Verification Script

Verifies that pycaffe is correctly installed and functional.
Run this script after installing the pycaffe wheel.
"""

import sys


def check_import():
    """Verify pycaffe can be imported."""
    try:
        import pycaffe
        print("[PASS] import pycaffe")
        return True
    except ImportError as e:
        print(f"[FAIL] import pycaffe: {e}")
        return False


def check_version():
    """Verify pycaffe version is accessible."""
    try:
        import pycaffe
        version = pycaffe.__version__
        print(f"[PASS] pycaffe.__version__ = {version}")
        return True
    except Exception as e:
        print(f"[FAIL] pycaffe.__version__: {e}")