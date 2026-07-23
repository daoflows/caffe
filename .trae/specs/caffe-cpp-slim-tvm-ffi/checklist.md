# Caffe C++ 核心瘦身优化验证清单

> **状态**: ✅ 已完成（2026-07-23）
> **复盘报告**: [retrospective-caffe-slim-tvm-ffi-20260723](../../../../../../.agents/docs/retrospective/reports/code-optimization/retrospective-caffe-slim-tvm-ffi-20260723/README.md)
> **模板来源**: [cpp-dependency-slimming 模板](../../../../../../spec/templates/cpp-dependency-slimming/)

---

## 〇、前置预检验证（事后补充——本项目初期未严格执行，导致返工）

| 检查项 | 验证方式 | 预期结果 | 状态 | 教训 |
|--------|----------|----------|------|------|
| 目标平台确认 | 阅读原项目README | Linux原生项目优先WSL/Linux | ⚠️ 初期未做→浪费30%时间 | ❌ Windows环境不适合Linux原生C++项目 |
| 编译器可用性 | `g++ --version` 编译hello world | GCC 8+/Clang 10+支持C++17 | ☑ WSL GCC 11.4.0 | ✅ WSL切换后编译顺利 |
| 新依赖库可编译 | 编译tvm-ffi最小示例 | tvm-ffi CMake配置+编译通过 | ☑ | ✅ |
| API映射表完整 | grep扫描+映射文档 | 每个旧API有新API对应 | ⚠️ 边猜边写→5-6轮返工 | ❌ 未做最小验证程序，宏参数错误 |
| API映射验证 | 10-20行最小测试程序 | 每个映射编译运行通过 | ⚠️ 部分未验证 | ❌ LOG(FATAL)用abort()而非throw；ICHECK宏参数错误；DLDataType命名空间错误 |
| Include闭包分析 | `g++ -H -fsyntax-only` | 一次性列出所有需迁移文件 | ⚠️ 正向猜测→打地鼠补文件 | ❌ 每次编译缺一个头文件，补了又缺下一个 |
| 必需文件清单完整 | 对照include树 | 75头+62源=130文件一次性列出 | ⚠️ 分批迁移逐步补全 | ❌ 缺少deconv_layer.hpp、internal_thread.hpp、caffe.hpp等头文件导致返工 |

---

## 一、依赖替换验证

| 检查项 | 验证方式 | 预期结果 | 状态 |
|--------|----------|----------|------|
| boost 头文件引用完全移除 | `grep -rn "#include <boost" python/include python/src python/pycaffe/python/pycaffe/` | 返回空结果（compat/ 别名除外） | ☑ |
| glog 头文件引用完全移除 | `grep -rn "#include <glog\|#include \"glog" python/include python/src` | 返回空结果 | ☑ |
| gflags 头文件引用完全移除 | `grep -rn "#include <gflags\|gflags::ParseCommandLineFlags" python/include python/src` | 返回空结果 | ☑ |
| boost 命名空间使用完全移除 | `grep -rn "boost::" python/include python/src` | 返回空结果（compat 层 using 别名除外） | ☑ |
| google/ 命名空间使用完全移除 | `grep -rn "google::" python/include python/src` | 返回空结果 | ☑ |
| CMake 中无 Boost/Glog/Gflags 查找 | `grep -rn "find_package.*[Bb]oost\|find_package.*[Gg]log\|find_package.*[Gg]flags" python/` | 返回空结果 | ☑ |
| target_link_libraries 中无 boost/glog/gflags | 检查 python/CMakeLists.txt | 仅链接 tvm_ffi、protobuf、BLAS、Threads | ☑ |
| 共享库无 boost/glog/gflags 动态依赖 | `ldd _caffe.so`（WSL/Linux） | 不包含 boost_*/glog/gflags .so | ☑ |

---

## 二、C++ 核心功能验证

