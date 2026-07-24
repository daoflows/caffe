# Caffe C++ 核心瘦身优化（tvm-ffi 替换 glog/boost） - 实现计划

> **状态**: ✅ 已完成（2026-07-23）
> **复盘报告**: [retrospective-20260723.md](retrospective-20260723.md)
> **构建避坑指南**: [build-pitfalls-guide.md](build-pitfalls-guide.md)

---

## ⚠️ 增量构建强制规则（MANDATORY BUILD RULES）（事后补充）

> 这些规则是从本项目实战教训中萃取的。本项目执行过程中部分违反了这些规则，导致了额外返工。

1. **禁止 `file(GLOB_RECURSE ...)` 收集源文件**：必须显式列出每个源文件路径。
   - ⚠️ 本项目初期使用GLOB_RECURSE导致_caffe.cpp被错误链接进静态库，后改为显式列表修复
2. **增量添加 + 每步编译验证**：先让最小核心（5-10个文件）编译通过，再逐层添加。
   - ⚠️ 本项目初期"大爆炸式"配置CMake，错误叠加难以定位
3. **兼容层必须先写且先测**：compat/头文件在业务代码迁移之前完成，且有独立测试。
   - ⚠️ 本项目LOG(FATAL)初期用abort()而非throw，导致FFI异常安全失效
4. **每步ctest**：每完成一个Task，运行相应测试验证。
   - ⚠️ 本项目后期集中测试导致错误定位困难

---

## [x] Task 0: 环境验证与WSL构建环境准备（事后补充，实际先于Task 1执行）
- **Priority**: critical
- **Depends On**: None
- **Description**:
  - ⚠️ 初期在Windows上尝试构建失败（MSVC/SDK配置问题、POSIX函数缺失、libbacktrace CRLF问题），后切换WSL
  - 在WSL2 Ubuntu 22.04中安装构建依赖：build-essential, cmake, ninja-build, libprotobuf-dev, protobuf-compiler, libopenblas-dev
  - 验证GCC 11.4.0支持C++17
  - 创建目标目录结构：include/caffe/, include/caffe/compat/, include/caffe/layers/, include/caffe/util/, src/caffe/, src/caffe/layers/, src/caffe/util/
- **Acceptance Criteria Addressed**: NFR-1, AC-3
- **Test Requirements**:
  - `programmatic` TR-0.1: WSL中cmake + ninja配置成功
  - `programmatic` TR-0.2: 目标目录结构创建完成
- **Notes**: 环境预检必须最先完成。Linux原生C++项目优先WSL/Linux。
- **Completion Date**: 2026-07-23

## [x] Task 1: 创建C++核心目录结构和CMake基础框架
- **Priority**: high
- **Depends On**: None
- **Description**: 
  - 在 `external/chaos/caffe/python/` 下创建 C++ 源码目录：`include/caffe/`、`include/caffe/compat/`、`include/caffe/layers/`、`include/caffe/util/`、`include/caffe/proto/`、`src/caffe/`、`src/caffe/layers/`、`src/caffe/util/`、`src/caffe/proto/`、`src/caffe/solvers/`
  - 复制 proto 文件：从 `caffex/src/caffe/proto/caffe.proto` 复制到 `src/caffe/proto/caffe.proto`，在 CMake 中使用 `protobuf_generate` 生成 `caffe.pb.h/cc` 到 build 目录
  - 创建根 `python/CMakeLists.txt`：
    - 设置 `cmake_minimum_required(VERSION 3.18)`、`project(caffe_python)`、`CXX_STANDARD 17`
    - 添加 `add_subdirectory` 引入 tvm-ffi（路径 `../../ffi/tvm-ffi`）
    - 查找依赖：`find_package(Protobuf REQUIRED)`、查找 BLAS（OpenBLAS 或系统 CBLAS）、`find_package(Threads REQUIRED)`
    - 定义编译选项：`CPU_ONLY`、`CAFFE_VERSION`
    - 定义 caffe_core 静态库目标
    - 定义 _caffe_ffi 共享库目标（FFI 导出模块，输出名为 `_caffe` 以兼容现有 Python import 路径）
  - 更新 pycaffe/pyproject.toml 和 pycaffe/CMakeLists.txt（或新建 pycaffe 的 CMake 集成），让 scikit-build-core 使用新的顶层 CMakeLists
  - 添加 LICENSE 文件（BSD 2-Clause，从 caffex 复制）
