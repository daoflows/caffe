# Caffe C++ 核心瘦身优化（tvm-ffi 替换 glog/boost） - 产品需求文档

> **状态**: ✅ 已完成（2026-07-23）
> **复盘报告**: [retrospective-caffe-slim-tvm-ffi-20260723](../../../../../../.agents/docs/retrospective/reports/code-optimization/retrospective-caffe-slim-tvm-ffi-20260723/README.md)
> **模板来源**: 本项目作为首个实战案例，萃取为 [cpp-dependency-slimming 模板](../../../../../../spec/templates/cpp-dependency-slimming/)

---

## Step 0: 环境预检（MANDATORY PRE-CHECK）

> ⚠️ **教训**: 本项目初期未做环境预检，在Windows上尝试编译Linux原生Caffe，因MSVC/SKD配置问题浪费约30%时间。最终切换到WSL解决。**未来同类项目必须先完成本步骤**。

### 0.1 原项目构建环境信息

| 项 | 实际值 | 验证情况 |
|----|--------|---------|
| 原项目推荐构建平台 | Linux (Ubuntu 18.04+/20.04+) | BVLC Caffe原生为Linux开发 |
| 原项目编译器要求 | GCC 4.8+/Clang 3.3+ (支持C++11) | caffex CMakeLists.txt |
| 原项目C++标准 | C++11 | 原始代码 |
| 我们的目标构建平台 | WSL2 (Ubuntu 22.04) | ⚠️ 初期错误选择Windows，后切换WSL |
| 目标编译器版本 | GCC 11.4.0 | `g++ --version` 验证通过 |
| 目标C++标准 | C++17（由tvm-ffi强制要求） | ✅ GCC 11完全支持 |

**环境预检确认清单（执行状态）：**
- [x] ~~未做：初期跳过此步骤~~ → 教训记录
- [x] WSL2 Ubuntu 22.04环境可用
- [x] GCC 11.4.0已安装，编译hello world通过
- [x] tvm-ffi在WSL下可正确编译
- [x] 已决策：CPU_ONLY模式，优先WSL/Linux构建
- [ ] ~~Windows构建~~：MSVC环境因CRT/SDK问题放弃，非目标平台

### 0.2 跨平台风险评估（事后总结）

| 风险项 | 评估 | 实际情况/缓解措施 |
|--------|------|-----------------|
| POSIX函数(unistd.h, dlfcn.h)在Windows不可用 | 🔴 高 | io.cpp中close()/read()在Windows缺失，需加`#include <unistd.h>`条件编译；最终放弃Windows构建，用WSL |
| MSVC与GCC语法差异 | 🟡 中 | `__attribute__`、typeof等GCC特有语法在MSVC不支持 |
| 路径分隔符差异 | 🟢 低 | std::filesystem可解决，但项目中硬编码`/`较少 |
| protobuf在Windows的ABI兼容 | 🟡 中 | protobuf版本匹配问题 |
| libbacktrace在Windows的CRLF问题 | 🟡 中 | tvm-ffi的libbacktrace子模块在Windows下有CRLF换行符问题，通过`TVM_FFI_USE_LIBBACKTRACE=OFF`禁用 |

**教训**: Linux原生C++项目优先选择WSL/Linux作为构建环境，不要在Windows上强行适配。

---

## Step 0.5: API映射前置验证（MANDATORY PRE-CHECK）

> ⚠️ **教训**: 本项目初期"边猜边写"API映射，未做最小验证程序，导致TVM_FFI_ICHECK宏参数错误、DLDataType命名空间错误、LOG(FATAL)语义错误等问题5-6轮返工。**未来同类项目必须先完成API映射表并验证**。

### 0.5.1 旧依赖API使用清单

