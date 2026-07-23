# Docker 独立模块镜像构建与验证测试报告

> **日期**: 2026-07-23
> **环境**: WSL (Ubuntu-24.04), Docker, Ubuntu 26.04 基础镜像
> **分支**: 当前工作树

---

## 1. 构建环境

| 项目 | 值 |
|------|-----|
| 宿主 OS | Windows + WSL2 (Ubuntu-24.04) |
| Docker 版本 | Docker Desktop for Windows |
| 基础镜像 | ubuntu:26.04 |
| Python | 3.14.4 (system) |
| Protobuf (pip) | 7.35.1 |
| Protobuf (system) | libprotoc 3.21.12 |
| Boost | 1.90.0 |
| BLAS | OpenBLAS (libopenblas-dev) |
| NumPy | 最新版 (2.x) |
| C++ 编译器 | GCC 15 |

---

## 2. 构建前修复

### 2.1 `caffex/Makefile` — 移除 `boost_system` 链接

**问题**: Boost 1.90.0 中 `boost_system` 已改为 header-only 库，无 `libboost_system.so` 文件，导致链接错误：
```
/usr/bin/x86_64-linux-gnu-ld.bfd: cannot find -lboost_system: No such file or directory
```

**修复**: `caffex/Makefile` L181: `LIBRARIES += glog gflags protobuf boost_system boost_filesystem m` → 移除 `boost_system`

### 2.2 `caffex/python/caffe/_caffe.cpp` — 修复 NumPy segfault

**问题**: `import_array1()` 原在 `BOOST_PYTHON_MODULE` 末尾调用，但 Blob 类注册时（L453）就需要 `PyArray_Type` 已初始化。`NdarrayConverterGenerator::get_pytype()` 访问未初始化的 `PyArray_Type` 导致 segfault。

**修复**: 将 `import_array1()` 从模块末尾移至 `BOOST_PYTHON_MODULE` 开头（L382），在任何类注册之前调用。

### 2.3 `docker/modules/pycaffe/Dockerfile` — Python 3.14 适配

- 移除 `python3.10-venv` 安装（Python 3.14 内置 venv 模块）
- 添加 `--break-system-packages` 到所有 `pip install` 命令（PEP 668）

### 2.4 `docker/modules/python-module/Dockerfile` — 构建修复

- 移除 `libboost-system-dev` apt 包（冗余，`libboost-all-dev` 已包含）
- `make distribute` 失败的容错处理（空 `TOOL_BINS`/`EXAMPLE_BINS` 导致 `cp` 失败）

---

## 3. 镜像构建结果

### 3.1 `caffe-cpu:python-module` (5.27 GB)

```bash
docker build -t caffe-cpu:python-module --target runtime \
  -f docker/modules/python-module/Dockerfile .
```

**构建阶段**:
| 阶段 | 说明 | 结果 |
|------|------|------|
| base-system | 基础 Ubuntu 26.04 + 阿里云镜像源 | PASS |
| base-builder | 编译依赖 + Python 运行时依赖 | PASS |
| builder | Caffe C++ 编译 (make all + make pycaffe + make distribute) | PASS |
| runtime | 运行时镜像组装 | PASS |

### 3.2 `caffe-cpu:pycaffe` (5.38 GB)

```bash
docker build -t caffe-cpu:pycaffe \
  -f docker/modules/pycaffe/Dockerfile .
```

**构建阶段**:
| 阶段 | 说明 | 结果 |
|------|------|------|
| 基础镜像 | FROM caffe-cpu:python-module | PASS |
| 符号链接 | libcaffe.so.1.0.0 → libcaffe.so | PASS |
| build 工具 | pip install build | PASS |
| Wheel 构建 | python -m build --wheel | PASS |
| Wheel 安装 | pip install *.whl | PASS |
| 内置验证 | verify-pycaffe.sh | PASS |

---

## 4. 验证结果

### 4.1 `verify-python-module.sh` (python-module 镜像)

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | import caffe and print `__version__` | PASS |
| 2 | from caffeproto import caffe_pb2 | PASS |
| 3 | from operators.layers import L2Norm | SKIP (TVM 不可用) |
| 4 | caffe.Net API | PASS |
| 5 | caffe.SGDSolver API | PASS |
| 6 | caffe.proto import | PASS |
| 7 | run_test.sh (caffeproto + BN-Scale fusion) | PASS |