- **Acceptance Criteria Addressed**: AC-2, AC-7
- **Test Requirements**:
  - `programmatic` TR-1.1: CMake configure 成功，未报错，找到了 tvm-ffi、protobuf、BLAS、Threads
  - `human-judgment` TR-1.2: 目录结构符合 include/src 分层规范，与 caffex 结构一致但精简
  - `human-judgment` TR-1.3: CMakeLists.txt 中无 find_package(Boost)/find_package(Glog)/find_package(GFlags)
- **Notes**: tvm-ffi 路径相对于 python/ 为 `../../ffi/tvm-ffi`（python/ → external/chaos/caffe/ → external/chaos/ → external/ → external/ffi/tvm-ffi），需验证相对路径正确性

## [x] Task 2: 创建 compat 兼容层头文件
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 创建 `include/caffe/compat/logging.hpp`：定义 LOG(INFO)/LOG(WARNING)/LOG(ERROR) 宏（基于 std::cerr + 严重性前缀 `[I/W/E] filename:line]`），LOG(FATAL) 映射到 TVM_FFI_THROW(RuntimeError)；定义 NOT_IMPLEMENTED 宏；定义 LOG_EVERY_N（可简化为直接 LOG）；不使用 glog 的 InitGoogleLogging（改为简单初始化）
  - 创建 `include/caffe/compat/check_macros.hpp`：将 CHECK/DCHECK/CHECK_EQ/CHECK_NE/CHECK_LT/CHECK_LE/CHECK_GT/CHECK_GE/CHECK_NOTNULL/CHECK_DOUBLE_EQ/CHECK_NEAR 映射到 TVM_FFI_ICHECK/TVM_FFI_DCHECK 系列宏
  - 创建 `include/caffe/compat/smart_ptr.hpp`：`namespace caffe { using std::shared_ptr; using std::weak_ptr; using std::unique_ptr; using std::make_shared; using std::dynamic_pointer_cast; using std::static_pointer_cast; }`
  - 创建 `include/caffe/compat/thread.hpp`：包装 std::thread、std::mutex、std::condition_variable、std::unique_lock、std::lock_guard、std::this_thread::sleep_for、std::this_thread::yield、std::atomic_bool/atomic_int、提供 Barrier 简单实现（condition_variable + counter）
  - 创建 `include/caffe/compat/filesystem.hpp`：`namespace caffe { namespace fs = std::filesystem; }`
  - 创建 `include/caffe/compat/function.hpp`：`using std::function; using std::bind; using namespace std::placeholders;`
  - 创建 `include/caffe/compat/chrono.hpp`：`using Clock = std::chrono::high_resolution_clock; using TimePoint = std::chrono::time_point<Clock>;` 提供 Timer 类（封装 chrono）
  - 创建 `include/caffe/compat/random.hpp`：`using rng_t = std::mt19937;` 提供 uniform_real/bernoulli 等分布类型别名
  - 创建 `include/caffe/compat/string_utils.hpp`：内联实现 split、trim、lexical_cast 等工具函数（替换 boost::algorithm::split/trim、boost::lexical_cast）
  - 创建 `include/caffe/compat/thread_local.hpp`：使用 C++11 `thread_local` 关键字实现模板类 ThreadLocalPtr 替代 boost::thread_specific_ptr
  - 创建 `include/caffe/compat/math.hpp`：inline float/double caffe_nextafter 实现（使用 std::nextafter）
- **Acceptance Criteria Addressed**: AC-5, AC-6
- **Test Requirements**:
  - `programmatic` TR-2.1: 编写一个小测试程序（tests/test_compat.cpp），include 所有 compat 头文件，使用 CHECK/LOG/shared_ptr/thread/mutex/fs/Barrier/Timer 等，编译通过并运行
  - `programmatic` TR-2.2: ICHECK(false) 触发时抛出 tvm::ffi::Error 异常，消息包含行号和条件表达式
  - `human-judgment` TR-2.3: compat 头文件不 include 任何 boost/glog/gflags 头文件（检查 #include 语句）