| 旧依赖库 | 使用的组件/API | 使用位置（文件数） |
|---------|---------------|-----------------|
| boost (10+组件) | shared_ptr/make_shared/dynamic_pointer_cast | 几乎所有头文件(45+) |
| boost | thread/mutex/condition_variable/scoped_lock | common.cpp, internal_thread.cpp, blocking_queue.cpp |
| boost | thread_specific_ptr | common.cpp (Caffe单例) |
| boost | thread_interrupted | internal_thread.cpp, base_data_layer.cpp |
| boost | barrier | parallel.hpp/cpp |
| boost | filesystem | io.hpp, upgrade_proto.cpp |
| boost | function/bind | solver.hpp, signal_handler.cpp |
| boost | posix_time (date_time) | benchmark.hpp/cpp |
| boost | random/mt19937 | rng.hpp, math_functions.cpp |
| boost | math/nextafter | math_functions.cpp |
| boost | split/trim/is_any_of/lexical_cast | solver.cpp等 |
| boost | python.hpp + suite/indexing + raw_function | _caffe.cpp (boost::python绑定) |
| glog | LOG(INFO)/LOG(WARNING)/LOG(ERROR)/LOG(FATAL) | 通过common.hpp被所有文件包含 |
| glog | CHECK/CHECK_EQ/CHECK_NE/CHECK_LT/CHECK_LE/CHECK_GT/CHECK_GE/DCHECK系列 | 所有文件 |
| glog | CHECK_NOTNULL/CHECK_DOUBLE_EQ/CHECK_NEAR | 多个文件 |
| glog | InitGoogleLogging/InstallFailureSignalHandler | common.cpp |
| glog | FLAGS_minloglevel/FLAGS_logtostderr | common.cpp |
| gflags | ParseCommandLineFlags/FLAGS_* | common.cpp, tools/caffe.cpp(不迁移) |

### 0.5.2 旧API→新API映射表（实际映射）

| 旧API | 新API替代 | 验证状态 | 实际遇到的问题 |
|-------|----------|---------|--------------|
| `boost::shared_ptr<T>` | `std::shared_ptr<T>` | ✅ 已验证 | 无问题，直接替换 |
| `boost::make_shared<T>` | `std::make_shared<T>` | ✅ 已验证 | 无问题 |
| `boost::scoped_ptr<T>` | `std::unique_ptr<T>` | ✅ 已验证 | tools/不迁移，未实际使用 |
| `boost::mutex` | `std::mutex` | ✅ 已验证 | 配合std::unique_lock/std::lock_guard |
| `boost::condition_variable` | `std::condition_variable` | ✅ 已验证 | blocking_queue中正常工作 |
| `boost::thread_specific_ptr` | 自定义ThreadLocalPtr（thread_local+ThreadLocalStore） | ✅ 已验证 | 初期错误使用static thread_local成员导致线程间共享，改为ThreadLocalStore类修复 |
| `boost::thread` + `boost::thread_interrupted` | `std::thread` + `std::atomic<bool> stop_` | ✅ 已验证 | interruption_point模式改为检查stop_标志 |
| `boost::barrier` | 自定义Barrier（condition_variable+counter） | ✅ 已验证 | parallel.cpp不迁移，Barrier仅用于internal_thread场景 |
| `boost::filesystem::path` | `std::filesystem::path` | ✅ 已验证 | C++17原生支持，namespace别名即可 |
| `boost::function` | `std::function` | ✅ 已验证 | 无问题 |
| `boost::bind` | `std::bind` / lambda | ✅ 已验证 | signal_handler中使用 |
| `boost::posix_time` | `std::chrono` + 自定义Timer类 | ✅ 已验证 | benchmark计时功能正常 |
| `boost::mt19937` | `std::mt19937` | ✅ 已验证 | rng_t类型别名 |
| `boost::math::nextafter` | `std::nextafter` (cmath) | ✅ 已验证 | ⚠️ 初期未做float/double特化导致无限递归 |
| `boost::split/trim/is_any_of` | 内联string_utils工具函数 | ✅ 已验证 | header-only实现 |
| `boost::lexical_cast` | 内联模板函数+stringstream | ✅ 已验证 | 简单实现，满足需求 |
| `glog LOG(INFO/WARNING/ERROR)` | 自定义LogMessage类到stderr | ✅ 已验证 | 格式`[I/W/E] file:line] message` |
| `glog LOG(FATAL)` | ~~std::abort()~~ → TVM_FFI_THROW(RuntimeError) | ✅ 已验证 | ⚠️ 初期用abort()导致无法被FFI安全捕获，改为throw |
| `glog CHECK(x)` | TVM_FFI_ICHECK(x) | ✅ 已验证 | ⚠️ 初期误用TVM_FFI_ICHECK宏参数，改用TVM_FFI_CHECK |
| `glog CHECK_EQ(a,b)` | TVM_FFI_ICHECK_EQ(a,b) | ✅ 已验证 | 同上 |
| `glog DCHECK(x)` | TVM_FFI_DCHECK(x) | ✅ 已验证 | 无问题 |
| `boost::python` | tvm-ffi TVM_FFI_DLL_EXPORT_TYPED_FUNC + handle模式 | ✅ 已验证 | handle=uintptr_t管理C++对象生命周期 |
| `bp::class_<Net>` 注册 | C ABI函数: NetInit/NetForward/NetDelete等 | ✅ 已验证 | Python端用类包装handle |
| `NdarrayConverter` (numpy零拷贝) | tvm::ffi::Tensor (DLPack) | ✅ 已验证 | DLTensor直接指向Blob内存 |
| `vector_indexing_suite` | ffi::Array<std::string> 手动构造 | ✅ 已验证 | 字符串数组通过ffi::Array返回 |
| `gflags ParseCommandLineFlags` | 移除（Python层处理配置） | ✅ 已验证 | GlobalInit改为空操作 |
| `FLAGS_*` 全局标志 | 移除或通过函数参数传入 | ✅ 已验证 | CPU_ONLY下多GPU标志不需要 |