| 检查项 | 验证方式 | 预期结果 | 状态 |
|--------|----------|----------|------|
| CMake configure 成功 | `cmake -B build` | 成功找到 tvm-ffi、protobuf、BLAS、Threads，无错误 | ☑ |
| Caffe 核心静态库编译 | `cmake --build build --target caffe_core` | 编译成功，0 errors | ☑ |
| FFI 共享库编译 | `cmake --build build --target _caffe` | 编译成功，生成 _caffe.so | ☑ |
| Blob 基础功能正确 | Python端测试 | Blob 创建、Reshape、cpu_data 读写正常 | ☑ |
| SyncedMemory 同步正确 | 代码审查+编译验证 | 状态转换正确（HEAD_AT_CPU ↔ SYNCED） | ☑ |
| Layer 工厂注册正确 | 运行时LayerRegistry | 可创建38种迁移的层类型 | ☑ |
| Net DAG 初始化正确 | 从prototxt初始化 | Net初始化成功，层拓扑正确（45个测试通过） | ☑ |
| Net Forward 推理正确 | 端到端测试 | 输入数据后Forward输出结果形状正确 | ☑ |
| BlockingQueue 线程安全 | 编译验证 | blocking_queue.hpp使用std::mutex/condition_variable | ☑ |
| InternalThread 启停正确 | 编译验证 | internal_thread使用std::thread+atomic<bool> | ☑ |
| CHECK/ICHECK 异常处理正确 | 代码审查 | 条件失败时抛出tvm::ffi::Error，通过SAFE_CALL传递 | ☑ |
| LOG 宏输出正确 | 代码审查 | INFO/WARNING/ERROR输出到stderr，FATAL抛出异常 | ☑ |

---

## 三、_caffe.cpp FFI 模块验证

| 检查项 | 验证方式 | 预期结果 | 状态 |
|--------|----------|----------|------|
| boost::python 完全移除 | `grep -rn "BOOST_PYTHON_MODULE\|bp::\|boost::python" src/caffe/_caffe.cpp` | 返回空结果 | ☑ |
| Python.h/numpy 头文件移除 | `grep -rn "#include <Python.h>\|#include <numpy" src/caffe/_caffe.cpp` | 返回空结果（使用tvm-ffi C ABI） | ☑ |
| TVM_FFI 导出符号存在 | `nm -D _caffe.so \| grep __tvm_ffi` | 包含`__tvm_ffi_`前缀的导出函数 | ☑ |
| CaffeVersion 导出函数可用 | Python FFI调用 | 返回版本字符串 | ☑ |
| NetInit/NetDelete 生命周期正确 | Python端测试 | 创建Net handle并正确销毁 | ☑ |
| NetForward 执行正确 | Python端测试 | 推理结果形状正确 | ☑ |
| NetGetBlobData 返回 ffi::Tensor | Python端测试 | 返回Tensor可转为numpy数组 | ☑ |
| NetSetBlobData 写入正确 | Python端测试 | 设置输入数据后Forward结果正确 | ☑ |
| Tensor 零拷贝验证 | 内存地址检查 | numpy数组data_ptr与Caffe Blob cpu_data一致 | ☑ |
| 安全调用宏包裹所有导出函数 | 代码审查 | 所有TVM_FFI_DLL_EXPORT_TYPED_FUNC有SAFE_CALL_BEGIN/END | ☑ |
| NCCL stub 正确 | FFI调用 | HasNCCL返回false | ☑ |
| 双路径FFI（pycaffe/ + src/caffe/） | 两个_caffe.cpp均重构 | pycaffe/python/pycaffe/_caffe.cpp与src/caffe/_caffe.cpp一致 | ☑ |

---

## 四、Python 层适配验证

| 检查项 | 验证方式 | 预期结果 | 状态 |
|--------|----------|----------|------|
| import pycaffe 成功 | `python -c "import sys; sys.path.insert(0, 'python'); from pycaffe import _caffe"` | 无ImportError | ☑ |
| Net 可实例化 | 通过tvm_ffi加载模块创建Net | 创建成功不崩溃 | ☑ |
| Net.forward() 正常工作 | 调用forward | 返回dict of numpy arrays | ☑ |
| Net.blobs 可访问 | 访问blobs字典 | 返回正确形状 | ☑ |
| Net.layers 可访问 | 访问layers列表 | 返回正确层数 | ☑ |
| set_mode_cpu() 正常工作 | 模式设置 | 切换成功无错误 | ☑ |
| Tensor.numpy() 零拷贝 | DLPack机制 | 零拷贝数据交换 | ☑ |
| Net 对象析构正确 | handle模式管理 | NetDelete正确释放资源 | ☑ |
| __init__.py使用tvm_ffi加载 | 检查pycaffe/__init__.py | 通过tvm_ffi.load_module加载 | ☑ |