- **Notes**: 所有 compat 头文件必须是 header-only，不引入额外 .cpp 文件；Barrier 使用 condition_variable + counter 实现（等待所有线程到达后统一放行）

## [x] Task 3: 重写 common.hpp/common.cpp（Caffe单例和全局初始化）
- **Priority**: high
- **Depends On**: Task 2
- **Description**: 
  - 基于 caffex 的 `include/caffe/common.hpp` 重写到 `caffe-slim/include/caffe/common.hpp`：
    - 替换 `#include <boost/shared_ptr.hpp>` 为 `#include "caffe/compat/smart_ptr.hpp"`
    - 替换 `#include <glog/logging.h>` 为 `#include "caffe/compat/logging.hpp"` 和 `#include "caffe/compat/check_macros.hpp"`
    - 移除 gflags 依赖（删除 `#include <gflags/gflags.h>`、`namespace gflags=google` 别名）
    - 将 `boost::thread_specific_ptr<Caffe>` 替换为 compat/thread_local.hpp 中的 ThreadLocalPtr
    - 保留 DISABLE_COPY_AND_ASSIGN、INSTANTIATE_CLASS、NOT_IMPLEMENTED 宏
    - 保留 Caffe 单例类（Brew模式、RNG）；CUBLAS/curand 句柄在 CPU_ONLY 模式下声明但不使用
    - 移除 GlobalInit 中对 gflags::ParseCommandLineFlags 和 google::InitGoogleLogging/InstallFailureSignalHandler 的调用，改为空操作或简单日志初始化
  - 重写 `src/caffe/common.cpp`：
    - 移除 `#include <boost/thread.hpp>`，替换为 `#include "caffe/compat/thread.hpp"`
    - 移除 gflags 相关代码
    - Caffe::SetDevice/DeviceQuery 等 GPU 相关在 CPU_ONLY 下 stub 为 NO_GPU
    - 保持 RNG 初始化和 Brew 模式逻辑不变
- **Acceptance Criteria Addressed**: AC-1, AC-5
- **Test Requirements**:
  - `programmatic` TR-3.1: common.hpp 能正确 include 且编译通过，无 boost/glog/gflags 符号
  - `programmatic` TR-3.2: Caffe::Get() 返回单例引用，Caffe::set_mode()/mode() 工作正常
  - `human-judgment` TR-3.3: gflags 相关代码（ParseCommandLineFlags、FLAGS_*）已完全移除

## [x] Task 4: 迁移和瘦身核心抽象头文件（SyncedMemory/Blob/Layer/Net/Solver/util）
- **Priority**: high
- **Depends On**: Task 3
- **Description**: 
  - 从 caffex 复制并修改以下头文件到 `caffe-slim/include/caffe/`：
    - `syncedmem.hpp`：替换 boost/glog 引用为 compat 头文件，保留 SyncedMemory 类（UNINITIALIZED/HEAD_AT_CPU/HEAD_AT_GPU/SYNCED 四状态懒同步）
    - `blob.hpp`：Blob<Dtype> 类（data_/diff_ dual storage、Reshape、Forward/Backward）
    - `layer.hpp`：Layer<Dtype> NVI 生命周期（SetUp/Forward/Backward），移除 boost::thread 前向声明
    - `net.hpp`：Net<Dtype> DAG 拓扑结构
    - `solver.hpp`：替换 boost::function 为 std::function，Solver<Dtype> 接口保留（可简化）
    - `layer_factory.hpp`：移除 boost::python 相关的 BP_REGISTER_LAYER 宏，保留 C++ 自注册工厂（LayerRegistry）
    - `solver_factory.hpp`
    - `filler.hpp`
    - `data_transformer.hpp`（简化版，CPU_ONLY）
    - `caffe.hpp`（主 include 头文件）
  - 从 caffex 复制并修改 util 头文件到 `caffe-slim/include/caffe/util/`：
    - `device_alternate.hpp`：CPU_ONLY 模式下 CUDA 宏定义为 NO_GPU
    - `math_functions.hpp`：移除 boost/math 依赖，使用 std:: 和 cblas
    - `blocking_queue.hpp`：替换 boost::mutex/condition_variable
    - `benchmark.hpp`：替换 boost::posix_time 为 compat/chrono.hpp Timer
    - `format.hpp`、`insert_splits.hpp`、`mkl_alternate.hpp`
    - `io.hpp`：替换 boost::filesystem 为 compat/filesystem.hpp
    - `rng.hpp`：替换 boost::random 为 compat/random.hpp
    - `signal_handler.h`：替换 boost::bind 为 std::bind/lambda
    - `upgrade_proto.hpp`：替换 boost::filesystem
    - `db.hpp`：保留 db 抽象基类（DB/Transaction/Cursor），LMDB/LevelDB 后端不实现（返回 nullptr 或 stub）
    - 不迁移：`cudnn.hpp`、`gpu_util.cuh`、`hdf5.hpp`、`db_leveldb.hpp`、`db_lmdb.hpp`、`nccl.hpp`、`parallel.hpp`（parallel 可简化或不迁移）、`performance.hpp`、`bench_fb.hpp`、`im2col.cuh`、`device_alternate.hpp` 的 GPU 部分
  - 复制 `proto/caffe.proto` 用于构建期生成