**API映射教训**:
- ❌ 不要凭文档猜测API签名，必须写最小验证程序
- ❌ TVM_FFI_ICHECK宏的用法与glog CHECK不完全相同，需仔细阅读error.h
- ❌ LOG(FATAL)必须抛出异常（不能abort()），否则无法通过TVM_FFI_SAFE_CALL_BEGIN/END安全传递到Python
- ❌ DLDataType/DLDevice在全局命名空间（不在tvm::ffi中）

---

## Step 1: 依赖闭包分析（MANDATORY PRE-CHECK）

> ⚠️ **教训**: 本项目初期采用"我觉得需要哪些文件"的正向猜测策略，导致头文件遗漏，出现"打地鼠式补文件"问题（每轮编译缺一个头文件，补了又缺下一个）。**未来同类项目必须用g++ -H工具获取真实include闭包**。

### 1.1 入口点

| 入口类型 | 文件路径 | 说明 |
|---------|---------|------|
| 主库入口头文件 | caffex/include/caffe/caffe.hpp | 所有外部使用者include的主头文件 |
| FFI/绑定入口 | caffex/python/pycaffe/python/pycaffe/_caffe.cpp | boost::python绑定入口（需重写） |

### 1.2 实际迁移文件清单（事后统计）

| 模块 | 迁移头文件数 | 迁移源文件数 | 说明 |
|------|------------|------------|------|
| 核心抽象 (Blob/Layer/Net/Solver) | 9 | 7 | blob, layer, net, solver, syncedmem, common, layer_factory, caffe.hpp等 |
| compat/兼容层 | 11 | 0 | 全部header-only |
| Util工具 | 12 | 11 | math_functions, io, blocking_queue, benchmark, rng, signal_handler, upgrade_proto, db stub, internal_thread, filler, format, insert_splits, device_alternate |
| Layers（推理路径） | 42 | 42 | NeuronLayer基类+ReLU/Sigmoid/TanH+Conv/Pool/FC+Softmax/SoftmaxLoss+BN/Scale+Eltwise/Concat/Split/Dropout/Reshape/Flatten+Accuracy/ArgMax+Input/MemoryData |
| Proto | 1 | 1(生成) | caffe.proto → caffe.pb.h/cc |
| FFI/绑定 | 0 | 1 | src/caffe/_caffe.cpp（tvm-ffi版本，重写） |
| **总计** | **75** | **62** | **总计137个文件（去掉caffe.pb的生成文件为130个），约11310行代码** |

**不迁移的文件（明确排除）：**
- ❌ 所有.cu/.cuh文件（CUDA/GPU代码）
- ❌ cudnn_*_layer.cpp（cuDNN加速层）
- ❌ python_layer.*（PythonLayer，boost::python专属）
- ❌ hdf5_*_layer.*（HDF5数据层）
- ❌ lmdb_data_layer.*、leveldb_data_layer.*、window_data_layer.*（数据库后端）
- ❌ lstm_layer.*、rnn_layer.*、recurrent_layer.*（循环网络）
- ❌ detection_*_layer.*、roi_*_layer.*、nms_layer.*、smooth_l1_loss.*（检测层）
- ❌ spp_layer.*、yolo_*layer.*（特殊层）
- ❌ parallel.cpp/.hpp（多GPU并行）
- ❌ nccl.cpp/.hpp（多GPU通信）
- ❌ db_leveldb.cpp、db_lmdb.cpp（数据库后端实现，仅保留db.hpp stub）
- ❌ im2col.cu、math_functions.cu（GPU核函数）
- ❌ tools/、examples/、docs/、matlab/、scripts/、docker/（非核心目录）

