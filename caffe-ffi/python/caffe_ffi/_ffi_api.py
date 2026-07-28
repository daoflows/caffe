from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _find_lib_path() -> Optional[Path]:
    base_dir = Path(__file__).resolve().parent.parent.parent
    
    if sys.platform == "win32":
        lib_names = [
            "_caffe_ffi.dll",
            "_caffe_ffi.pyd",
            "_caffe_ffi.cp314-win_amd64.pyd",
        ]
    elif sys.platform == "darwin":
        lib_names = [
            "lib_caffe_ffi.dylib",
            "_caffe_ffi.so",
            "_caffe_ffi.cpython-314-darwin.so",
        ]
    else:
        lib_names = [
            "lib_caffe_ffi.so",
            "_caffe_ffi.so",
            "_caffe_ffi.cpython-314-x86_64-linux-gnu.so",
        ]
    
    search_dirs = [
        base_dir,
        base_dir / "build",
        base_dir / "build-cmake",
        base_dir / "build-wheel",
        base_dir / "build" / "Release",
        base_dir / "build-cmake" / "Release",
        base_dir / "build-wheel" / "Release",
        base_dir / "build" / "lib",
        base_dir / "build-cmake" / "lib",
        Path(__file__).parent,
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            for lib_name in lib_names:
                lib_path = search_dir / lib_name
                if lib_path.exists():
                    return lib_path
    
    return None


_lib_path = _find_lib_path()
_ffi_available = False


def _try_init_tvm_ffi():
    global _ffi_available
    
    try:
        import tvm_ffi
        
        if _lib_path is not None:
            lib_dir = _lib_path.parent
            if sys.platform == "win32":
                try:
                    os.add_dll_directory(str(lib_dir))
                except (OSError, AttributeError):
                    pass
            tvm_ffi.load_module(str(_lib_path))
        
        _ffi_available = True
        return True
    except ImportError:
        return False
    except Exception:
        return False


_try_init_tvm_ffi()


class _FFIRegistry:
    
    def __init__(self):
        self._funcs: Dict[str, Any] = {}
        self._types: Dict[str, type] = {}
        self._Object = None
        self._register_object = None
        self._get_global_func = None
        
        if _ffi_available:
            try:
                import tvm_ffi
                self._Object = tvm_ffi.Object
                self._register_object = tvm_ffi.register_object
                self._get_global_func = tvm_ffi.get_global_func
            except ImportError:
                pass
    
    @property
    def available(self) -> bool:
        return _ffi_available
    
    @property
    def Object(self):
        if self._Object is None:
            raise RuntimeError(
                "tvm_ffi not available. C++ extension not loaded. "
                "Please build caffe-ffi first."
            )
        return self._Object
    
    def get_global_func(self, name: str) -> Any:
        if name not in self._funcs:
            if self._get_global_func is not None:
                self._funcs[name] = self._get_global_func(name, allow_missing=True)
            else:
                self._funcs[name] = None
        return self._funcs[name]
    
    def register_object(self, type_key: str, cls: type):
        if self._register_object is not None:
            self._register_object(type_key)(cls)
        self._types[type_key] = cls


registry = _FFIRegistry()


def get_global_func(name: str) -> Any:
    return registry.get_global_func(name)


def is_available() -> bool:
    return registry.available


def lib_path() -> Optional[Path]:
    return _lib_path
