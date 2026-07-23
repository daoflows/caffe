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
        return False


def check_net():
    """Verify Net class is available."""
    try:
        from pycaffe import Net
        print("[PASS] pycaffe.Net is available")
        return True
    except Exception as e:
        print(f"[FAIL] pycaffe.Net: {e}")
        return False


def check_solvers():
    """Verify Solver classes are available."""
    try:
        from pycaffe import SGDSolver, AdamSolver
        print("[PASS] pycaffe.SGDSolver is available")
        print("[PASS] pycaffe.AdamSolver is available")
        return True
    except Exception as e:
        print(f"[FAIL] pycaffe solvers: {e}")
        return False


def check_cpu_mode():
    """Verify set_mode_cpu() works."""
    try:
        import pycaffe
        pycaffe.set_mode_cpu()
        print("[PASS] pycaffe.set_mode_cpu()")
        return True
    except Exception as e:
        print(f"[FAIL] pycaffe.set_mode_cpu(): {e}")
        return False


def check_classifier():
    """Verify Classifier is available."""
    try:
        from pycaffe import Classifier
        print("[PASS] pycaffe.Classifier is available")
        return True
    except Exception as e:
        print(f"[FAIL] pycaffe.Classifier: {e}")
        return False


def check_io():
    """Verify io module is available."""
    try:
        from pycaffe import io
        print("[PASS] pycaffe.io is available")
        # Check Transformer
        transformer = io.Transformer({"data": (1, 3, 224, 224)})
        print("[PASS] pycaffe.io.Transformer can be instantiated")
        return True
    except Exception as e:
        print(f"[FAIL] pycaffe.io: {e}")
        return False


def check_proto():
    """Verify protobuf definitions are available."""
    try:
        from pycaffe.proto.caffe_pb2 import TRAIN, TEST
        print(f"[PASS] pycaffe.proto.caffe_pb2 (TRAIN={TRAIN}, TEST={TEST})")
        return True
    except Exception as e:
        print(f"[FAIL] pycaffe.proto.caffe_pb2: {e}")
        return False


def check_net_spec():
    """Verify net_spec module is available."""
    try:
        from pycaffe.net_spec import layers, params, NetSpec, to_proto
        print("[PASS] pycaffe.net_spec (layers, params, NetSpec, to_proto)")
        return True
    except Exception as e:
        print(f"[FAIL] pycaffe.net_spec: {e}")
        return False


def main():
    print("=" * 60)
    print("PyCaffe Verification")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print()

    results = {}

    checks = [
        ("import", check_import),
        ("version", check_version),
        ("Net", check_net),
        ("Solvers", check_solvers),
        ("set_mode_cpu", check_cpu_mode),
        ("Classifier", check_classifier),
        ("io/Transformer", check_io),
        ("proto/caffe_pb2", check_proto),
        ("net_spec", check_net_spec),
    ]

    for name, check_fn in checks:
        results[name] = check_fn()

    print()
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed")

    if passed == total:
        print("ALL CHECKS PASSED!")
        return 0
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"Failed checks: {', '.join(failed)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())