### 1.3 闭包分析教训

- ❌ 正向猜测"需要哪些文件"会导致头文件遗漏，编译错误链极长
- ❌ 每次补一个文件又引入新的依赖，形成"打地鼠"循环
- ✅ 正确做法：使用`g++ -H -I include -fsyntax-only caffe.cpp 2>&1`获取真实include树，一次性列出所有依赖
- ✅ Layer迁移时，先列出LayerRegistry中所有注册的层，再按推理路径筛选需要的层

---

## Overview
- **Summary**: 对 BVLC Caffe（caffex）的 C++ 核心库进行依赖瘦身，使用 tvm-ffi 库（C++17）替换 glog 和 boost 等老旧依赖。瘦身完成的 C++ 核心代码（include/src）放置到 `external/chaos/caffe/python/` 目录下，与现有 Python 层（pycaffe/）整合。原有的 `python/pycaffe/python/pycaffe/_caffe.cpp`（boost::python绑定）重写为 tvm-ffi FFI 导出模块，彻底移除 boost::python 依赖。最终形成一个不依赖 boost、不依赖 glog、不依赖 gflags、使用 C++17 标准库 + tvm-ffi 的轻量 Caffe 推理核心库，通过 tvm-ffi 的跨语言 FFI 机制提供 Python 绑定。
- **Purpose**: 原始 caffex 依赖 boost（10+组件）和 glog/gflags，编译配置复杂、跨平台问题频发（NumPy 2.x ABI断裂、Boost.Python组件名变更等），与现代 Python 生态集成困难。通过替换为 tvm-ffi + C++17 标准库，大幅减少外部依赖，提高可维护性和构建效率，使得 pycaffe 可以作为独立 wheel 分发包使用。
- **Target Users**: 需要轻量 Caffe 推理核心、通过 Python 调用 Caffe 模型的开发者；将 Caffe 作为依赖嵌入其他项目的集成者；需要跨平台（Windows/Linux/macOS）构建 pycaffe 的用户。

## Goals
- 使用 tvm-ffi 的错误/检查系统（`TVM_FFI_ICHECK`/`TVM_FFI_THROW`/`TVM_FFI_DCHECK`）替换 glog 的 CHECK/DCHECK/LOG(FATAL) 宏
- 使用 C++17 标准库替换 boost 各组件（shared_ptr→std::shared_ptr, thread→std::thread, mutex→std::mutex, filesystem→std::filesystem, function→std::function, chrono→std::chrono, random→std::mt19937 等）
- 编写最小日志 shim 替代 glog 的 LOG(INFO)/LOG(WARNING)/LOG(ERROR) 分级日志
- 移除 gflags 依赖（Python 绑定场景下命令行解析由 Python 层处理）
- 将 `_caffe.cpp` 从 boost::python 绑定重写为 tvm-ffi FFI 导出（使用 `TVM_FFI_DLL_EXPORT_TYPED_FUNC` 宏导出 C ABI 函数，通过 handle 模式管理 Net/Blob 对象）
- 将瘦身完成的 C++ 核心代码（include/src）放置到 `external/chaos/caffe/python/` 目录下
- 适配现有 Python 层（pycaffe.py 等）使用新的 tvm-ffi FFI 接口
- 提供统一的 CMake 构建系统（python/CMakeLists.txt），编译 C++ 核心库和 FFI 扩展模块
- 确保瘦身代码编译通过、核心推理功能完整、无内存泄漏

