"""caffe-ffi 三层日志配置工具

提供 Python/FFI/C++ 三层日志的统一配置入口，方便调试内存问题时快速启用。

使用方法:
    from config import setup_debug, setup_quiet, setup_memory_trace
    import caffe_ffi
    from caffe_ffi import Blob
    import numpy as np

    setup_debug()                      # 启用所有三层 DEBUG 日志（控制台输出）
    # setup_debug(log_file="mem.log") # 同时写入文件
    # setup_memory_trace()             # 最细粒度追踪（含 TRACE）
    # setup_quiet()                    # 恢复默认 WARN 级别

    b = Blob([2, 3, 4, 5])
    b.data_tensor[:] = np.random.randn(2, 3, 4, 5).astype(np.float32)
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

import caffe_ffi
from caffe_ffi import (
    LOG_LEVEL_TRACE,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
)

_PY_LOGGER_NAME = "caffe_ffi"
_PY_LOGGER = logging.getLogger(_PY_LOGGER_NAME)

_CONFIGURED_HANDLERS: list[logging.Handler] = []


def _clear_handlers() -> None:
    for h in _CONFIGURED_HANDLERS:
        _PY_LOGGER.removeHandler(h)
        h.close()
    _CONFIGURED_HANDLERS.clear()


def _add_handler(handler: logging.Handler, level: int, fmt: str, datefmt: str) -> None:
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    _PY_LOGGER.addHandler(handler)
    _CONFIGURED_HANDLERS.append(handler)


def setup_debug(
    level: int = LOG_LEVEL_DEBUG,
    log_file: Optional[str] = None,
    python_level: int = logging.DEBUG,
    fmt: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt: str = "%H:%M:%S",
) -> None:
    """启用三层调试日志。

    同时开启 Python 层(logging 模块)和 C++ 原生层的 DEBUG/Trace 输出。

    Args:
        level: C++ 原生日志级别，默认 LOG_LEVEL_DEBUG(1)。
               使用 LOG_LEVEL_TRACE(0) 获取最细粒度输出。
        log_file: 可选文件路径，日志将同时写入该文件。
        python_level: Python logging 模块级别，默认 logging.DEBUG。
        fmt: 日志格式字符串。
        datefmt: 时间格式字符串。
    """
    _clear_handlers()

    _PY_LOGGER.setLevel(python_level)
    if not _PY_LOGGER.handlers or not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in _PY_LOGGER.handlers
    ):
        _add_handler(logging.StreamHandler(sys.stdout), python_level, fmt, datefmt)

    if log_file:
        _add_handler(logging.FileHandler(log_file, encoding="utf-8"), python_level, fmt, datefmt)

    caffe_ffi.set_log_level(level)
    _PY_LOGGER.debug(
        "Debug logging enabled (C++ level=%d, Python level=%d, file=%s)",
        level, python_level, log_file,
    )


def setup_memory_trace(log_file: Optional[str] = None) -> None:
    """启用最细粒度内存追踪日志（TRACE级别）。

    输出所有内存分配/释放/访问细节，用于排查内存泄漏、野指针等问题。
    """
    setup_debug(level=LOG_LEVEL_TRACE, log_file=log_file)
    _PY_LOGGER.debug("Memory trace mode enabled (TRACE level)")


def setup_quiet() -> None:
    """关闭调试日志，恢复默认 WARN 级别。

    Python 和 C++ 层均恢复到 WARNING 级别，移除本工具添加的 handler。
    """
    _clear_handlers()
    _PY_LOGGER.setLevel(logging.WARNING)
    caffe_ffi.set_log_level(LOG_LEVEL_WARN)


def setup_file_logging(
    log_file: str,
    level: int = LOG_LEVEL_DEBUG,
    append: bool = False,
) -> None:
    """仅启用文件日志（不输出到控制台）。

    适合长时间运行时后台记录，避免控制台输出过多。

    Args:
        log_file: 日志文件路径。
        level: C++ 日志级别，默认 DEBUG。
        append: True=追加写入，False=覆盖（默认覆盖）。
    """
    _clear_handlers()
    _PY_LOGGER.setLevel(logging.DEBUG)
    mode = "a" if append else "w"
    fh = logging.FileHandler(log_file, mode=mode, encoding="utf-8")
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    _add_handler(fh, logging.DEBUG, fmt, "%H:%M:%S")
    caffe_ffi.set_log_level(level)
    _PY_LOGGER.debug("File logging enabled -> %s (append=%s)", log_file, append)


def memory_snapshot(label: str = "") -> int:
    """打印当前 C++ 层全局已分配内存字节数，返回该值。

    用于检查内存是否在正确时机释放：在操作前后分别调用，对比差值。

    Args:
        label: 可选标签，日志中显示。

    Returns:
        当前全局已分配字节数。
    """
    nbytes = caffe_ffi.total_allocated_bytes()
    prefix = f"[{label}] " if label else ""
    _PY_LOGGER.info("%sMemory snapshot: total_allocated_bytes=%d (%.2f KB)",
                    prefix, nbytes, nbytes / 1024.0)
    print(f"[MEM-SNAPSHOT] {prefix}total_allocated_bytes={nbytes} ({nbytes/1024:.2f} KB)")
    return nbytes


def check_memory_baseline(label: str = "check") -> bool:
    """检查当前内存分配是否归零（用于检测泄漏）。

    在所有 Blob 释放后调用，如果返回 False 说明存在内存泄漏。

    Args:
        label: 检查点标签。

    Returns:
        True 表示内存已归零（无泄漏），False 表示存在泄漏。
    """
    nbytes = caffe_ffi.total_allocated_bytes()
    ok = nbytes == 0
    status = "OK (zero)" if ok else f"LEAK DETECTED ({nbytes} bytes still allocated)"
    print(f"[MEM-CHECK] {label}: {status}")
    _PY_LOGGER.info("Memory check '%s': %s", label, status)
    return ok


if __name__ == "__main__":
    import gc
    import numpy as np
    from caffe_ffi import Blob

    print("=== config.py self-test ===\n")

    print("--- Test 1: setup_debug() ---")
    setup_debug()
    b1 = Blob([2, 3, 4, 5])
    b1.data_tensor[:] = 1.0
    memory_snapshot("after_create_b1")
    del b1
    gc.collect()
    check_memory_baseline("after_del_b1")
    print()

    print("--- Test 2: setup_quiet() ---")
    setup_quiet()
    b2 = Blob([10])
    b2.data_tensor[:] = 2.0
    print(f"b2[0] = {float(b2.data_tensor[0])}")
    del b2
    gc.collect()
    baseline = check_memory_baseline("quiet_mode")
    print()

    print("--- Test 3: memory_snapshot multi-blob ---")
    setup_debug()
    blobs = [Blob([4, 4]) for _ in range(3)]
    for i, b in enumerate(blobs):
        b.data_tensor[:] = i
    mem_after = memory_snapshot("3_blobs_alive")
    assert mem_after > 0, "Should have allocated memory"
    del blobs
    gc.collect()
    check_memory_baseline("after_del_all")
    setup_quiet()
    print()

    print("=== All self-tests passed ===")
