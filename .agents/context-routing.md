# 上下文路由表（Context Routing）

> 任务类型 → 必读源码文件映射。执行任务前，根据任务类型找到对应入口文件阅读。

## 按任务类型路由

### 🔧 构建与编译

| 关注点 | 文件路径 |
|--------|---------|
| 外层最小化构建（protobuf） | `../CMakeLists.txt` |
| 外层依赖管理 | `../conanfile.py` |
| Caffe完整构建系统 | `../caffex/CMakeLists.txt` |
| 构建依赖查找（gflags/glog/protobuf等） | `../caffex/cmake/Dependencies.cmake` |
| CUDA检测与配置 | `../caffex/cmake/Cuda.cmake` |
| 安装说明 | `../caffex/INSTALL.md` |
| Makefile构建（传统方式） | `../caffex/Makefile` + `../caffex/Makefile.config.example` |

### 🧠 核心架构理解（按抽象层从底向上）

| 抽象层 | 头文件 | 实现文件 | 必读优先级 |
|--------|--------|---------|-----------|
| SyncedMemory | `../caffex/include/caffe/syncedmem.hpp` | `../caffex/src/caffe/syncedmem.cpp`（如存在） | ⭐⭐⭐⭐⭐ |
| Blob | `../caffex/include/caffe/blob.hpp` | `../caffex/src/caffe/blob.cpp` | ⭐⭐⭐⭐⭐ |
| Layer（基类） | `../caffex/include/caffe/layer.hpp` | `../caffex/src/caffe/layer.cpp` | ⭐⭐⭐⭐⭐ |
| Net | `../caffex/include/caffe/net.hpp` | `../caffex/src/caffe/net.cpp` | ⭐⭐⭐⭐⭐ |
| Solver（基类） | `../caffex/include/caffe/solver.hpp` | `../caffex/src/caffe/solver.cpp` | ⭐⭐⭐⭐ |
| SGD求解器 | `../caffex/include/caffe/sgd_solvers.hpp` | `../caffex/src/caffe/solvers/sgd_solver.cpp` | ⭐⭐⭐ |
| LayerRegistry工厂 | `../caffex/include/caffe/layer_factory.hpp` | `../caffex/src/caffe/layer_factory.cpp` | ⭐⭐⭐⭐ |
| Solver工厂 | `../caffex/include/caffe/solver_factory.hpp` | `../caffex/src/caffe/solver_factory.cpp` | ⭐⭐⭐ |
| Caffe单例 | `../caffex/include/caffe/common.hpp` | `../caffex/src/caffe/common.cpp` | ⭐⭐⭐⭐ |
| Proto定义 | `../caffex/src/caffe/proto/caffe.proto` | （编译生成） | ⭐⭐⭐⭐⭐ |
| Filler（参数初始化） | `../caffex/include/caffe/filler.hpp` | `../caffex/src/caffe/filler.cpp`（如存在） | ⭐⭐⭐ |
| DataTransformer | `../caffex/include/caffe/data_transformer.hpp` | `../caffex/src/caffe/data_transformer.cpp` | ⭐⭐ |
| 并行训练 | `../caffex/include/caffe/parallel.hpp` | `../caffex/src/caffe/parallel.cpp` | ⭐⭐ |
| 内部线程 | `../caffex/include/caffe/internal_thread.hpp` | `../caffex/src/caffe/internal_thread.cpp` | ⭐⭐ |

### 📦 Layer 实现（推荐优先阅读的核心Layer）

| Layer类型 | 头文件 | 实现文件 | 说明 |
|-----------|--------|---------|------|
| 卷积层（核心） | `../caffex/include/caffe/layers/conv_layer.hpp` | `../caffex/src/caffe/layers/conv_layer.cpp` + `.cu` | 卷积运算，含im2col |
| 池化层 | `../caffex/include/caffe/layers/pooling_layer.hpp` | `../caffex/src/caffe/layers/pooling_layer.cpp` + `.cu` | 最大/平均池化 |
| ReLU激活 | `../caffex/include/caffe/layers/relu_layer.hpp` | `../caffex/src/caffe/layers/relu_layer.cpp` + `.cu` | 最常用激活函数 |
| 全连接层 | `../caffex/include/caffe/layers/inner_product_layer.hpp` | `../caffex/src/caffe/layers/inner_product_layer.cpp` + `.cu` | InnerProduct（FC层） |
| Softmax+Loss | `../caffex/include/caffe/layers/softmax_loss_layer.hpp` | `../caffex/src/caffe/layers/softmax_loss_layer.cpp` + `.cu` | 分类任务常用损失 |
| 数据层基类 | `../caffex/include/caffe/layers/base_data_layer.hpp` | `../caffex/src/caffe/layers/base_data_layer.cpp` | 数据读取抽象 |
| 数据层 | `../caffex/include/caffe/layers/data_layer.hpp` | `../caffex/src/caffe/layers/data_layer.cpp` | LMDB数据读取 |
| Dropout | `../caffex/include/caffe/layers/dropout_layer.hpp` | `../caffex/src/caffe/layers/dropout_layer.cpp` + `.cu` | 正则化 |
| BatchNorm | `../caffex/include/caffe/layers/batch_norm_layer.hpp` | `../caffex/src/caffe/layers/batch_norm_layer.cpp` + `.cu` | 批归一化 |
| Concat | `../caffex/include/caffe/layers/concat_layer.hpp` | `../caffex/src/caffe/layers/concat_layer.cpp` + `.cu` | 张量拼接 |
| Split | `../caffex/include/caffe/layers/split_layer.hpp` | `../caffex/src/caffe/layers/split_layer.cpp` + `.cu` | 张量分裂（扇出） |
| 损失层基类 | `../caffex/include/caffe/layers/loss_layer.hpp` | （内联在头文件） | 所有损失层基类 |
| 神经元层基类 | `../caffex/include/caffe/layers/neuron_layer.hpp` | （内联在头文件） | ReLU/Sigmoid/Tanh等激活层基类 |

