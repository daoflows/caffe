### Docker 独立模块镜像构建 Spec

> **最终实现状态**: 已完成构建并通过全部验证 (2026-07-23)
>
> **关键实现细节**:
> - 基础镜像: Ubuntu 26.04
> - BLAS: OpenBLAS (libopenblas-dev, 替代已废弃的 ATLAS)
> - Python: 3.14 (system)
> - Protobuf: >= 7.0 (pip), 系统 libprotobuf 3.21.12 (apt)
> - NumPy: 最新版 (无版本约束)
> - Boost: 1.90.0 (header-only boost_system, 需从 Makefile 移除 `-lboost_system`)
> - 构建方式: Makefile (Caffe C++), scikit-build-core + CMake (PyCaffe wheel)
> - 生产标准: 多阶段构建, 非 root 用户 (builder), HEALTHCHECK, .dockerignore
>
> **Ubuntu 26.04 兼容性关键修复**:
> 1. `import_array1()` 从 `BOOST_PYTHON_MODULE` 末尾移至开头（NumPy PyArray_Type 未初始化导致 segfault）
> 2. `caffex/Makefile` 移除 `boost_system` 链接（Boost 1.90.0 header-only，无 .so 文件）
> 3. `python3.10-venv` → 移除（Python 3.14 内置 venv，无需额外安装）
> 4. `pip install` 需添加 `--break-system-packages`（PEP 668 外部管理环境）
> 5. `libatlas-base-dev` → `libopenblas-dev`（ATLAS 在 Ubuntu 26.04 中已废弃）
> 6. `leveldb` 从 pip 依赖移除（不兼容 Python 3.14 的 PyUnicode_AS_UNICODE）
>
> **验证结果 (2026-07-23)**:
> | 镜像 | 验证方式 | 结果 |
> |------|---------|------|
> | `caffe-cpu:python-module` (5.27 GB) | verify-python-module.sh | 6 PASS / 0 FAIL / 1 SKIP |
> | `caffe-cpu:pycaffe` (5.38 GB) | verify-pycaffe.sh | 18 PASS / 0 FAIL / 1 SKIP |
> | `caffe-cpu:pycaffe` | verify-parity.sh (对标) | 11 PASS / 0 FAIL / 0 SKIP |

## 项目背景与复盘

### 模块演进路线
```
caffex/python/ (废弃)  ──→  python/ (主力维护)
    │                            │
    │ 原始 BVLC PyCaffe          │ caffeproto/ + operators/ + protos/ + scripts/ + tests/
    │ (Makefile 构建)            │ 新架构：caffeproto 解耦、operators 独立、测试完善
    │                            │
    └──────── 测试对标 ──────────→  python/pycaffe/python/pycaffe/ (PyCaffe 模块)
                                  │
                                  pycaffe/ 目录：scikit-build-core + CMake 构建 wheel
                                  python/pycaffe/ 目录：_caffe.cpp + Python 模块源码
                                  测试对标：caffex/python/caffe/test/ 的结果
```

### 关键文件清单

| 模块 | 路径 | 说明 |
|------|------|------|
| 废弃模块 | `caffex/python/caffe/` | 原始 BVLC PyCaffe，Makefile 构建，不再维护 |
| 主力模块 | `python/` | 新架构根目录，包含 caffeproto/operators/protos/scripts/tests |
| Proto 层 | `python/caffeproto/` | caffe_pb2 封装（caffe_fuse.py, caffe_utils.py） |
| 算子层 | `python/operators/` | TVM Relax 算子实现（layers.py 含 L2Norm） |
| Proto 源码 | `python/protos/` | caffe.proto + 生成的 caffe_pb2.py |
| PyCaffe 构建 | `python/pycaffe/` | CMakeLists.txt + pyproject.toml + build.sh |
| PyCaffe 源码 | `python/pycaffe/python/pycaffe/` | _caffe.cpp + 8 个 Python 模块 |
| 测试 | `python/tests/` | verify.py + test_inference.py + test_l2norm.py |
| 脚本 | `python/scripts/` | gen_proto.py + run_test.sh + 诊断脚本 |

### 测试对标关系
旧 `caffex/python/caffe/test/` 的测试结果，需要在新 `python/pycaffe/python/pycaffe/` 镜像中复现一致：
- `test_net.py` (TestNet/TestLevels/TestStages/TestAllInOne) → pycaffe 镜像中 Net 创建/前向/反向/保存/加载行为一致
- `test_solver.py` → pycaffe 镜像中 Solver 行为一致
- `test_coord_map.py` / `test_draw.py` / `test_io.py` → pycaffe 镜像中对应模块行为一致

## Why
`caffex/python` 已废弃，`python/` 是后续主力维护模块。需要为两个独立模块分别构建 Docker 镜像：
1. `python/` 模块镜像（caffeproto + operators + protos 完整环境）
2. `python/pycaffe/python/pycaffe` 模块镜像（PyCaffe wheel 独立部署）
并确保 pycaffe 镜像的测试结果与废弃的 `caffex/python` 测试结果一致。

