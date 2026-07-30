# Caffe - 深度学习框架三层架构演进版

BVLC Caffe 深度学习框架的演进版本，包含原始fork、CPU精简推理版和基于TVM FFI的现代Python绑定三层架构。

---

## 三层架构概览

本项目采用三层渐进式架构设计，从原始BVLC Caffe逐步演进到现代Python绑定，兼顾兼容性与现代性：

| 模块 | 版本 | Python要求 | 定位 |
|------|------|-----------|------|
| caffex | 1.0.0 | 无特定要求 | BVLC Caffe原始fork，完整训练/推理框架（参考源码） |
| caffe-slim | 1.0.0-slim | >=3.10 (支持3.10-3.13) | CPU-only精简推理版，TVM Relax算子支持 |
| caffe-ffi | 0.1.0 (Alpha) | >=3.14 | 基于TVM FFI原生对象系统的现代Python绑定（推荐使用） |

---

## 模块详解

### caffex - BVLC Caffe原始fork (v1.0.0)

**功能定位**：BVLC Caffe原始fork，完整深度学习框架，作为源码参考和完整训练功能保留。

**核心特性**：
- CUDA/cuDNN/NCCL GPU加速支持
- 75+层实现
- 完整训练和推理流水线
- Matlab绑定、Python绑定
- OpenCV/LevelDB/LMDB/HDF5数据格式支持

**依赖**：
- 必需：glog、protobuf、BLAS、Python3
- 可选：CUDA、OpenCV、LevelDB、LMDB、HDF5、Matlab

**构建**：CMake（参考 `caffex/INSTALL.md`）

**许可证**：BSD 2-Clause（见 `caffex/LICENSE`）

**适用场景**：源码参考、完整训练需求、CUDA GPU训练。

---

### caffe-slim - CPU精简推理版 (v1.0.0-slim)

**功能定位**：CPU-only精简推理版Caffe，移除GPU依赖，专为推理场景优化。

**技术规格**：
- Python要求：>=3.10（支持3.10-3.13）
- C++标准：C++17

**核心特性**：
- 移除CUDA/GPU依赖，纯CPU运行
- tvm-ffi header-only集成
- TVM Relax算子支持
- 静态库 `caffe_core` + 共享库 `_caffe` Python扩展
- scikit-build-core现代构建系统
- caffeproto：protobuf Python绑定
- operators：TVM Relax算子层
- pycaffe：传统PyCaffe绑定，含Python 3.14兼容性patch

**关键依赖**：
- tvm-ffi（header-only）
- protobuf
- BLAS
- numpy>=1.24

**构建系统**：CMake + scikit-build-core

**目录结构**：
- `caffeproto/` - protobuf Python绑定
- `operators/` - TVM Relax算子层
- `pycaffe/` - 传统PyCaffe绑定（含py314 patch）
- `include/`、`src/` - C++头文件和源码
- `cmake/`、`protos/`、`scripts/`、`tests/`

---

### caffe-ffi - TVM FFI现代绑定 (v0.1.0 Alpha)【推荐】

**功能定位**：基于TVM FFI原生对象系统的现代Caffe Python绑定，提供高性能、类型安全的Python接口。

**技术规格**：
- Python要求：>=3.14
- C++标准：C++17

**核心特性**：
1. **双类对象模型**：`XxxObj` C++内部类 + `Xxx ObjectRef` Python句柄类，实现Python/C++无缝互操作
2. **零拷贝DLPack张量通路**：`data_tensor`/`diff_tensor`属性，通过`numpy.from_dlpack`实现，大张量操作性能提升1000x+
3. **三层日志架构**：SPDLOG_CAFFE宏/CAFFE_LOGGING_ENABLED编译开关/`set_log_level`运行时API
4. **类型化异常体系**：`CaffeError`基类→`BlobError`/`LayerError`/`NetError`/`InvalidArgumentError`/`NotImplementedError`/`IOError`子类
5. **C++和Python单元测试**：ctest + pytest，188+测试用例通过
6. **跨平台支持**：Windows/Linux双平台兼容
7. **内存泄漏检测**：`live_blob_count()`/`total_allocated_bytes()`/`memory_info()`全局API
8. **已支持约20层**：accuracy、batch_norm、bias、concat、conv、dropout、eltwise、elu、flatten、inner_product、input、pooling、prelu、relu、reshape、scale、sigmoid、softmax、softmax_loss、tanh