## Non-Goals (Out of Scope)
- 不修改 `caffex/` 原始源码（遵循 AGENTS.md 规范，作为只读参考）
- 不保留 CUDA/CUDNN 支持（初始版本仅 CPU 推理；CPU_ONLY=ON）
- 不保留 LMDB/LevelDB/HDF5 数据库后端（初始版本使用内存/protobuf输入，MemoryDataLayer）
- 不保留 MATLAB 绑定
- 不保留 tools/、examples/、docs/、matlab/、scripts/、docker/ 等非核心目录
- 不保留 NCCL 多GPU训练支持
- 不保留训练相关 Solver（SGD/Adam等）的完整实现，初始版本仅保留推理所需的 Net::Forward 核心路径（Solver 代码可标记为可选/stub）
- 不保留 HDF5 保存/加载功能
- 不升级 protobuf 版本（保持现有 protobuf 生成的 caffe.pb.h/cc 兼容）
- 不保留 PythonLayer（动态在 Python 中定义 Layer 的功能，boost::python 专属）

## Background & Context
- **tvm-ffi** 是 Apache TVM 项目的 FFI 库，位于 `external/ffi/tvm-ffi/`，要求 C++17，提供：
  - 错误处理：`tvm::ffi::Error` 异常类 + `TVM_FFI_THROW`/`TVM_FFI_ICHECK`/`TVM_FFI_DCHECK` 宏（带 libbacktrace 回溯）
  - 安全调用边界：`TVM_FFI_SAFE_CALL_BEGIN/END` 宏用于 C ABI 边界异常转换
  - FFI 导出：`TVM_FFI_DLL_EXPORT_TYPED_FUNC(ExportName, Function)` 宏将普通 C++ 函数导出为稳定 C ABI 符号 `__tvm_ffi_<ExportName>`
  - FFI 加载：Python 端 `tvm_ffi.load_module("path/to/library")` 加载共享库，直接调用导出函数
  - 对象系统：`Object`/`ObjectPtr`/`Arc` 引用计数
  - 容器：`Array`/`Map`/`Tensor`（基于 DLPack，可与 NumPy 零拷贝互操作）、`String` 等跨语言容器
  - Python 运行时：`external/ffi/tvm-ffi/python/tvm_ffi/` 提供完整 Python 端支持（加载模块、类型转换、Tensor<->NumPy、dataclass 互操作等）
- **C++17 标准库**已涵盖 boost 绝大多数常用功能。
- **caffex 当前 boost 使用分布**（需要替换）：
  | boost 组件 | 使用位置 | C++17/tvm-ffi 替代 |
  |-----------|---------|-----------|
  | shared_ptr/make_shared | common.hpp + 所有文件 | std::shared_ptr/std::make_shared |
  | scoped_ptr | tools/examples（不迁移） | std::unique_ptr |
  | thread/mutex/condition_variable/scoped_lock | common.cpp, internal_thread.cpp, blocking_queue.cpp, parallel.cpp | std::thread, std::mutex, std::condition_variable, std::unique_lock |
  | thread_specific_ptr | common.cpp | thread_local |
  | thread_interrupted | internal_thread.cpp, base_data_layer.cpp | 自定义停止标志（std::atomic<bool>） |
  | barrier | parallel.hpp/cpp | 自研简单 barrier（基于 std::condition_variable） |
  | filesystem | io.hpp, upgrade_proto.cpp | std::filesystem |
  | function | solver.hpp | std::function |
  | bind | signal_handler.cpp | std::bind 或 lambda |
  | date_time/posix_time | benchmark.hpp/cpp | std::chrono |
  | random/mt19937 | rng.hpp, math_functions.cpp | <random> (std::mt19937) |
  | math/nextafter | math_functions.cpp | std::nextafter (cmath) |
  | split/trim/is_any_of/lexical_cast | solver.cpp 等 | 最小内联工具函数（compat/string_utils.hpp） |
  | python.hpp + suite/indexing + raw_function | _caffe.cpp | tvm-ffi Function 导出系统（TVM_FFI_DLL_EXPORT_TYPED_FUNC + handle 模式） |
  | make_shared/dynamic_pointer_cast | _caffe.cpp | std::make_shared/std::dynamic_pointer_cast |
