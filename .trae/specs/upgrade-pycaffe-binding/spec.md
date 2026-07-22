# PyCaffe 绑定全面升级 Spec

## Why
caffex 的 `caffe.proto` 缺少 `NormalizeParameter` 定义（外层 `protos/caffe.proto` 已包含），且 `_caffe.cpp` 使用较旧的 Boost.Python 编码模式，`CMakeLists.txt` 未显式设置 C++ 标准。需同步升级此三文件以保持项目一致性。

## What Changes
- 在 `caffex/src/caffe/proto/caffe.proto` 中新增 `NormalizeParameter` 消息定义，并在 `LayerParameter` 中添加 `norm_param = 149` 字段
- 现代化 `caffex/python/caffe/_caffe.cpp`：使用 `nullptr` 替代 `NULL`、`override` 关键字、`constexpr` 等 C++14/17 特性
- 更新 `caffex/python/CMakeLists.txt` 编译配置，显式设置 C++14 标准，增强兼容性

## Impact
- Affected specs: 无（新增规格）
- Affected code:
  - `caffex/src/caffe/proto/caffe.proto` — 协议定义
  - `caffex/python/caffe/_caffe.cpp` — Boost.Python 绑定
  - `caffex/python/CMakeLists.txt` — 编译配置

## ADDED Requirements

### Requirement: NormalizeParameter Proto 定义
系统 SHALL 在 `caffe.proto` 中定义 `NormalizeParameter` 消息，包含 `across_spatial`、`scale_filler`、`channel_shared`、`eps` 字段，并在 `LayerParameter` 中添加 `norm_param = 149` 字段。

#### Scenario: NormalizeParameter 序列化/反序列化
- **WHEN** 创建 NormalizeParameter 并设置所有字段
- **THEN** 序列化后反序列化，字段值保持一致

#### Scenario: LayerParameter 包含 norm_param
- **WHEN** 设置 LayerParameter.type = "Normalize" 并配置 norm_param
- **THEN** HasField("norm_param") 返回 True

### Requirement: _caffe.cpp 代码现代化
系统 SHALL 将 `_caffe.cpp` 中的 C++ 代码升级到 C++14 标准，包括：
- `NULL` 替换为 `nullptr`
- 虚函数添加 `override` 关键字
- 使用 `constexpr` 替代 `#define` 常量
- 移除不必要的 `NOLINT` 注释

#### Scenario: 现代化后编译通过
- **WHEN** 使用 C++14 标准编译 _caffe.cpp
- **THEN** 编译无错误无警告

### Requirement: CMakeLists.txt 编译标准升级
系统 SHALL 在 `caffex/python/CMakeLists.txt` 中显式设置 `CMAKE_CXX_STANDARD 14` 和 `CMAKE_CXX_STANDARD_REQUIRED ON`，确保 pycaffe 目标使用 C++14 标准编译。

#### Scenario: C++14 标准编译
- **WHEN** 配置 CMake 构建
- **THEN** pycaffe 目标使用 C++14 标准编译

## MODIFIED Requirements
无

## REMOVED Requirements
无