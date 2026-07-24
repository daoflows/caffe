---
version: "1.0"
---
# PyCaffe dataclasses.py 模块重命名 - Product Requirement Document

## Overview
- **Summary**: 将 `caffe-slim/pycaffe/python/pycaffe/dataclasses.py` 重命名为 `data_types.py`，解决与Python标准库 `dataclasses`（Python 3.7+内置）的命名冲突问题。
- **Purpose**: 模块名 `dataclasses` 与Python标准库同名，可能导致模块导入混淆、命名空间遮蔽风险，降低代码可维护性。重命名为 `data_types.py` 准确反映模块功能（定义数据处理相关的数据类型/配置/统计结构），且不与任何标准库或第三方库冲突。
- **Target Users**: PyCaffe开发者和维护者

## Goals
- 消除 dataclasses.py 与Python标准库 dataclasses 的命名冲突
- 确保新名称准确反映模块功能
- 同步更新所有相关导入语句和引用位置
- 保持功能完全等价（纯重命名，无代码逻辑变更）
- caffex/vendor目录不做任何修改

## Non-Goals (Out of Scope)
- 不修改模块内任何代码逻辑
- 不改变任何类的公开API
- 不修改caffex/目录下的任何文件
- 不重构或优化模块内部实现
- 不处理除dataclasses.py之外的其他命名冲突问题

## Background & Context
- 前次重命名（io.py→transforms.py）已解决一个标准库命名冲突
- dataclasses.py定义了12个数据类：TransformerConfig、DataProcessorConfig、TimingStats、PerImageTiming、BatchTimingStats、ChannelStats、TensorStats、ValueHealthWarning、ImageLoadInfo、BatchInputInfo、TransformInfo等
- 这些类主要被transforms.py导入使用（通过`from .dataclasses import ...`相对导入）
- net_spec.py中使用`from dataclasses import dataclass`是引用标准库，不是引用本地模块
- dataclasses.py内部`import dataclasses`和`from dataclasses import dataclass, field`是引用标准库，绝对导入在正常包使用场景下能找到标准库，但存在潜在遮蔽风险

## Functional Requirements
- **FR-1**: 将dataclasses.py物理重命名为data_types.py
- **FR-2**: 更新transforms.py中的相对导入（from .dataclasses import → from .data_types import）
- **FR-3**: 确保dataclasses.py内部的`import dataclasses`和`from dataclasses import dataclass, field`在重命名后仍正确引用标准库（重命名后自动解决）
- **FR-4**: 确保net_spec.py中的`from dataclasses import dataclass`不受影响（它引用的是标准库，重命名后无影响）

## Non-Functional Requirements
- **NFR-1**: 纯重命名操作，不改变任何代码逻辑和功能行为
- **NFR-2**: 新名称不与Python标准库或常用第三方库冲突
- **NFR-3**: 所有Python文件语法正确，可通过py_compile检查
- **NFR-4**: 模块导入验证通过，所有公开API可访问

## Constraints
- **Technical**: 必须保持向后兼容性（通过transforms.py间接访问的类型不受影响）
- **Dependencies**: 依赖前次io.py→transforms.py重命名已完成
- **Vendor**: caffex/目录为vendor代码，禁止修改

## Assumptions
- data_types.py不与任何已知Python标准库或常用第三方库同名
- 没有外部代码直接import pycaffe.dataclasses（这些类型主要通过transforms内部使用）
- 重命名后dataclasses.py内部的标准库dataclasses引用将自动正确

## Acceptance Criteria

### AC-1: 文件重命名完成
- **Given**: dataclasses.py存在于pycaffe包目录
- **When**: 执行重命名操作
- **Then**: data_types.py存在且内容与原dataclasses.py完全一致，原dataclasses.py不存在
- **Verification**: `programmatic`

### AC-2: 所有导入引用更新
- **Given**: 文件已重命名为data_types.py
- **When**: 搜索所有Python文件中的导入引用
- **Then**: transforms.py中`.dataclasses`相对导入已更新为`.data_types`，无残留的`.dataclasses`或`pycaffe.dataclasses`引用（caffex/除外）
- **Verification**: `programmatic`

### AC-3: 标准库引用不受影响
- **Given**: 文件已重命名
- **When**: 检查dataclasses.py（现data_types.py）内部和net_spec.py中的标准库导入
- **Then**: `import dataclasses`和`from dataclasses import ...`正确引用Python标准库dataclasses模块
- **Verification**: `programmatic`

### AC-4: 功能等价性验证
- **Given**: 所有引用已更新
- **When**: 导入data_types模块并检查所有公开类
- **Then**: 所有12个数据类均可正常访问，与重命名前行为一致
- **Verification**: `programmatic`

### AC-5: Vendor代码隔离
- **Given**: 重命名完成
- **When**: 检查caffex/目录
- **Then**: caffex/目录下所有文件未被修改
- **Verification**: `programmatic`

### AC-6: 语法正确性
- **Given**: 所有修改完成
- **When**: 对所有修改的Python文件执行py_compile
- **Then**: 无语法错误
- **Verification**: `programmatic`

## Open Questions
- 无