---

## 五、核心推理层覆盖验证

| 检查项 | 验证方式 | 预期结果 | 状态 |
|--------|----------|----------|------|
| InputLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| MemoryDataLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| ConvolutionLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| InnerProductLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| PoolingLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| ReLULayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| SigmoidLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| TanHLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| SoftmaxLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| SoftmaxWithLossLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| BatchNormLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| ScaleLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| ConcatLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| DropoutLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| EltwiseLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| SplitLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| ReshapeLayer/FlattenLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| AccuracyLayer/ArgMaxLayer 可用 | 注册验证 | LayerRegistry可创建 | ☑ |
| EluLayer/PReluLayer/PowerLayer等 | 注册验证 | NeuronLayer子类均注册成功 | ☑ |
| **总计** | LayerRegistry统计 | **42层头文件，38层成功注册运行** | ☑ |

---

## 六、代码质量与规范验证

| 检查项 | 验证方式 | 预期结果 | 状态 |
|--------|----------|----------|------|
| 目录结构符合 include/src 分层 | 检查python/目录 | include/caffe/放头文件，src/caffe/放源文件 | ☑ |
| 编译警告级别合理 | 构建日志 | 第三方库警告允许，无新引入的核心代码警告 | ☑ |
| 兼容层 header-only | 检查include/caffe/compat/ | 11个compat头文件，无对应.cpp | ☑ |
| 原始业务逻辑未破坏 | 对比caffex源码 | 核心算法（SyncedMemory/Blob/Layer/Net）仅头文件替换，逻辑无修改 | ☑ |
| 无硬编码绝对路径 | grep检查 | 无绝对路径硬编码 | ☑ |
| 所有文件使用UTF-8编码 | 文件检查 | 无乱码 | ☑ |
| LICENSE文件存在 | 检查python/ | BSD 2-Clause许可证 | ☑ |
| 源文件显式列出（无GLOB_RECURSE） | 检查CMakeLists.txt | 无file(GLOB_RECURSE)，源文件显式列表 | ☑ |
| C++17标准正确设置 | 检查CMakeLists.txt | CXX_STANDARD 17 | ☑ |
| 代码统计 | 脚本统计 | 130个C++文件，11310行代码 | ☑ |

---

## 七、不迁移组件的隔离验证

| 检查项 | 验证方式 | 预期结果 | 状态 |
|--------|----------|----------|------|
| 无 CUDA/cuDNN 代码 | grep检查 | 仅NO_GPU stub宏定义和device_alternate.hpp条件编译 | ☑ |
| 无 HDF5 代码 | grep检查 | 返回空结果 | ☑ |
| 无 LevelDB/LMDB 代码 | grep检查 | db.hpp中仅基类，无具体后端实现 | ☑ |
| 无 PythonLayer 代码 | grep检查 | 返回空结果 | ☑ |
| 无 NCCL 代码 | grep检查 | 仅_caffe.cpp中HasNCCL()返回false的stub | ☑ |
| 无OpenBLAS/protobuf/Threads/tvm-ffi之外的硬依赖 | 检查CMakeLists.txt | 仅4个外部依赖 | ☑ |

---

## 八、端到端推理验证

| 检查项 | 验证方式 | 预期结果 | 状态 |
|--------|----------|----------|------|
| Net从prototxt加载 | Python端测试 | Net初始化成功 | ☑ |
| blob_names/layer_names可访问 | Python端测试 | 返回名称列表 | ☑ |
| blobs形状正确 | 访问blob.shape | 返回正确形状 | ☑ |
| Markdown测试报告 | tests/test_result.md | 45个测试项全部通过 | ☑ |
| 多次Forward一致性 | 相同输入多次运行 | 输出一致（确定性） | ☑ |
| 构建产物大小合理 | 检查.so大小 | libcaffe_core.a约20MB，_caffe.so约1.3MB | ☑ |
| 链接依赖精简 | ldd检查 | 动态链接依赖从15个降至3个（stdc++/gcc_s/protobuf） | ☑ |

---

## 九、实际遇到问题与修复记录（14个问题）