- **Acceptance Criteria Addressed**: AC-1, AC-5
- **Test Requirements**:
  - `programmatic` TR-4.1: 所有头文件能独立 include 编译通过（编译测试：每个头文件单独写一个 .cpp 只 include 它）
  - `programmatic` TR-4.2: grep 确认头文件中无 boost::/glog/gflags/BOOST_PYTHON_MODULE 引用
  - `human-judgment` TR-4.3: 核心类接口（Blob::Reshape/Forward/Backward, Layer::SetUp/Forward/Backward, Net::Forward/Init）保持与原始一致

## [x] Task 5: 迁移核心抽象源文件
- **Priority**: high
- **Depends On**: Task 4
- **Description**: 
  - 从 caffex 复制并修改以下源文件到 `caffe-slim/src/caffe/`：
    - `syncedmem.cpp`
    - `blob.cpp`
    - `layer.cpp`
    - `net.cpp`
    - `solver.cpp`：移除 boost::split/boost::is_any_of/boost::trim/boost::lexical_cast，用 compat/string_utils.hpp 的 inline 函数替代
    - `data_transformer.cpp`（CPU_ONLY 简化版）
    - `layer_factory.cpp`：移除 boost::python 相关代码（BP_REGISTER_LAYER 宏、python_layer.hpp 引用），保留 C++ 层注册
    - `internal_thread.cpp` 和 `internal_thread.hpp`：替换 boost::thread/boost::thread_interrupted 为 std::thread + std::atomic<bool> stop_ flag
  - 从 caffex 复制并修改 util 源文件到 `caffe-slim/src/caffe/util/`：
    - `math_functions.cpp`：移除 boost::math/nextafter 和 boost::random，使用 std::nextafter 和 compat/random.hpp；移除 GPU 代码
    - `blocking_queue.cpp`：替换 boost::mutex/condition_variable/scoped_lock
    - `benchmark.cpp`：替换 boost::posix_time 为 compat/chrono.hpp
    - `io.cpp`：替换 boost::filesystem 为 compat/filesystem.hpp，移除 HDF5/LMDB/LevelDB 相关的 save/load 函数（保留 proto 读写）
    - `signal_handler.cpp`：替换 boost::bind 为 std::bind 或 lambda
    - `upgrade_proto.cpp`：替换 boost::filesystem
    - `db.cpp`：保留 DB 基类实现，提供简单的 stub 或移除不需要的后端
    - `insert_splits.cpp`、`format.cpp`
    - `filler.cpp`（在 src/caffe/ 下）
    - 不迁移：`im2col.cu`、`math_functions.cu`、`cudnn.cpp`、`parallel.cpp`（如有 OpenMP 可保留或简化为单线程）、`hdf5.cpp`、`db_leveldb.cpp`、`db_lmdb.cpp`、`nccl.cpp`
  - 生成 `caffe.pb.cc`/`caffe.pb.h`（通过 CMake protobuf_generate）