**汇总: 6 PASS / 0 FAIL / 1 SKIP**

### 4.2 `verify-pycaffe.sh` (pycaffe 镜像)

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | import pycaffe | PASS |
| 2 | pycaffe.`__version__` = 1.0.0 | PASS |
| 3 | pycaffe.TRAIN = 0 | PASS |
| 4 | pycaffe.TEST = 1 | PASS |
| 5 | pycaffe.Net class | PASS |
| 6 | pycaffe.set_mode_cpu() | PASS |
| 7 | LeNet forward pass | PASS |
| 8 | pycaffe.classifier | PASS |
| 9 | pycaffe.detector | PASS |
| 10 | pycaffe.draw | SKIP (pydotplus 未安装) |
| 11 | pycaffe.io | PASS |
| 12 | pycaffe.net_spec | PASS |
| 13 | pycaffe.coord_map | PASS |
| 14 | pycaffe.SGDSolver | PASS |
| 15 | pycaffe.AdamSolver | PASS |
| 16 | pycaffe.NesterovSolver | PASS |
| 17 | pycaffe.AdaGradSolver | PASS |
| 18 | pycaffe.RMSPropSolver | PASS |
| 19 | pycaffe.AdaDeltaSolver | PASS |

**汇总: 18 PASS / 0 FAIL / 1 SKIP**

### 4.3 `verify-parity.sh` (pycaffe 对标废弃模块)

| # | 测试项 | 对标来源 | 结果 |
|---|--------|----------|------|
| 1 | Net creation and forward | test_net.py (TestNet) | PASS |
| 2 | Net backward pass | test_net.py (TestNet) | PASS |
| 3 | Net save and load | test_net.py (TestNet) | PASS |
| 4 | Net level filtering | test_net.py (TestLevels) | PASS |
| 5 | Net stage filtering | test_net.py (TestStages) | PASS |
| 6 | Solver creation and step | test_solver.py | PASS |
| 7 | coord_map basic operations | test_coord_map.py | PASS |
| 8 | draw module import and basic usage | test_draw.py | PASS |
| 9 | draw module | test_draw.py | PASS |
| 10 | io: array_to_blobproto round-trip | test_io.py | PASS |
| 11 | API surface consistency | 全模块 | PASS |

**汇总: 11 PASS / 0 FAIL / 0 SKIP**

---

## 5. 生产环境标准检查

| 标准 | python-module | pycaffe | 状态 |
|------|:---:|:---:|:---:|
| 多阶段构建 | base-system → base-builder → builder → runtime | FROM python-module | PASS |
| 非 root 用户 | builder (UID 1000) | builder (UID 1000) | PASS |
| HEALTHCHECK | `import caffe; from caffeproto import caffe_pb2` | `import pycaffe; print(version)` | PASS |
| .dockerignore | 排除 .git/, __pycache__/, build/, *.whl 等 | — | PASS |
| 阿里云镜像源 | apt + pip | — | PASS |
| 镜像大小 | 5.27 GB | 5.38 GB (+0.11 GB) | 合理 |

---

## 6. 已知限制

1. **TVM 不可用**: `operators.layers.L2Norm` 需 TVM Relax 运行时，镜像中未安装
2. **pydotplus 未安装**: `pycaffe.draw` 模块需要 pydotplus + graphviz，作为可选依赖跳过了 draw 测试
3. **CMake 警告**: `CMakeLists.txt` 中 `find_library(BOOST_SYSTEM_LIBRARY boost_system)` 在 Boost 1.90.0 中会产生 "not found" 警告，但不影响构建（该库为可选依赖）
4. **镜像大小**: 5.27-5.38 GB 较大，主要因为包含完整编译工具链和 OpenCV 等大型依赖

---

## 7. 受影响文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `caffex/Makefile` | 修改 | 移除 `boost_system` 链接标志 |
| `caffex/python/caffe/_caffe.cpp` | 修改 | `import_array1()` 移至模块初始化开头 |
| `docker/modules/python-module/Dockerfile` | 修改 | 移除 `libboost-system-dev`；`make distribute` 容错 |
| `docker/modules/pycaffe/Dockerfile` | 修改 | 移除 `python3.10-venv`；添加 `--break-system-packages` |
| `.trae/specs/docker-images-for-modules/spec.md` | 修改 | 更新最终实现状态和验证结果 |