**关键依赖**：
- numpy>=2.3
- protobuf>=7.0.0
- apache-tvm-ffi
- scikit-build-core>=0.10
- cmake>=3.26
- ninja>=1.13

**构建系统**：CMake + scikit-build-core（9个模块化.cmake文件：CompilerConfig、Dependencies、DetectBLAS、Install、Options、ProtoCompile、TargetBuild、Tests、WindowsDllCopy）

**环境配置**：提供 `environment.yml` conda环境配置文件

**安装验证**：
```bash
python -c "import caffe_ffi; print(caffe_ffi.__version__)"
```

---

## 模块对比

| 维度 | caffex | caffe-slim | caffe-ffi |
|------|--------|------------|-----------|
| 版本 | 1.0.0 | 1.0.0-slim | 0.1.0 (Alpha) |
| Python要求 | 无特定要求 | >=3.10 (3.10-3.13) | >=3.14 |
| C++标准 | C++11 | C++17 | C++17 |
| GPU支持 | 支持 CUDA/cuDNN | 不支持 (CPU-only) | 不支持 (CPU-only) |
| 训练支持 | 支持 完整训练 | 不支持 仅推理 | 不支持 仅推理 |
| 层数 | 75+层 | 精简 | 约20层 |
| TVM FFI集成 | 无 | 有 header-only | 有 原生对象系统 |
| 零拷贝张量 | 无 | 无 | 有 DLPack 1000x+加速 |
| 类型化异常 | 无 | 无 | 有 |
| 构建系统 | 传统CMake | CMake + scikit-build-core | CMake + scikit-build-core（模块化） |
| 测试覆盖 | - | - | 188+测试用例 |
| 推荐场景 | 源码参考/GPU训练 | 轻量推理/Python 3.10-3.13 | 现代Python绑定/高性能推理 |

---

## 环境准备与安装

### 使用conda（推荐）

```bash
# 创建conda环境
conda env create -f caffe-ffi/environment.yml

# 激活环境
conda activate caffe-ffi

# 进入caffe-ffi目录
cd caffe-ffi

# 可编辑模式安装
pip install -e .
```

**国内用户提示**：可取消 `environment.yml` 中清华/阿里镜像源注释以加速依赖下载。

---

## 快速开始

### Blob基本操作

```python
import numpy as np
from caffe_ffi import Blob

# 创建Blob
blob = Blob(shape=(2, 3, 4, 4))  # NCHW格式
print(f"Shape: {blob.shape}, Ndim: {blob.ndim}, Size: {blob.size}")

# 填充常量值
blob.fill(1.0)
blob.zero()  # 清零

# 从numpy数组设置数据
arr = np.random.randn(2, 3, 4, 4).astype(np.float32)
blob.from_numpy(arr)

# 零拷贝numpy视图（DLPack，大张量推荐）
data_view = blob.data_tensor
diff_view = blob.diff_tensor

# 安全访问（返回拷贝）
data_copy = blob.data
diff_copy = blob.diff

# 转为numpy（拷贝）
data_np = blob.to_numpy()

# 改变形状
blob.Reshape((1, 3, 8, 8))

# 从其他blob拷贝
blob2 = Blob(shape=(1, 3, 8, 8))
blob2.copy_from(blob)
```

### 简单MLP前向传播

```python
import numpy as np
from caffe_ffi import Blob, Net

# 定义简单MLP网络prototxt
prototxt = """
name: "SimpleMLP"
layer {
  name: "data"
  type: "Input"
  top: "data"
  input_param { shape: { dim: 1 dim: 784 } }
}
layer {
  name: "fc1"
  type: "InnerProduct"
  bottom: "data"
  top: "fc1"
  inner_product_param {
    num_output: 256
    weight_filler { type: "xavier" }
    bias_filler { type: "constant" }
  }
}
layer {
  name: "relu1"
  type: "ReLU"
  bottom: "fc1"
  top: "fc1"
}
layer {
  name: "fc2"
  type: "InnerProduct"
  bottom: "fc1"
  top: "fc2"
  inner_product_param {
    num_output: 10
    weight_filler { type: "xavier" }
    bias_filler { type: "constant" }
  }
}
layer {
  name: "prob"
  type: "Softmax"
  bottom: "fc2"
  top: "prob"
}
"""

# 构建网络
net = Net(prototxt)

# 准备输入
input_data = np.random.randn(1, 784).astype(np.float32)

# 前向传播
output = net.forward({"data": input_data})

# 获取输出
prob = output["prob"]
print(f"Output shape: {prob.shape}")
print(f"Predicted class: {np.argmax(prob)}")
```