- **Acceptance Criteria Addressed**: AC-1, AC-3
- **Test Requirements**:
  - `programmatic` TR-5.1: 所有 .cpp 文件编译通过，无 boost/glog/gflags 链接错误
  - `programmatic` TR-5.2: caffe_core 静态库成功生成
  - `human-judgment` TR-5.3: 核心业务逻辑（SyncedMemory 状态转换、Blob 数据访问、层工厂注册、Net DAG 初始化）未被修改

## [x] Task 6: 迁移核心推理 Layers
- **Priority**: high
- **Depends On**: Task 5
- **Description**: 
  - 首先迁移 Layer 基类相关头文件到 `caffe-slim/include/caffe/layers/`：
    - `neuron_layer.hpp`、`loss_layer.hpp`、`base_data_layer.hpp`、`base_conv_layer.hpp`、`data_layer.hpp`、`memory_data_layer.hpp`、`input_layer.hpp`
  - 迁移核心推理层的 .hpp 和 .cpp（仅 CPU 版本，不迁移 .cu 文件）到 `caffe-slim/src/caffe/layers/` 及对应 include 目录：
    - neuron_layer.cpp + relu_layer、sigmoid_layer、tanh_layer、elu_layer、prelu_layer、absval_layer、bnll_layer、power_layer、exp_layer、log_layer、threshold_layer、swish_layer（部分简单层可只保留常用的）
    - conv_layer.cpp + inner_product_layer.cpp + base_conv_layer.cpp + im2col.cpp（CPU实现）
    - pooling_layer.cpp
    - softmax_layer.cpp + softmax_loss_layer.cpp
    - batch_norm_layer.cpp + scale_layer.cpp
    - eltwise_layer.cpp、concat_layer.cpp、split_layer.cpp、dropout_layer.cpp、slice_layer.cpp
    - reshape_layer.cpp、flatten_layer.cpp
    - accuracy_layer.cpp、argmax_layer.cpp
    - input_layer.cpp、memory_data_layer.cpp（BaseDataLayer 的简化实现）
    - 不迁移：所有 `*_cu.cpp`/`*.cu`、`cudnn_*_layer.cpp`、`python_layer.*`、`hdf5_*_layer.*`、`lmdb_data_layer.*`、`leveldb_data_layer.*`、`window_data_layer.*`、`lstm_layer.*`、`rnn_layer.*`、`recurrent_layer.*`、`detection_*_layer.*`、`roi_*_layer.*`、`nms_layer.*`、`smooth_l1_loss.*`、`spp_layer.*`、`yolo_*layer.*` 等训练/特殊层
  - 为每个层替换 boost/glog 引用为 compat 头文件
  - 在 `layer_factory.cpp` 中为所有迁移的层添加 INSTANTIATE_CLASS 和 REGISTER_LAYER_CLASS 宏
- **Acceptance Criteria Addressed**: AC-1, AC-3, AC-4
- **Test Requirements**:
  - `programmatic` TR-6.1: 所有迁移的 Layer 编译通过，链接到 caffe_core 静态库
  - `programmatic` TR-6.2: LayerRegistry 能正确查询并创建迁移的所有层类型（通过 CreateLayer 测试）
  - `human-judgment` TR-6.3: 核心推理路径（Conv→BN→Scale→ReLU→Pooling→FC→Softmax）所需层均已覆盖

## [x] Task 7: 迁移 Solver（推理最小化）
- **Priority**: medium
- **Depends On**: Task 6
- **Description**: 
  - 迁移 `src/caffe/solvers/sgd_solver.cpp` 和对应头文件（核心SGD求解器，推理时可能不需要但 Net 加载权重可直接用 Net::CopyTrainedLayersFrom，Solver 仅用于可选的微调场景）
  - 其他 solver（adam、adagrad、rmsprop、nesterov、adadelta）不迁移或只提供空壳 stub（头文件声明但无 .cpp 实现）
  - 如果目标仅为推理，Solver 可以只保留接口，实际不链接 solver .cpp 文件
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-7.1: solver.hpp 包含后编译通过（即使 solver.cpp 不完整也不影响 Net 推理）
  - `human-judgment` TR-7.2: Solver 接口保持可用（推理不需要但构建不报错）