## What Changes
- 新增 `docker/modules/python-module/Dockerfile`：为 `python/` 模块构建独立镜像（含完整 Caffe 编译 + Python 绑定 + caffeproto + operators）
- 新增 `docker/modules/pycaffe/Dockerfile`：为 `python/pycaffe/python/pycaffe` 模块构建独立镜像（基于预编译 libcaffe.so 构建 wheel 并安装）
- 新增 `docker/modules/python-module/scripts/`：python-module 镜像专用辅助脚本（含测试对标验证）
- 新增 `docker/modules/pycaffe/scripts/`：pycaffe 镜像专用辅助脚本（含与 caffex/python 测试对标验证）
- 新增 `docker/modules/Makefile`：统一构建入口，含复盘分析输出
- 复用现有 `docker/local/conda/Dockerfile` 中的多阶段构建模式（base-system → base-builder → builder → runtime）
- 复用现有 `python/scripts/` 中的 gen_proto.py、run_test.sh 等脚本

## Impact
- Affected specs: 无（全新 spec）
- Affected code: `docker/modules/`（新目录）、`docker/local/conda/`（参照复用）
- 不影响现有 `docker/local/conda/` 下的 Dockerfile 和构建流程
- `caffex/python/` 标记为废弃，不再参与新镜像构建

## ADDED Requirements

### Requirement: python-module 独立镜像（主力模块）
系统 SHALL 为 `python/` 主力模块提供独立 Docker 镜像构建能力，镜像包含完整的 Caffe C++ 编译产物、Python 绑定（`_caffe.so`）、caffeproto 层、operators 层及所有运行时依赖。

#### Scenario: 构建 python-module 镜像
- **WHEN** 在 WSL 中执行 `docker build -t caffe-cpu:python-module --target runtime -f docker/modules/python-module/Dockerfile .`
- **THEN** 成功生成包含完整 `python/` 模块环境的镜像
- **AND** 镜像中 `python -c "import caffe"` 可成功导入
- **AND** 镜像中 `caffe.Net`、`caffe.SGDSolver` 等核心 API 可用
- **AND** 镜像中 `from caffeproto import caffe_pb2` 可成功导入
- **AND** 镜像中 `from operators.layers import L2Norm` 可成功导入（如 TVM 可用）

#### Scenario: python-module 镜像运行时验证
- **WHEN** 启动容器并执行 `python/scripts/run_test.sh`
- **THEN** 所有测试通过（含 caffeproto、operators、tests 下的测试）

#### Scenario: python-module 镜像可移植性
- **WHEN** 镜像在任意 Docker 环境（含 WSL 内的 Docker）中运行
- **THEN** 无需额外配置即可正常使用 Caffe Python API
- **AND** 镜像大小控制在合理范围内（通过多阶段构建优化）

### Requirement: pycaffe 独立镜像（对标废弃模块）
系统 SHALL 为 `python/pycaffe/python/pycaffe` 模块提供独立 Docker 镜像构建能力，镜像包含预编译的 libcaffe.so、通过 scikit-build-core 构建的 pycaffe wheel 包及所有 Python 运行时依赖。**必须确保 pycaffe 镜像的测试结果与废弃的 `caffex/python` 测试结果一致。**

#### Scenario: 构建 pycaffe 镜像（依赖 python-module 镜像）
- **WHEN** 先构建好 `caffe-cpu:python-module` 镜像作为基础
- **AND** 在 WSL 中执行 `docker build -t caffe-cpu:pycaffe -f docker/modules/pycaffe/Dockerfile .`
- **THEN** 成功生成包含 pycaffe wheel 的镜像
- **AND** 镜像中 `python -c "import pycaffe"` 可成功导入
- **AND** 镜像中 `pycaffe.Net`、`pycaffe.TRAIN` 等核心 API 可用

#### Scenario: pycaffe 镜像测试对标验证（关键）
- **WHEN** 启动 pycaffe 容器并执行对标验证脚本
- **THEN** pycaffe 的 Net 创建/前向/反向/保存/加载行为与 `caffex/python/caffe/test/test_net.py` 中 TestNet 测试结果一致
- **AND** pycaffe 的 Level/Stage 过滤行为与 TestLevels/TestStages 测试结果一致
- **AND** pycaffe 的 Solver 行为与 `caffex/python/caffe/test/test_solver.py` 测试结果一致
- **AND** pycaffe 的 coord_map/draw/io 模块行为与对应测试结果一致

#### Scenario: pycaffe 镜像独立版本管理
- **WHEN** pycaffe 模块代码更新
- **THEN** 仅需重新构建 pycaffe 镜像，无需重新构建 python-module 镜像
- **AND** 两个镜像版本可独立演进

### Requirement: 统一构建入口与复盘分析
系统 SHALL 提供统一的构建入口，支持一键构建两个镜像，并支持单独构建任一镜像。构建前输出项目复盘分析报告。

#### Scenario: 一键构建全部镜像
- **WHEN** 在 WSL 中执行统一构建命令（如 `make -C docker/modules all`）
- **THEN** 按依赖顺序构建：先 python-module，后 pycaffe
- **AND** 构建开始前输出项目复盘分析（模块演进路线、关键文件清单、依赖关系图）
- **AND** 构建完成后两个镜像均可用

#### Scenario: 单独构建指定镜像
- **WHEN** 执行 `make -C docker/modules python-module` 或 `make -C docker/modules pycaffe`
- **THEN** 仅构建指定的镜像

#### Scenario: 构建前输出复盘信息
- **WHEN** 执行构建命令
- **THEN** 终端输出项目模块结构概览、废弃/主力模块关系、测试对标要求
- **AND** 输出信息包含两个模块的关键文件路径和依赖项列表