### 全局API使用

```python
import caffe_ffi

# 版本信息
print(caffe_ffi.version())

# 日志控制
caffe_ffi.set_log_level(caffe_ffi.LOG_LEVEL_INFO)
caffe_ffi.enable_debug_logging()
caffe_ffi.disable_debug_logging()

# 内存监控
print(f"Live blobs: {caffe_ffi.live_blob_count()}")
print(f"Total allocated: {caffe_ffi.total_allocated_bytes()} bytes")
print(caffe_ffi.memory_info())
```

**日志级别常量**：
- `LOG_LEVEL_TRACE = 0`
- `LOG_LEVEL_DEBUG = 1`
- `LOG_LEVEL_INFO = 2`
- `LOG_LEVEL_WARN = 3`
- `LOG_LEVEL_ERROR = 4`

**导入方式**：
```python
import caffe_ffi
from caffe_ffi import Blob, Net
from caffe_ffi import net_from_param, net_param_from_string
```

---

## Python API参考

### Blob类

| 方法/属性 | 说明 |
|----------|------|
| `Blob(shape=(N,C,H,W))` 或 `Blob(shape=(N,))` | 构造函数 |
| `.from_numpy(arr)` | 从numpy数组设置数据 |
| `.data_tensor` / `.diff_tensor` | 零拷贝numpy视图（DLPack） |
| `.data` / `.diff` | 返回拷贝的安全访问 |
| `.fill(value)` | 填充常量值 |
| `.zero()` | 清零 |
| `.Reshape(shape)` | 改变形状 |
| `.shape` / `.ndim` / `.size` | 属性 |
| `.to_numpy()` | 转为numpy（拷贝） |
| `.copy_from(other)` | 从其他blob或数组拷贝 |

### Net类

| 方法/属性 | 说明 |
|----------|------|
| `Net(prototxt_path_or_string)` | 从prototxt文件或字符串构建 |
| `.forward(input_dict)` | 前向传播，返回 `{name: ndarray}` |
| `net_from_param(param)` | 从NetParam构建 |
| `net_param_from_string(prototxt_str)` | 从字符串解析NetParam |
| `read_net(prototxt_path)` | 读取prototxt |
| `read_net_from_prototxt(path)` | 读取prototxt文件 |
| `read_net_from_binary(caffemodel_path)` | 读取caffemodel |
| `.blob_by_name(name)` / `.layer_by_name(name)` | 按名称获取blob/layer |
| `.blobs_dict` / `.layers_dict` | 字典访问 |
| `.CopyTrainedLayersFrom(path)` / `.copy_from(path)` | 加载caffemodel |
| `.blob_names()` / `.layer_names()` | 获取名称列表 |

---

## Protobuf代码生成

### 方式一：快速生成（推荐）

使用内置的Python生成脚本（自动检查protoc版本一致性）：

```bash
python caffe-slim/scripts/gen_proto.py
```

脚本会自动：查找protoc → 检查版本一致性 → 编译proto → 验证生成代码。

### 方式二：直接调用protoc

```bash
protoc --proto_path=caffe-slim/protos \
  --cpp_out=caffe-slim/src/caffe/proto \
  --python_out=caffe-ffi/python/caffe_ffi/caffe/proto \
  caffe-slim/protos/caffe.proto
```

**注意**：脚本会自动检查protoc版本一致性，推荐使用方式一。

---

## 目录结构