## [x] Task 8: 重写 _caffe.cpp 为 tvm-ffi FFI 导出模块
- **Priority**: high
- **Depends On**: Task 6
- **Description**: 
  - 重写 `caffe-slim/pycaffe/python/pycaffe/_caffe.cpp`（原 boost::python 绑定），完全移除 boost::python 相关代码（`#include <boost/python.hpp>`、`BOOST_PYTHON_MODULE`、`bp::` 命名空间、`vector_indexing_suite`、`NdarrayConverter` 等）
  - 改为使用 tvm-ffi 导出机制（`TVM_FFI_DLL_EXPORT_TYPED_FUNC`），采用 opaque handle 模式：
    - 定义 `using NetHandle = uintptr_t;`、`using BlobHandle = uintptr_t;`（包装指针）
    - 导出函数：
      - `CaffeVersion() -> std::string`
      - `CaffeSetModeCPU()` / `CaffeSetModeGPU()`（GPU 模式 stub）
      - `CaffeSetRandomSeed(seed: int)`
      - `NetInit(model_path: str, phase: int, weights_path: str) -> NetHandle`：创建 Net，加载 prototxt 和 weights，返回 handle
      - `NetForward(handle: NetHandle) -> None`：执行 Net::Forward
      - `NetReshape(handle: NetHandle) -> None`
      - `NetCopyFrom(handle: NetHandle, weights_path: str) -> None`
      - `NetGetBlobNames(handle: NetHandle) -> ffi::Array<std::string>`：返回所有 blob 名称
      - `NetGetLayerNames(handle: NetHandle) -> ffi::Array<std::string>`
      - `NetGetBlobShape(handle: NetHandle, name: str) -> ffi::Array<int64_t>`：返回指定 blob 形状
      - `NetGetBlobData(handle: NetHandle, name: str) -> ffi::Tensor`：返回 blob 的 cpu data 作为 ffi::Tensor（零拷贝，共享 Caffe Blob 的内存，使用 Tensor::FromNDAlloc 或创建 unsafe view）
      - `NetSetBlobData(handle: NetHandle, name: str, tensor: ffi::Tensor)`：设置输入 blob 数据（从 Tensor 复制到 Blob cpu_data）
      - `NetSetInputArrays(handle: NetHandle, data: ffi::Tensor, labels: ffi::Tensor)`：MemoryDataLayer 设置数据
      - `NetDelete(handle: NetHandle) -> None`：销毁 Net
      - `GetSolverCount()/SetSolverCount()/GetSolverRank()/SetSolverRank()/SetMultiprocess()/SetDevice()`：多GPU stubs
      - `HasNCCL() -> bool`（返回 false）
      - `TimerCreate() -> uintptr_t` / `TimerStart(handle)` / `TimerStop(handle)` / `TimerMilliSeconds(handle) -> double` / `TimerDelete(handle)`
    - 所有导出函数使用 `TVM_FFI_SAFE_CALL_BEGIN/END` 包裹，异常通过安全调用机制传递
  - 移除所有 NCCL 相关代码（HasNCCL 返回 false，NCCL 类不导出）
  - 移除 Solver 各种子类（SGDSolver/NesterovSolver 等）的 bp::class_ 导出（如需保留 Solver 接口，添加 handle 模式导出：SolverCreateFromFile -> SolverHandle, SolverSolve, SolverStep, SolverGetNet 等）
  - 移除 PythonLayer、Callback 相关代码（SolverCallback/NetCallback）
  - tensor 传递：将 Caffe Blob 的 cpu_data() 包装为 DLTensor（data 指针直接指向 Blob 内存），通过 `TVMFFITensorCreateUnsafeView` 或自定义方式创建 ffi::Tensor 视图，确保不拷贝数据
  - 移除 `#include <Python.h>` 和 `#include <numpy/arrayobject.h>`（不再使用 CPython API，tvm-ffi 提供跨语言绑定）
