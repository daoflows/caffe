#!/usr/bin/env python
"""PyCaffe End-to-End Inference Test

Verifies that pycaffe can load a network, run forward pass, and produce
correct output shapes. Uses LeNet (MNIST) as the reference network.

Usage:
    python test_inference.py
"""

import sys
import os
import numpy as np


# --- Test Configuration ---
# LeNet deploy prototxt (Input layer, no data layer — suitable for inference)
LENET_DEPLOY_PROTOTXT = os.path.join(os.path.dirname(__file__), "..", "pycaffe", "lenet_deploy.prototxt")


def test_import():
    """Test 1: Import pycaffe and verify core API availability."""
    print("=" * 60)
    print("Test 1: Import & Core API")
    print("=" * 60)

    import pycaffe
    print(f"  [OK] pycaffe imported successfully")
    print(f"  [OK] pycaffe.__version__ = {pycaffe.__version__}")