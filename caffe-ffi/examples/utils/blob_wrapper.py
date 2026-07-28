"""Blob工具模块：提供weakref兼容的包装类和生命周期管理工具。

由于caffe_ffi.Blob是C++ FFI扩展类型（通过TVM FFI导出），不支持Python
weakref机制（未设置Py_TPFLAGS_MANAGED_WEAKREF/tp_weaklistoffset）。
本模块提供三种替代方案来跟踪Blob生命周期：
  1. BlobRef     - 纯Python包装类，支持weakref和销毁回调
  2. tracked_blob - 上下文管理器，with语句自动验证内存释放
  3. blob_snapshot/mem_check - 基于total_allocated_bytes计数器的检测工具
"""

from __future__ import annotations

import sys
import weakref
from contextlib import contextmanager
from typing import Any, Callable, Optional

import caffe_ffi
from caffe_ffi import Blob


class BlobRef:
    """支持weakref的Blob包装类。

    持有底层caffe_ffi.Blob实例，提供透明属性访问（__getattr__代理到底层Blob），
    并支持weakref.ref(callback)在包装对象销毁时收到通知。

    注意：包装对象销毁时底层Blob的Python引用计数归零，会立即触发C++析构。
         回调中请勿访问底层Blob（可能已析构），仅用于通知目的。

    使用示例:
        from utils.blob_wrapper import BlobRef
        import weakref

        def on_destroy(ref):
            print(f"Blob destroyed, was at 0x{ref.data_ptr:016x}")

        br = BlobRef([2, 3, 4, 5])
        br.data_ptr = br._data_ptr  # 附加信息供回调使用
        ref = weakref.ref(br, on_destroy)
        del br  # 触发回调
    """

    __slots__ = ("_blob", "_data_ptr", "_diff_ptr", "_shape", "_label", "__dict__", "__weakref__")

    def __init__(self, shape, label: str = "") -> None:
        self._blob = Blob(shape)
        self._shape = tuple(shape) if not isinstance(shape, (list, tuple)) else tuple(shape)
        try:
            self._data_ptr = self._blob.data_tensor.ctypes.data
            self._diff_ptr = self._blob.diff_tensor.ctypes.data
        except Exception:
            self._data_ptr = 0
            self._diff_ptr = 0
        self._label = label

    def __getattr__(self, name: str) -> Any:
        return getattr(self._blob, name)

    def __repr__(self) -> str:
        nbytes = 0
        try:
            nbytes = self._blob.data_tensor.nbytes + self._blob.diff_tensor.nbytes
        except Exception:
            pass
        return (
            f"BlobRef(shape={self._shape}, data_ptr=0x{self._data_ptr:016x}, "
            f"diff_ptr=0x{self._diff_ptr:016x}, nbytes={nbytes}, "
            f"label={self._label!r})"
        )

    @property
    def data_ptr(self) -> int:
        return self._data_ptr

    @property
    def diff_ptr(self) -> int:
        return self._diff_ptr

    @property
    def nbytes(self) -> int:
        try:
            return self._blob.data_tensor.nbytes + self._blob.diff_tensor.nbytes
        except Exception:
            return 0

    @property
    def shape(self) -> tuple:
        return self._shape

    @property
    def label(self) -> str:
        return self._label


@contextmanager
def tracked_blob(shape, label: str = "blob", verbose: bool = True):
    """上下文管理器：创建Blob并在退出with块时报告内存状态。

    即使with块内抛出异常，也会在finally中检测内存状态并打印日志。

    注意：Python的`with ... as b`会在调用方作用域创建变量b，它持有Blob引用。
    在with块退出时，b仍然存活（引用计数>0），因此C++析构不会立即触发。
    tracked_blob会如实报告这一状态，而不是误报泄漏。要完全验证释放，
    请在with块外执行`del b`（或让函数返回使局部变量b超出作用域）后调用mem_check()。

    Args:
        shape: Blob形状（list/tuple of int）
        label: 标签字符串，用于日志中标识此Blob
        verbose: True=打印日志到stdout

    Yields:
        caffe_ffi.Blob实例

    使用示例（函数作用域内，b随函数返回自动释放）:
        def test():
            with tracked_blob([10, 10], "test1") as b:
                b.data_tensor[:] = 1.0
            # with退出时：blob仍被b引用，打印"still held by caller (expected with 'as b')"
        # 函数返回后b超出作用域，C++析构触发，mem_check("after")返回OK
        mem_check("after_test")
    """
    mem_before = caffe_ffi.total_allocated_bytes()
    b = Blob(shape)
    expected = b.data_tensor.nbytes + b.diff_tensor.nbytes
    dp = b.data_tensor.ctypes.data
    dfp = b.diff_tensor.ctypes.data
    exception_info: Optional[str] = None
    if verbose:
        print(
            f"[TRACK:{label}] created, data_ptr=0x{dp:016x}, "
            f"diff_ptr=0x{dfp:016x}, nbytes={expected}"
        )
    try:
        yield b
    except Exception:
        exc_type, exc_val, _ = sys.exc_info()
        exception_info = f"{exc_type.__name__}: {exc_val}"
        raise
    finally:
        ref_count = sys.getrefcount(b) - 1  # subtract the local reference
        del b
        mem_after = caffe_ffi.total_allocated_bytes()
        if verbose:
            held_by_as = mem_after >= mem_before + expected
            exc_note = f" (exception: {exception_info})" if exception_info else ""
            if mem_after == mem_before:
                print(f"[TRACK:{label}] OK: freed {expected} bytes{exc_note}")
            elif held_by_as:
                remaining = mem_after - mem_before
                print(
                    f"[TRACK:{label}] NOTE: {remaining} bytes still held "
                    f"(expected with 'as b' binding; del b or exit scope to free)"
                    f"{exc_note}"
                )
            else:
                delta = mem_after - mem_before
                if delta < 0:
                    print(
                        f"[TRACK:{label}] WARNING: memory decreased by {-delta} bytes "
                        f"beyond this blob (other blobs freed concurrently){exc_note}"
                    )
                else:
                    print(
                        f"[TRACK:{label}] LEAK? +{delta} bytes "
                        f"(unexpected allocations during block){exc_note}"
                    )


def blob_snapshot(label: str = "", verbose: bool = True) -> int:
    """打印并返回当前全局已分配内存字节数。

    Args:
        label: 标签字符串
        verbose: True=打印到stdout

    Returns:
        当前total_allocated_bytes值
    """
    nbytes = caffe_ffi.total_allocated_bytes()
    if verbose:
        prefix = f"[{label}] " if label else ""
        print(
            f"[MEM-SNAPSHOT] {prefix}total_allocated_bytes={nbytes} "
            f"({nbytes/1024:.2f} KB)"
        )
    return nbytes


def mem_check(label: str = "check", verbose: bool = True) -> bool:
    """检查当前内存分配是否归零（检测泄漏）。

    Args:
        label: 检查点标签
        verbose: True=打印结果

    Returns:
        True=无泄漏（归零），False=有泄漏
    """
    nbytes = caffe_ffi.total_allocated_bytes()
    ok = nbytes == 0
    if verbose:
        status = "OK (zero)" if ok else f"LEAK DETECTED ({nbytes} bytes still allocated)"
        print(f"[MEM-CHECK] {label}: {status}")
    return ok
