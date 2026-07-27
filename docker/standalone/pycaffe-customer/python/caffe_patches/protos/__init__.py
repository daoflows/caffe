"""protos package - protobuf generated code for caffe.

This __init__ patches protobuf runtime version check to tolerate version
mismatches between the pre-generated caffe_pb2.py and the installed protobuf
Python package, since we use PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python.
"""
from __future__ import annotations
import warnings as _warnings
try:
    from google.protobuf import runtime_version as _rv
    if not getattr(_rv.ValidateProtobufRuntimeVersion, '_caffe_patched', False):
        _orig = _rv.ValidateProtobufRuntimeVersion
        def _pv(domain, major, minor, micro, suffix, proto_file):
            try:
                return _orig(domain, major, minor, micro, suffix, proto_file)
            except Exception as _e:
                _warnings.warn(
                    f"Protobuf version mismatch for {proto_file}: {_e}. Continuing.",
                    RuntimeWarning, stacklevel=3)
        _pv._caffe_patched = True
        _rv.ValidateProtobufRuntimeVersion = _pv
except Exception:
    pass