- **glog 使用分布**：通过 `common.hpp` 被所有文件包含，使用 LOG(INFO)/WARNING/ERROR/FATAL、CHECK/DCHECK/CHECK_EQ 等系列、InitGoogleLogging、InstallFailureSignalHandler、FLAGS_minloglevel/FLAGS_logtostderr。tvm-ffi 提供 CHECK 替代（ICHECK/DCHECK）和异常抛出替代 LOG(FATAL)，但不提供分级日志，需补最小日志头。
- **gflags 使用分布**：主要在 tools/caffe.cpp（不迁移）和 common.cpp 中的 GlobalInit（需移除）。Python 扩展中也有 FLAGS_* 引用需移除。
- **目标目录现状** `external/chaos/caffe/python/` 已存在，包含：
  - `pycaffe/`：Python 包（pycaffe.py 包装层、classifier.py、detector.py、_caffe.cpp 绑定等）+ pyproject.toml + CMakeLists.txt（当前链接外部 caffex 构建的 libcaffe.so）
  - `caffeproto/`、`operators/`、`protos/`、`scripts/`、`tests/`：Python 层代码和测试，保留
  - 当前 CMakeLists.txt 依赖外部 caffex 库（CAFFE_LIBRARY/CAFFE_INCLUDE_DIR）、Boost.Python、glog、gflags

## Functional Requirements
- **FR-1**: 提供最小兼容层头文件（`include/caffe/compat/`），将 glog/boost API 映射到 tvm-ffi + C++17 std:: 实现
- **FR-2**: 核心抽象（Blob、SyncedMemory、Layer、Net、Solver 头文件和源文件）完成依赖替换，无 boost/glog/gflags 引用
- **FR-3**: 必要的 util 组件（math_functions、common、blocking_queue、internal_thread、benchmark、io、signal_handler、rng、upgrade_proto、format、device_alternate、filler、insert_splits、db stub）完成依赖替换
- **FR-4**: 核心推理 Layer 实现（推理路径所需的常用层：NeuronLayer 基类、ReLU、Convolution、Pooling、InnerProduct、Softmax、SoftmaxWithLoss、BatchNorm、Scale、Eltwise、Concat、Split、Dropout、Reshape、Flatten、Accuracy、ArgMax、Input、MemoryData 等）完成依赖替换
- **FR-5**: 重写 `python/pycaffe/python/pycaffe/_caffe.cpp` 为 tvm-ffi FFI 导出模块（移除所有 boost::python 代码，使用 `TVM_FFI_DLL_EXPORT_TYPED_FUNC` 导出 C ABI 函数），采用 handle（uintptr_t/void*）模式管理 Net/Blob/Solver 对象，使用 tvm::ffi::Tensor（DLPack）传递张量数据
- **FR-6**: 提供统一的 `python/CMakeLists.txt` 构建系统，编译：(1) Caffe 核心静态库（caffe_core），(2) tvm-ffi FFI 共享库（_caffe_ffi 或保持 _caffe 名称），正确链接 tvm-ffi、protobuf、BLAS（OpenBLAS），启用 C++17，不依赖 boost/glog/gflags
- **FR-7**: 适配 Python 层（pycaffe.py）使用新的 tvm-ffi FFI 接口加载（通过 `tvm_ffi.load_module`），保持对上层用户（tests/、operators/）的 API 兼容
- **FR-8**: 完全移除 glog、gflags、boost 的所有引用和链接依赖（包括 _caffe.cpp 中的 boost::python 相关代码）

## Non-Functional Requirements
- **NFR-1（编译）**: 瘦身代码在 C++17 编译器（GCC 8+/Clang 10+/MSVC 2019+）下编译无错误，不依赖 boost-devel、libgoogle-glog-dev、libgflags-dev
- **NFR-2（功能等价）**: 替换后的 Blob/Layer/Net 核心推理逻辑与原始 caffex 行为一致（前向计算数值结果相同）
- **NFR-3（性能）**: 推理性能不低于原始 caffex CPU 版本（std::shared_ptr 与 boost::shared_ptr 性能等价；tvm-ffi CHECK 宏在非错误路径零开销；tvm::ffi::Tensor 与 NumPy 通过 DLPack 零拷贝）
- **NFR-4（内存安全）**: 无内存泄漏（std::shared_ptr/RAII 自动管理；handle 模式在 Net 删除时正确释放所有资源）
- **NFR-5（代码规范）**: 遵循现有 caffex 代码风格（命名、缩进、宏定义模式），不引入新的第三方依赖
- **NFR-6（最小依赖）**: 瘦身核心库外部依赖仅有：C++17 标准库、tvm-ffi、protobuf、BLAS（OpenBLAS/cblas）
- **NFR-7（构建效率）**: 相比 caffex 完整构建，pycaffe 构建时间显著减少（无 boost 头文件解析开销）

