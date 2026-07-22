# Tasks

- [x] Task 1: 在 caffe.proto 中添加 NormalizeParameter 定义
  - [x] 1.1 在 PReLUParameter 之后添加 NormalizeParameter 消息（含 across_spatial, scale_filler, channel_shared, eps 字段）
  - [x] 1.2 在 LayerParameter 中添加 `optional NormalizeParameter norm_param = 149;`（按字母序插入到 BatchNormParameter 和 BiasParameter 之间）
  - [x] 1.3 更新 LayerParameter 注释中的 next available ID 为 150

- [x] Task 2: 现代化 _caffe.cpp 代码
  - [x] 2.1 将 `NULL` 替换为 `nullptr`（第35/37/214行共3处）
  - [x] 2.2 为虚函数添加 `override` 关键字（SolverCallback::on_gradients_ready/on_start, NetCallback::run）
  - [x] 2.3 将 `const int NPY_DTYPE` 替换为 `constexpr int NPY_DTYPE`（#define NPY_NO_DEPRECATED_API 保留，它是 Numpy 兼容性宏）
  - [x] 2.4 清理不必要的 `NOLINT` 注释（移除第15行 `// NOLINT`）
  - [x] 2.5 确保所有 `#include` 顺序符合规范（已验证无需调整）

- [x] Task 3: 更新 CMakeLists.txt 编译配置
  - [x] 3.1 在 `set_target_properties` 中添加 `CXX_STANDARD 14` 和 `CXX_STANDARD_REQUIRED ON`
  - [x] 3.2 合并到现有 `set_target_properties` 中，避免重复调用

# Task Dependencies
- Task 2 和 Task 3 可并行执行
- Task 1 不依赖其他任务，可独立执行