- **Acceptance Criteria Addressed**: AC-1, AC-4, AC-10
- **Test Requirements**:
  - `programmatic` TR-8.1: _caffe.cpp 编译成功（无 boost::python、Python.h 依赖），生成共享库 _caffe.pyd/.so
  - `programmatic` TR-8.2: 使用 nm/objdump 检查导出符号包含 `__tvm_ffi_` 前缀的函数
  - `programmatic` TR-8.3: C++ 测试程序能通过 FFI 函数创建 Net、执行 Forward、获取输出 Blob 数据
  - `human-judgment` TR-8.4: _caffe.cpp 中无 bp:: 或 boost::python 引用

## [x] Task 9: 统一 CMake 构建和编译验证
- **Priority**: high
- **Depends On**: Task 8
- **Description**: 
  - 完善根 `python/CMakeLists.txt`：
    - 将所有 C++ 源文件加入 caffe_core 静态库
    - 添加编译选项：CPU_ONLY 定义、C++17、-Wall -Wextra（MSVC 下 /W3）
    - 正确配置 include 路径（include/、build/ 生成的 protobuf 目录）
    - target_link_libraries: tvm_ffi、protobuf::libprotobuf、BLAS（cblas/openblas）、Threads::Threads
    - _caffe 共享库链接 caffe_core 静态库和 tvm_ffi
    - 添加 install 目标（将 _caffe 共享库安装到 pycaffe/python/pycaffe/ 目录）
  - 在 Windows 环境下进行编译验证（使用 MSVC 或 MinGW）
  - 确保 ffi 共享库输出名为 `_caffe`（无 lib 前缀，.pyd 后缀 on Windows，.so on Linux），与 Python import 路径兼容
  - 更新 pycaffe/CMakeLists.txt（如果需要保留 scikit-build 集成），让顶层 CMake 管理构建
  - 生成 compile_commands.json 供 IDE 使用
- **Acceptance Criteria Addressed**: AC-2, AC-3
- **Test Requirements**:
  - `programmatic` TR-9.1: cmake configure 无错误无警告
  - `programmatic` TR-9.2: cmake --build 成功编译 caffe_core 静态库和 _caffe 共享库（0 errors）
  - `programmatic` TR-9.3: 链接成功，无 boost/glog/gflags 未定义引用错误
  - `human-judgment` TR-9.4: CMakeLists.txt 不包含 Boost/Glog/GFlags 查找/链接逻辑

## [x] Task 10: 适配 Python 层（pycaffe.py）使用 tvm-ffi
- **Priority**: high
- **Depends On**: Task 9
- **Description**: 
  - 修改 `caffe-slim/pycaffe/python/pycaffe/__init__.py` 和 `pycaffe.py`：
    - 将 `from ._caffe import Net, SGDSolver, ...` 改为通过 tvm_ffi 加载 _caffe 模块
    - 编写 Python 包装类：`Net`、`Blob`、`Timer` 等，持有 handle 并在 __del__ 中调用 Delete 函数
    - Net 类封装：`__init__(model_file, phase, weights=None)` → 调用 NetInit；`forward()` → 调用 NetForward + 获取输出 Blob 转为 numpy；`blobs` 属性返回 OrderedDict of Blob 包装；`layers` 属性等
    - Blob 包装类：`data` 属性返回 numpy 数组（通过 Tensor.numpy() 零拷贝）；`shape` 属性；`reshape()` 方法
    - 保留原有的猴子补丁方法（_Net_blobs、_Net_forward、_Net_backward 等），只需适配底层 _forward/_backward 调用
    - 对于 backward（推理模式下可能不需要，SoftmaxWithLoss 用 forward 即可计算 loss，但 backward 用于训练）—— 推理模式下 backward 可 stub 或提供最小实现
    - 模式设置（set_mode_cpu/set_mode_gpu）→ 调用 CaffeSetModeCPU/stub
  - 移除/调整 `classifier.py`、`detector.py` 中对旧 _caffe API 的依赖（如需保留可适配）
  - 更新 `pyproject.toml` 添加 tvm-ffi Python 包依赖
  - 确保 Python 端通过 `import tvm_ffi` 加载模块，路径指向编译生成的 _caffe 共享库位置