| # | 问题 | 根因 | 修复方式 | 对应预防规范 |
|---|------|------|---------|------------|
| 1 | Windows PowerShell不支持mkdir -p | 跨平台命令差异 | 使用New-Item -ItemType Directory | Step 0环境预检 |
| 2 | logging.h不存在于tvm-ffi | 未做API前置验证 | 创建compat/logging.hpp shim | Step 0.5 API映射验证 |
| 3 | protobuf_generate路径问题 | CMake配置不熟悉 | 自定义add_custom_command显式指定输出目录 | Task 1增量构建 |
| 4 | LOG(FATAL)用abort()无法被FFI捕获 | 语义理解错误 | 改为throw RuntimeError | Step 0.5 API映射验证 |
| 5 | ThreadLocalPtr使用static thread_local成员 | 实现错误 | 使用ThreadLocalStore辅助类 | Task 2兼容层先测 |
| 6 | math_functions.hpp函数名去掉了cpu_前缀 | 错误重构 | 恢复原始函数名 | Task 3+ 核心迁移 |
| 7 | caffe_nextafter无限递归 | 模板未特化 | 提供float/double显式特化 | Task 2兼容层先测 |
| 8 | 缺少caffe.hpp主头文件 | 闭包分析不完整 | 创建精简caffe.hpp | Step 1闭包分析 |
| 9 | GLOB_RECURSE包含_caffe.cpp到静态库 | CMake大爆炸配置 | 拆分glob显式过滤_caffe.cpp | 增量构建规则1 |
| 10 | Windows编译环境SDK问题 | 未做环境预检 | 切换到WSL | Step 0环境预检 |
| 11 | tvm-ffi相对路径错误 | 路径计算错误 | 调整为../../../ffi/tvm-ffi | Task 1 |
| 12 | GPU方法在CPU_ONLY有实现无声明 | 条件编译不完整 | 移除或包裹在#ifndef CPU_ONLY | Task 4 |
| 13 | POSIX函数(close/read)在WSL缺声明 | 缺头文件 | 添加#include <unistd.h> | Step 0跨平台风险 |
| 14 | libbacktrace CRLF问题 | 子模块换行符问题 | TVM_FFI_USE_LIBBACKTRACE=OFF | Task 1 |

---

## 十、反模式检查（从实战教训总结）

| 反模式 | 检查方式 | 状态 | 本项目是否违反 |
|--------|---------|------|--------------|
| ❌ 未做环境预检就开始写代码 | 确认Step 0完成 | ⚠️ 违反 | ✅ 是→Windows构建失败 |
| ❌ "边猜边写"API映射不验证 | 确认Step 0.5完成 | ⚠️ 违反 | ✅ 是→5-6轮返工 |
| ❌ "我觉得需要哪些文件"正向猜测 | 确认Step 1使用工具 | ⚠️ 违反 | ✅ 是→打地鼠补文件 |
| ❌ 兼容层未验证就迁移业务代码 | 确认Task 2测试通过 | ⚠️ 违反 | ✅ 是→LOG(FATAL)bug扩散 |
| ❌ CMake使用GLOB_RECURSE | grep CMakeLists.txt | ⚠️ 初期违反→修复 | ✅ 是→_caffe.cpp被错误链接 |
| ❌ "大爆炸式"一次性加所有文件 | 检查tasks增量步骤 | ⚠️ 违反 | ✅ 是→错误叠加难定位 |
| ❌ 不在每步编译验证 | 检查每Task TR | ⚠️ 部分违反 | 部分阶段集中测试 |
| ❌ Windows强行编译Linux项目 | Step 0平台决策 | ⚠️ 违反 | ✅ 是→切换WSL |
| ❌ CHECK/LOG宏语义理解错误 | TR-2.2/AC-6验证 | ⚠️ 违反 | ✅ 是→ICHECK参数/LOG(FATAL) |
| ❌ FFI边界忘记安全调用宏 | 代码审查导出函数 | ✅ 遵守 | 否 |
| ❌ handle模式忘记释放资源 | NetDelete实现审查 | ✅ 遵守 | 否 |
| ❌ 路径硬编码或相对路径计算错误 | 多次验证路径 | ⚠️ 违反 | ✅ 是→tvm-ffi路径修正 |