## Constraints
- **Technical**: C++17 标准（由 tvm-ffi 强制）；CPU_ONLY 模式；不修改 caffex/ 原文件；tvm-ffi FFI 不直接暴露 C++ 类，需用 handle 模式
- **Business**: 代码放置到 `external/chaos/caffe/python/` 目录，与现有 Python 层整合；保持开源 License 声明；保持 Python 层对 tests/ 的兼容性
- **Dependencies**: tvm-ffi（已有）、protobuf（已有）、BLAS/OpenBLAS（已有）、Python3 + NumPy（已有）、tvm-ffi Python 端（已有）

## Assumptions
- tvm-ffi 可作为 CMake 子项目通过 `add_subdirectory` 引入（路径：`external/ffi/tvm-ffi`）
- protobuf 生成的 `caffe.pb.h/cc` 可从 caffex 构建产物中获取，或在构建时使用 protoc 重新生成（proto 文件从 caffex/src/caffe/proto/caffe.proto 复制）
- 推理核心 Layer 集合为：NeuronLayer 基类 + ReLU/Sigmoid/TanH + Conv/Pool/FC + Softmax/SoftmaxLoss + BatchNorm/Scale + Eltwise/Concat/Split/Dropout/Reshape/Flatten + Accuracy/ArgMax + Input/MemoryData
- `boost::python` 的 Python 层类注册（Net/Blob/Solver 等 bp::class_）改用 handle 模式：导出创建/销毁/成员函数调用的 C 函数，Python 端通过 tvm_ffi.load_module 加载后，用 Python 类包装 handle
- `boost::python` 的 NdarrayConverter（numpy 数组零拷贝）改用 tvm::ffi::Tensor（DLPack），Python 端通过 `tvm_ffi.Tensor` 的 `from_numpy`/`numpy()` 方法实现零拷贝
- 日志 shim 仅需支持 LOG(INFO)/LOG(WARNING)/LOG(ERROR) 三个级别（LOG(FATAL) 映射到 TVM_FFI_THROW），无需 VLOG/LOG_EVERY_N 等复杂功能
- gflags 的命令行参数（FLAGS_*）由 Python 层在调用 C++ 核心前通过配置结构体传入，或移除这些功能（如 solver_count/solver_rank 等多GPU相关在CPU_ONLY下不需要）
- Python 端（pycaffe.py）的猴子补丁模式（Net.blobs = _Net_blobs 等）可以保留，只需调整底层 `_caffe` 模块的加载方式
- 原始 _caffe.cpp 中使用的 `BP_REGISTER_SHARED_PTR_TO_PYTHON` 宏（boost::python 智能指针注册）在 tvm-ffi 中不需要（handle 模式手动管理生命周期）
- NCCL 相关代码完全移除（CPU_ONLY）
- PythonLayer（python_layer.hpp/_caffe.cpp 中的 Layer 类暴露）不保留（boost::python 专属功能），如需在 Python 中自定义 Layer 可后续通过 tvm-ffi Function 回调实现

## Acceptance Criteria

### AC-1: C++ 源码无 boost/glog/gflags 残留
- **Given**: 瘦身完成后 `python/include/` 和 `python/src/`（含 FFI 导出层 _caffe.cpp）下的所有 C++ 源文件
- **When**: 执行 grep 搜索 `#include <boost/`、`#include <glog/`、`#include <gflags/` 以及 `boost::`、`google::`、`gflags::`、`BOOST_PYTHON_MODULE`、`bp::` 符号
- **Then**: 除 compat/ 兼容层（如有必要的映射别名）外，所有源文件不包含上述引用
- **Verification**: `programmatic`

### AC-2: CMake 配置不查找 boost/glog/gflags
- **Given**: `python/CMakeLists.txt` 和其引用的 cmake 模块
- **When**: 检查 find_package 和 target_link_libraries 调用
- **Then**: 仅查找/链接 tvm-ffi、protobuf、BLAS（CBLAS）、Threads、Python（用于开发头文件，但不用于 boost::python），不包含 Boost、Glog、GFlags
- **Verification**: `programmatic`

### AC-3: C++17 编译通过
- **Given**: 使用 CMake 配置并编译瘦身核心库和 FFI 模块
- **When**: 执行 cmake 配置 + 编译
- **Then**: 编译成功无错误，无 boost/glog 相关编译或链接错误，生成共享库（_caffe_ffi.pyd/.so 或等效文件）
- **Verification**: `programmatic`