### 🔧 工具与实用程序

| 工具 | 文件路径 | 说明 |
|------|---------|------|
| caffe命令行主入口 | `../caffex/tools/caffe.cpp` | train/test/time/device_query |
| compute_image_mean | `../caffex/tools/compute_image_mean.cpp` | 计算图像均值 |
| extract_features | `../caffex/tools/extract_features.cpp` | 特征提取 |
| upgrade_net_proto_text | `../caffex/tools/upgrade_net_proto_text.cpp` | 升级旧版prototxt |
| 升级Proto工具 | `../caffex/include/caffe/util/upgrade_proto.hpp` | 兼容旧版模型文件 |
| IO工具 | `../caffex/include/caffe/util/io.hpp` | 读写proto、快照 |
| 数学函数 | `../caffex/include/caffe/util/math_functions.hpp` | BLAS/cuBLAS封装 |
| im2col | `../caffex/include/caffe/util/im2col.hpp` | 卷积展开 |
| 数据库（LMDB/LevelDB） | `../caffex/include/caffe/util/db.hpp` | 数据存储抽象 |
| 阻塞队列 | `../caffex/include/caffe/util/blocking_queue.hpp` | 多线程数据预取 |

### 🐍 Python绑定

| 模块 | 文件路径 |
|------|---------|
| Python入口 | `../caffex/python/caffe/__init__.py` |
| PyCaffe核心 | `../caffex/python/caffe/_caffe.cpp`（C++绑定）+ `../caffex/python/caffe/pycaffe.py` |
| Net类（Python） | `../caffex/python/caffe/pycaffe.py` |
| Classifier封装 | `../caffex/python/caffe/classifier.py` |
| Detector封装 | `../caffex/python/caffe/detector.py` |
| NetSpec声明式定义 | `../caffex/python/caffe/net_spec.py` |
| IO工具 | `../caffex/python/caffe/io.py` |
| 绘图工具 | `../caffex/python/caffe/draw.py` |

### 📝 官方文档

| 文档 | 路径 |
|------|------|
| 官方主页/教程入口 | `../caffex/docs/index.md` |
| 安装指南 | `../caffex/docs/installation.md` |
| Blob/Layer/Net教程 | `../caffex/docs/tutorial/net_layer_blob.md` |
| 前向反向传播 | `../caffex/docs/tutorial/forward_backward.md` |
| 层定义教程 | `../caffex/docs/tutorial/layers.md` |
| 求解器说明 | `../caffex/docs/tutorial/solver.md` |
| 模型动物园 | `../caffex/docs/model_zoo.md` |
| 开发指南 | `../caffex/docs/development.md` |
| 接口说明（Python/MATLAB） | `../caffex/docs/tutorial/interfaces.md` |
| 各Layer使用文档 | `../caffex/docs/tutorial/layers/`（70+个md文件） |

### 📁 示例

| 示例 | 路径 |
|------|------|
| MNIST手写数字 | `../caffex/examples/mnist/` |
| CIFAR-10分类 | `../caffex/examples/cifar10/` |
| ImageNet分类 | `../caffex/examples/imagenet/` |
| 特征提取 | `../caffex/examples/feature_extraction/` |
| C++分类示例 | `../caffex/examples/cpp_classification/` |
| Net Surgery（模型裁剪） | `../caffex/examples/net_surgery.ipynb` |
| Siamese网络 | `../caffex/examples/siamese/` |
| Web Demo | `../caffex/examples/web_demo/` |

## 父工作区资源

当需要使用SpecWeave的Skill工具、复盘方法论、模式库等能力时，向上回溯到父工作区：

| 资源 | 路径（相对于本文件） |
|------|-------------------|
| SpecWeave AGENTS.md | `../../../AGENTS.md` |
| 已有Caffe架构分析（含思维导图） | `../../../.agents/docs/knowledge/learning/caffe-architecture-wiki/README.md` |
| 全局核心规则 | `../../../.agents/global-core-rules.md` |
| 上下文路由表（主工作区） | `../../../.agents/context-routing.md` |
| Skill门面 | `../../../.agents/skills/` |
| 复盘模板与模式库 | `../../../.agents/docs/retrospective/` |
