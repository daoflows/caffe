# Caffe Docker 镜像构建 — 最终修复总结

> **日期**: 2026-07-23
> **环境**: WSL2 (Ubuntu-24.04), Docker, Ubuntu 26.04 基础镜像
> **目标**: 为 `caffex/python`(废弃) 和 `python/pycaffe`(主力) 两个模块构建独立 Docker 镜像，确保 pycaffe 测试结果与废弃模块一致

---

## 修复清单

### 1. `caffex/Makefile` — 移除 `boost_system` 链接

**Commit Message:**
```
fix(caffex): remove boost_system from link libraries for Boost 1.90.0

Boost 1.90.0 on Ubuntu 26.04 makes boost_system a header-only library,
so libboost_system.so no longer exists. Remove -lboost_system from
LIBRARIES to fix "cannot find -lboost_system" linker error.

Affected: caffex/Makefile L181
```

**变更:**
```diff
- LIBRARIES += glog gflags protobuf boost_system boost_filesystem m
+ LIBRARIES += glog gflags protobuf boost_filesystem m
```

**根因**: Ubuntu 26.04 的 Boost 1.90.0 将 `boost_system` 改为 header-only 库，`libboost_system.so` 不再存在。

---

### 2. `caffex/python/caffe/_caffe.cpp` — 修复 NumPy segfault

**Commit Message:**
```
fix(caffex): move import_array1() before class registration to fix segfault

NdarrayConverterGenerator::get_pytype() accesses PyArray_Type during
Blob class registration (BOOST_PYTHON_MODULE), but import_array1()
was called at the end of the module init function. On Python 3.14
with NumPy 2.x, this causes a segfault because the NumPy C API is
not initialized when Boost.Python registers the converter.

Move import_array1() to the beginning of BOOST_PYTHON_MODULE so
PyArray_Type is ready before any class registration.

Affected: caffex/python/caffe/_caffe.cpp L377-579
```

**变更:**
```diff
 BOOST_PYTHON_MODULE(_caffe) {
+  // boost python expects a void (missing) return value, while import_array
+  // returns NULL for python3. import_array1() forces a void return value.
+  // Must be called before any class definitions that use NumPy types.
+  import_array1();
+
   // below, we prepend an underscore to methods that will be replaced
   // in Python

   ...

-  // boost python expects a void (missing) return value, while import_array
-  // returns NULL for python3. import_array1() forces a void return value.
-  import_array1();
 }
```

**根因**: `import_array1()` 原在模块末尾调用，但 Blob 类注册时 `NdarrayConverterGenerator::get_pytype()` 需要 `PyArray_Type` 已初始化。

---

### 3. `python/pycaffe/CMakeLists.txt` — 移除 `BOOST_SYSTEM_LIBRARY` 查找

**Commit Message:**
```
fix(pycaffe): remove BOOST_SYSTEM_LIBRARY from CMakeLists.txt

boost_system is header-only in Boost 1.90.0 (Ubuntu 26.04), so
find_library(BOOST_SYSTEM_LIBRARY boost_system) produces a harmless
but noisy "not found" warning. Remove the find_library call and the
entry from _optional_libs since the library is never needed.

Affected: python/pycaffe/CMakeLists.txt L134-136, L202
```

**变更:**
```diff
- find_library(BOOST_SYSTEM_LIBRARY boost_system
-   PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib ...
- )
  find_library(BOOST_THREAD_LIBRARY boost_thread ...

-   BOOST_SYSTEM_LIBRARY BOOST_THREAD_LIBRARY BOOST_FILESYSTEM_LIBRARY
+   BOOST_THREAD_LIBRARY BOOST_FILESYSTEM_LIBRARY
```

---

### 4. `docker/modules/python-module/Dockerfile` — 构建修复

**变更:**
- 移除 `libboost-system-dev` apt 包（`libboost-all-dev` 已包含）
- `make distribute` 容错处理（空 `TOOL_BINS`/`EXAMPLE_BINS` 导致 `cp` 失败）

---

### 5. `docker/modules/pycaffe/Dockerfile` — Python 3.14 适配

**变更:**
- 移除 `python3.10-venv` 安装（Python 3.14 内置 venv 模块）
- 添加 `--break-system-packages` 到所有 `pip install` 命令（PEP 668）
- 添加 `--no-isolation` 到 `python -m build`（避免隔离环境 EXTERNALLY-MANAGED 错误）
- 手动安装构建依赖（scikit-build-core, ninja, cmake, numpy）

---

## 验证结果

| 镜像 | 验证脚本 | 结果 |
|------|---------|------|
| `caffe-cpu:python-module` (5.27 GB) | `verify-python-module.sh` | **6 PASS / 0 FAIL / 1 SKIP** |
| `caffe-cpu:pycaffe` (5.38 GB) | `verify-pycaffe.sh` | **18 PASS / 0 FAIL / 1 SKIP** |
| `caffe-cpu:pycaffe` | `verify-parity.sh` (对标废弃模块) | **11 PASS / 0 FAIL / 0 SKIP** |

**对标验证覆盖**: Net 创建/前向/反向/保存/加载、Level/Stage 过滤、Solver、coord_map、draw、io、API 一致性

---

## 生产标准

| 标准 | python-module | pycaffe |
|------|:---:|:---:|
| 多阶段构建 | base-system → base-builder → builder → runtime | FROM python-module |
| 非 root 用户 | builder (UID 1000) | builder (UID 1000) |
| HEALTHCHECK | `import caffe; from caffeproto import caffe_pb2` | `import pycaffe; print(version)` |
| `.dockerignore` | 排除 .git/、__pycache__/、build/、*.whl | 继承 |
| 阿里云镜像源 | apt + pip | 继承 |

---

## 受影响文件

| 文件 | 变更类型 | 关联 Commit |
|------|----------|------------|
| `caffex/Makefile` | 修改 | #1: 移除 boost_system |
| `caffex/python/caffe/_caffe.cpp` | 修改 | #2: 修复 segfault |
| `python/pycaffe/CMakeLists.txt` | 修改 | #3: 移除 BOOST_SYSTEM_LIBRARY |
| `docker/modules/python-module/Dockerfile` | 修改 | #4: 构建修复 |
| `docker/modules/pycaffe/Dockerfile` | 修改 | #5: Python 3.14 适配 |
| `.dockerignore` | 新增 | 构建上下文优化 |
| `docker/modules/` | 新增 | 模块构建基础设施 |
| `.trae/specs/docker-images-for-modules/spec.md` | 修改 | 最终实现状态 |
| `.trae/specs/docker-images-for-modules/test-report-20260723.md` | 新增 | 详细测试报告 |
| `.trae/specs/docker-images-for-modules/fix-summary-20260723.md` | 新增 | 本文件 |

---

## 已知限制

1. **TVM 不可用**: `operators.layers.L2Norm` 需 TVM Relax 运行时
2. **pydotplus 未安装**: `pycaffe.draw` 模块需要 pydotplus + graphviz（可选依赖）
3. **镜像大小**: 5.27-5.38 GB，包含完整编译工具链和 OpenCV 等大型依赖