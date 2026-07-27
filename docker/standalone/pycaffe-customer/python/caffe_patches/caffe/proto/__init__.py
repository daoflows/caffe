"""caffe.proto compatibility shim."""
from __future__ import annotations

import warnings


def _ensure_protobuf_patch():
    try:
        from google.protobuf import runtime_version as _rv
        if not getattr(_rv.ValidateProtobufRuntimeVersion, '_caffe_patched', False):
            _original = _rv.ValidateProtobufRuntimeVersion

            def _patched(domain, major, minor, micro, suffix, proto_file):
                try:
                    return _original(domain, major, minor, micro, suffix, proto_file)
                except Exception as e:
                    warnings.warn(
                        f"Protobuf version mismatch for {proto_file}: {e}. "
                        "Attempting to continue.",
                        RuntimeWarning,
                        stacklevel=3,
                    )

            _patched._caffe_patched = True
            _rv.ValidateProtobufRuntimeVersion = _patched
    except ImportError:
        pass
    except Exception:
        pass


_ensure_protobuf_patch()

from . import caffe_pb2