### AC-4: 核心功能可加载模型并执行前向推理
- **Given**: 一个有效的 Caffe 模型（prototxt + caffemodel），如 MNIST LeNet（lenet_deploy.prototxt）
- **When**: 通过 FFI 接口（从 Python 端调用 tvm_ffi.load_module 加载后）创建 Net、加载权重、执行 Forward
- **Then**: 前向传播成功完成，输出 Blob 数据可通过 Tensor/NumPy 获取
- **Verification**: `programmatic`

### AC-5: 兼容层 API 覆盖完整
- **Given**: 新的 compat/ 头文件
- **When**: 检查所有被替换的 API
- **Then**: shared_ptr/make_shared、mutex/unique_lock、thread、ICHECK/DCHECK、LOG_INFO/LOG_WARNING/LOG_ERROR、LOG_FATAL、barrier、fs::path、Clock/TimePoint、rng_t、split/trim/lexical_cast 均有可用替代
- **Verification**: `human-judgment`

### AC-6: CHECK 宏失败时抛出异常并输出回溯
- **Given**: 一个触发 ICHECK 失败的测试用例
- **When**: 执行触发 ICHECK 失败的代码
- **Then**: 抛出 tvm::ffi::Error 异常，异常消息包含文件/行号/条件描述和回溯信息，且通过 TVM_FFI_SAFE_CALL_BEGIN/END 安全传递到 Python 端
- **Verification**: `programmatic`

### AC-7: 目录结构符合项目规范
- **Given**: `python/` 目录结构
- **When**: 检查文件布局
- **Then**: include/caffe/ 存放头文件、src/caffe/ 存放源文件、include/caffe/compat/ 存放兼容层头文件、pycaffe/python/pycaffe/ 存放 Python 包（含重写后的 _caffe.cpp 或新的 ffi 导出文件）、CMakeLists.txt 在 python/ 根目录；现有 Python 目录（caffeproto/、operators/、protos/、scripts/、tests/）保留
- **Verification**: `human-judgment`

### AC-8: 无内存泄漏
- **Given**: 多次创建和销毁 Net 并执行 Forward
- **When**: 使用 valgrind 或 AddressSanitizer 运行测试
- **Then**: 无明确的内存泄漏报告
- **Verification**: `programmatic`

### AC-9: Python 层接口兼容
- **Given**: 适配后的 pycaffe.py 和现有 tests/test_inference.py
- **When**: 运行 test_inference.py 测试
- **Then**: 测试通过，Net/Blob 接口可用，forward() 返回正确的输出字典
- **Verification**: `programmatic`

### AC-10: FFI 模块可被 tvm_ffi 加载
- **Given**: 编译生成的 FFI 共享库
- **When**: 在 Python 中执行 `tvm_ffi.load_module("_caffe_ffi")`（或等效名称）
- **Then**: 加载成功，可以调用导出的函数（如 Net 创建、Forward 等）
- **Verification**: `programmatic`

## Open Questions
- [ ] FFI 模块名称保持 `_caffe` 还是改为 `_caffe_ffi`？（保持 `_caffe` 可最大化兼容 pycaffe.py 的 import 路径，但需要调整构建产物命名）
- [ ] Solver 代码是否需要保留？如果仅推理，Solver 相关文件可以只保留 solver.hpp 中 Net 需要的最小接口，SGDSolver 等可 stub。
- [ ] PythonLayer 是否需要保留？（当前 boost::python 专属功能，需要 Python 回调机制）—— 建议初始版本不保留，后续通过 tvm-ffi Function 回调实现
- [ ] OpenCV 是否保留？（数据层预处理可能需要，但初始版本可用 MemoryDataLayer + NumPy 输入跳过）
- [ ] `boost::python` 中 `vector_indexing_suite` 提供的 Python list <-> std::vector 自动转换，在 tvm-ffi 中通过 `ffi::Array` 类型或手动处理 std::vector<T> 参数实现
- [ ] 是否保留 db.hpp 和 db.cpp 抽象层（不保留 LMDB/LevelDB 后端，但 db.hpp 接口可能被 io.cpp 引用）—— 提供最小 stub 实现或移除相关调用