```
caffe/
├── AGENTS.md              # AI协作者全局契约
├── README.md              # 本文档
├── .gitignore
├── .dockerignore
├── caffex/                # BVLC Caffe原始fork (v1.0.0)
│   ├── LICENSE            # BSD 2-Clause许可证
│   ├── INSTALL.md
│   ├── CMakeLists.txt
│   ├── src/               # 75+层CUDA/C++实现
│   ├── include/
│   ├── python/            # 原始Python绑定
│   ├── matlab/            # Matlab绑定
│   ├── examples/          # 官方示例
│   ├── models/
│   └── docs/
├── caffe-slim/            # CPU-only精简推理版 (v1.0.0-slim)
│   ├── CMakeLists.txt
│   ├── caffeproto/        # protobuf Python绑定
│   ├── operators/         # TVM Relax算子层
│   ├── pycaffe/           # 传统PyCaffe绑定+py314 patch
│   ├── include/
│   ├── src/
│   ├── cmake/
│   ├── protos/
│   ├── scripts/
│   │   └── gen_proto.py   # protobuf代码生成脚本
│   └── tests/
├── caffe-ffi/             # TVM FFI现代绑定 (v0.1.0 Alpha)【推荐】
│   ├── pyproject.toml
│   ├── environment.yml    # conda环境配置
│   ├── CMakeLists.txt
│   ├── cmake/             # 9个模块化.cmake文件
│   ├── include/           # C++头文件（双类对象模型）
│   ├── src/               # C++实现（层注册、零拷贝张量、异常体系）
│   ├── python/
│   │   └── caffe_ffi/     # Python包
│   │       ├── __init__.py
│   │       ├── _core.py   # Blob/Layer/Net核心类
│   │       ├── blob.py
│   │       ├── layer.py
│   │       ├── net.py
│   │       ├── io.py
│   │       └── tools/     # memory/debug工具
│   ├── tests/             # C++和Python测试
│   ├── examples/          # 示例脚本（MLP/benchmark/零拷贝demo等）
│   └── docs/              # 优化报告、技术文档
├── docs/
│   └── adding-operators.md  # 添加新算子四步法指南
├── .agents/               # AI协作者规范容器
└── .trae/                 # Spec规划文档
```

---

## 重要变更记录

按时间倒序排列：

- **零拷贝DLPack张量通路优化**：实现`data_tensor`/`diff_tensor`零拷贝numpy访问，大张量操作性能提升1000x+
- **TVM FFI集成与双类对象模型**：基于apache-tvm-ffi实现`XxxObj`/`Xxx ObjectRef`双类模型，Python/C++无缝互操作
- **CMake构建系统原子化重构**：拆分为9个模块化.cmake文件（CompilerConfig/Dependencies/DetectBLAS等），职责单一清晰
- **C++单元测试框架搭建**：基于Catch2的C++测试框架 + pytest Python测试，188+测试用例通过
- **类型化异常体系**：`CaffeError`基类→`BlobError`/`LayerError`/`NetError`/`InvalidArgumentError`等子类，分层错误处理
- **三层日志架构**：SPDLOG_CAFFE宏/编译开关/运行时`set_log_level` API
- **内存监控与泄漏检测**：`live_blob_count()`/`total_allocated_bytes()`/`memory_info()`全局API
- **FindBLAS递归Bug修复**：修复CMake FindBLAS在某些环境下的递归调用问题
- **Python 3.14适配**：caffe-slim pycaffe添加py314兼容性patch；caffe-ffi原生支持Python 3.14+
- **scikit-build-core构建迁移**：从传统setuptools迁移到scikit-build-core>=0.10现代构建系统

---

## 添加新算子

添加新算子采用四步法流程，详见：[docs/adding-operators.md](docs/adding-operators.md)

该指南详细说明了从C++层注册到Python绑定的完整流程。

---

## 许可证

本项目基于BSD 2-Clause许可证发布，详见 [caffex/LICENSE](caffex/LICENSE)。

caffex模块保留BVLC Caffe原始BSD 2-Clause许可证。

---

## 参考资料与协作说明

### 参考链接
- BVLC Caffe官网：[http://caffe.berkeleyvision.org](http://caffe.berkeleyvision.org)
- caffe-ffi优化报告：[caffe-ffi/docs/OPTIMIZATION_REPORT.md](caffe-ffi/docs/OPTIMIZATION_REPORT.md)
- 添加新算子指南：[docs/adding-operators.md](docs/adding-operators.md)

### AI协作者说明
- `AGENTS.md`：AI协作者全局契约，定义协作规范
- `.agents/`：AI协作者规范容器，包含各类开发规范和工作流
- `.trae/`：Spec规划文档目录，包含项目规划和演进路径

### 示例代码
更多示例请参考 `caffe-ffi/examples/` 目录：
- `create_and_run_mlp.py` - MLP网络创建与推理
- `benchmark_performance.py` - 性能基准测试
- `zero_copy_vs_copy_demo.py` - 零拷贝vs拷贝性能对比演示
- `test_memory_leak.py` - 内存泄漏检测示例
- `test_tensor_api.py` - 张量API使用示例
- `test_blob_wrapper.py` - Blob封装测试
