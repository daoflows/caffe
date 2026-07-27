# PyCaffe Full Build Environment for Caffe Operator Tests

## 概述

本目录提供完整的 BVLC PyCaffe 编译环境，用于运行 `tests/ops/` 下的 Caffe 算子测试。

**与 `docker/standalone/pycaffe/` 的区别**：
- `standalone/pycaffe`：基于 caffe-slim，推理-only，`caffe.SGDSolver` 是 stub（抛 `NotImplementedError`）
- 本环境：基于 BVLC 原版 Caffe（`caffex/`），编译完整 pycaffe，含 Solver/Net/Layers 全部 API

## API 依赖清单

测试代码使用以下 Caffe Python API，均需完整 pycaffe：

| API | 用途 |
|---|---|
| `caffe.NetSpec` | 定义网络结构 |
| `caffe.Net` | 加载并运行网络 |
| `caffe.SGDSolver` | 生成 caffemodel 权重文件 |
| `caffe.TEST` | 推理模式标志 |
| `caffe.layers as L` | 所有 Layer 定义（23个算子） |
| `caffe.params as P` | 所有 Param 定义（Pooling类型等） |
| `caffe.io` | blob 读写 |
| `caffe.proto.caffe_pb2` | Protobuf 定义 |

## 快速开始

### Windows PowerShell（推荐）

```powershell
cd projects\xuanspace\vendor\caffe

# 一键构建+运行全部测试
.\tests\docker\build-and-test.ps1

# 快速模式（仅构建+验证import，不跑测试）
.\tests\docker\build-and-test.ps1 -Quick

# 构建后进入交互式shell
.\tests\docker\build-and-test.ps1 -Interactive

# 强制重新构建（不使用缓存）
.\tests\docker\build-and-test.ps1 -NoCache
```

### Linux / macOS / WSL Bash

```bash
cd projects/xuanspace/vendor/caffe

# 一键构建+运行全部测试
bash tests/docker/build-and-test.sh

# 快速模式
bash tests/docker/build-and-test.sh --quick

# 强制重新构建
bash tests/docker/build-and-test.sh --no-cache
```

### 手动 Docker 命令

```bash
cd projects/xuanspace/vendor/caffe

# 1. 构建镜像
docker build -t caffe-pycaffe:full -f tests/docker/Dockerfile .

# 2. 验证 import
docker run --rm caffe-pycaffe:full python -c "import caffe; print('OK')"

# 3. 运行测试（带覆盖率）
docker run --rm -v $(pwd)/tests/ops:/workspace/tests \
  caffe-pycaffe:full bash -c "
    cd /workspace/tests && \
    CAFFE_LOG_LEVEL=INFO pytest -v \
      --cov=. \
      --cov-report=term-missing \
      --cov-report=html:/workspace/coverage/htmlcov
  "

# 4. 交互式调试
docker run --rm -it -v $(pwd)/tests/ops:/workspace/tests caffe-pycaffe:full bash
```

## 日志级别

设置 `CAFFE_LOG_LEVEL` 环境变量控制日志详细程度：

```bash
# DEBUG（最详细，包含所有参数和中间结果）
CAFFE_LOG_LEVEL=DEBUG pytest -v

# INFO（算子级别的进度信息）
CAFFE_LOG_LEVEL=INFO pytest -v

# WARNING（默认，仅警告和错误）
CAFFE_LOG_LEVEL=WARNING pytest -v

# ERROR（仅错误）
CAFFE_LOG_LEVEL=ERROR pytest -v
```

## 测试覆盖的算子

共 23 个 Caffe 算子，分 5 大类：

1. **激活函数类**（5个）：ReLU、Sigmoid、TanH、PReLU、Dropout
2. **归一化/线性代数类**（6个）：BatchNorm、LRN、Scale、Power、Flatten、InnerProduct
3. **卷积/池化类**（3个）：Convolution、Deconvolution、Pooling
4. **数据操作类**（5个）：Concat、Crop、Slice、Reshape、Permute
5. **逐元素/归约/嵌入类**（4个）：Eltwise、Softmax、Reduction、Embed

## 常见问题

### 1. 构建失败：HDF5 找不到

Ubuntu 22.04 的 HDF5 包名是 `libhdf5-serial-dev`，库文件名带 `_serial` 后缀。Dockerfile 中已包含自动修复：
```bash
ln -sf libhdf5_serial.so libhdf5.so
```

### 2. 构建失败：Python/NumPy 路径错误

Dockerfile 使用 `sysconfig` 自动检测 Python 3 路径，无需手动配置。

### 3. 构建慢（首次构建约 15-30 分钟）

BVLC Caffe 需要编译大量 C++ 代码，CPU-only 版本首次构建约 15-30 分钟。后续构建使用缓存可加速。

### 4. 测试运行报错：Solver stub NotImplementedError

这是 caffe-slim 的问题，使用本目录的完整 pycaffe 镜像即可。确保运行的是 `caffe-pycaffe:full` 镜像而非 standalone 镜像。