- **Acceptance Criteria Addressed**: AC-9, AC-10
- **Test Requirements**:
  - `programmatic` TR-10.1: `import pycaffe` 成功（无 ImportError）
  - `programmatic` TR-10.2: pycaffe.Net 可以从 lenet_deploy.prototxt 创建（有 weights 可加载，没有则跳过权重加载）
  - `human-judgment` TR-10.3: Python 层 API 尽量保持向后兼容（forward 返回字典，blobs 可访问 data 属性）
- **Notes**: 由于 tvm-ffi 加载的模块不直接是 Python C extension，需要通过 tvm_ffi.load_module 加载并包装。Python Net/Blob 类是纯 Python 类，通过 handle 调用底层 FFI 函数

## [x] Task 11: 编写C++冒烟测试和Python端到端测试
- **Priority**: high
- **Depends On**: Task 10
- **Description**: 
  - C++ 测试：创建 `caffe-slim/tests/cpp/` 目录
    - `test_blob.cpp`：验证 Blob 创建、Reshape、cpu_data() 读写
    - `test_net.cpp`：使用代码方式创建简单网络（Input→InnerProduct→Softmax），执行 Forward，验证输出
    - `test_check.cpp`：验证 ICHECK 宏失败时抛出 tvm::ffi::Error
    - `test_logging.cpp`：验证日志宏可正常使用不崩溃
    - `test_thread.cpp`：验证 BlockingQueue 和 InternalThread 替换
  - Python 测试：运行现有 `caffe-slim/tests/test_inference.py`，验证端到端推理可用
  - 配置 CTest 集成运行 C++ 测试
- **Acceptance Criteria Addressed**: AC-4, AC-6, AC-8, AC-9
- **Test Requirements**:
  - `programmatic` TR-11.1: C++ 测试编译并通过（ctest 输出 100% passed）
  - `programmatic` TR-11.2: CHECK 失败测试确实抛出 tvm::ffi::Error 异常
  - `programmatic` TR-11.3: test_inference.py 运行通过（或在没有预训练权重的情况下，至少能创建网络并执行 Forward）
  - `human-judgment` TR-11.4: 测试覆盖核心功能（Blob/Net/Layer/thread/FFI）

## [x] Task 12: 无残留依赖验证和清理
- **Priority**: high
- **Depends On**: Task 9
- **Description**: 
  - 对 `caffe-slim/include/`、`caffe-slim/src/`、`caffe-slim/pycaffe/python/pycaffe/_caffe.cpp` 下所有 .hpp/.cpp/.cc/.h 文件执行 grep，确认无 boost::/glog/gflags 残留
  - 检查 CMakeLists.txt 和 cmake/ 目录确认无 find_package(Boost)/find_package(Glog)/find_package(GFlags)
  - 确认 target_link_libraries 中没有 boost_*/glog/gflags 库
  - 运行 `dumpbin /dependents`（Windows）或 `ldd`（Linux）检查生成的 _caffe 共享库，确认不依赖 boost_*-mt/boost_python/glog/gflags DLL
  - 删除原始 pycaffe/CMakeLists.txt 中查找 CAFFE_LIBRARY 外部库的逻辑（因为现在 C++ 核心内嵌到 python/ 构建中）
  - 如有残留，逐一修复
- **Acceptance Criteria Addressed**: AC-1, AC-2
- **Test Requirements**:
  - `programmatic` TR-12.1: `grep -rn "boost::\|#include <boost\|BOOST_PYTHON_MODULE\|bp::"` caffe-slim/include caffe-slim/src caffe-slim/pycaffe/python/pycaffe/_caffe.cpp 返回空（compat 头文件中 using 别名除外）
  - `programmatic` TR-12.2: `grep -rn "glog\|#include <glog\|google::InitGoogleLogging\|google::InstallFailureSignalHandler\|FLAGS_" caffe-slim/include caffe-slim/src caffe-slim/pycaffe/python/pycaffe/_caffe.cpp` 返回空
  - `programmatic` TR-12.3: `grep -rn "find_package.*[Bb]oost\|find_package.*[Gg]log\|find_package.*[Gg]flags" python/CMakeLists.txt caffe-slim/pycaffe/CMakeLists.txt` 返回空
  - `programmatic` TR-12.4: dumpbin/ldd 检查 _caffe 共享库无 boost_glog_gflags 动态依赖
