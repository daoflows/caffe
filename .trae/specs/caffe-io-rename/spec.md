---
version: "1.0"
---
# PyCaffe io.py 模块重命名 - Product Requirement Document

## Overview
- **Summary**: 将 pycaffe 包中名为 `io.py` 的模块重命名为 `transforms.py`，解决与 Python 标准库 `io` 模块的命名冲突问题，同时更新所有相关的导入语句和引用位置，确保系统功能不受影响。
- **Purpose**: 消除模块命名空间混淆，提升代码可维护性和可读性，避免因同名模块导致的潜在导入错误。
- **Target Users**: PyCaffe 开发者和维护者、使用 PyCaffe 进行深度学习推理的应用开发者。

## Goals
- 将 `caffe-slim/pycaffe/python/pycaffe/io.py` 重命名为 `transforms.py`
- 更新 pycaffe 包内部所有文件的导入语句（`__init__.py`, `pycaffe.py`, `classifier.py`, `detector.py`）
- 更新项目中引用 `pycaffe.io` 的测试脚本和工具脚本
- 确保重命名后所有功能等价，不引入回归问题
- 不修改 caffex/ 目录下的原版 BVLC/Caffe vendor 代码

## Non-Goals (Out of Scope)
- 不修改 caffex/ 目录下的原版 Caffe 代码（保留 vendor 代码原样）
- 不重构 transforms.py（原 io.py）内部实现逻辑
- 不新增或删除任何公开 API（保持 100% 向后兼容，仅模块名变更）
- 不更新 .trae/specs/ 下的历史规格文档（作为历史记录保留）
- 不为旧名称 `io` 提供向后兼容 shim（干净重命名）

## Background & Context
- PyCaffe 是 Caffe 深度学习框架的 Python 接口
- 当前 `io.py` 模块名与 Python 标准库 `io` 模块同名，虽然包内相对导入（`from . import io`）不会直接导致运行时错误，但会产生以下问题：
  1. 在需要同时使用标准库 `io`（如 `io.BytesIO`）和 pycaffe.io 时造成混淆
  2. 模块内部已使用 `skimage.io`，三层 io 概念（标准库/skimage/pycaffe）严重影响可读性
  3. 名称 "io" 过于泛化，不能准确传达模块包含 Transformer、DataProcessor 等高级预处理功能的本质
- 模块核心功能是 Caffe 网络输入数据的变换和预处理管道，"transforms" 更准确地描述了其功能定位
- 该命名与深度学习社区惯例一致（如 PyTorch torchvision.transforms）

## Functional Requirements
- **FR-1**: 将 io.py 文件物理重命名为 transforms.py
- **FR-2**: 更新 `pycaffe/__init__.py` 中的导入语句，将 `from . import io` 和 `from .io import ...` 改为对应 transforms 版本
- **FR-3**: 更新 `pycaffe/pycaffe.py` 中的 `from . import io` 为 `from . import transforms`
- **FR-4**: 更新 `pycaffe/classifier.py` 中的导入及所有 `io.xxx` 引用为 `transforms.xxx`
- **FR-5**: 更新 `pycaffe/detector.py` 中的导入及所有 `io.xxx` 引用为 `transforms.xxx`
- **FR-6**: 更新 `caffe-slim/scripts/test_new_features.sh` 中 `pycaffe.io` 的引用为 `pycaffe.transforms`
- **FR-7**: 更新 `docker/local/conda/runtest.sh` 中 `pycaffe.io` 的引用为 `pycaffe.transforms`
- **FR-8**: 更新 `docker/local/conda/test_new_features.sh` 中 `pycaffe.io` 的引用为 `pycaffe.transforms`
- **FR-9**: 更新 `docker/modules/pycaffe/scripts/verify-parity.sh` 中 `pycaffe.io` 的引用为 `pycaffe.transforms`
- **FR-10**: 模块内对 `skimage.io` 的引用保持不变（这是第三方库，不冲突）

## Non-Functional Requirements
- **NFR-1**: 重命名后所有公开 API（函数、类、常量）保持完全一致，仅模块路径变更
- **NFR-2**: 所有现有的功能测试应继续通过，无回归
- **NFR-3**: 不引入任何新的依赖或第三方库
- **NFR-4**: 代码风格保持与现有代码库一致
- **NFR-5**: 修改应原子化，每个文件的变更是独立可验证的

## Constraints
- **Technical**: Python 3.x；不得改变任何函数签名、类接口或行为逻辑
- **Business**: 必须保持与现有 PyCaffe API 的向后兼容性（除模块名变更外）
- **Dependencies**: NumPy, skimage, OpenCV (可选), protobuf；caffex/ 目录为 vendor 代码不得修改

## Assumptions
- 没有外部代码直接依赖 `pycaffe.io` 模块路径（如有则需要用户自行更新，但项目内脚本必须全部更新）
- transforms.py 模块内不需要导入标准库 `io` 模块（当前代码确实没有导入）
- 模块名 `transforms` 不会与 pycaffe 包内任何现有模块冲突（已确认没有同名文件）
- `transforms` 不与任何已安装的顶级 Python 包冲突（HuggingFace `transformers` 是复数顶级包，与 `pycaffe.transforms` 命名空间隔离）

## Acceptance Criteria

### AC-1: 文件重命名完成
- **Given**: io.py 文件存在于 pycaffe 包目录
- **When**: 执行重命名操作
- **Then**: io.py 不再存在，transforms.py 存在且内容与原 io.py 完全一致（仅文件名变更）
- **Verification**: `programmatic`
- **Notes**: 使用 git mv 或等效操作保留文件历史

### AC-2: pycaffe 包内部导入全部更新
- **Given**: 四个核心文件引用了 .io 模块
- **When**: 更新导入语句
- **Then**: __init__.py, pycaffe.py, classifier.py, detector.py 中不再有对 `.io` 的引用，全部改为 `.transforms`
- **Verification**: `programmatic`（grep 验证无残留）

### AC-3: 脚本文件引用全部更新
- **Given**: 4 个 shell 脚本引用了 pycaffe.io
- **When**: 更新脚本中的 Python 代码
- **Then**: 所有 shell 脚本中不再有 `pycaffe.io`，全部改为 `pycaffe.transforms`
- **Verification**: `programmatic`（grep 验证无残留）

### AC-4: 功能等价性验证
- **Given**: 模块已重命名且导入已更新
- **When**: 运行 PyCaffe 基本功能测试
- **Then**: 可以成功 `import pycaffe.transforms`，可以访问 Transformer, DataProcessor, load_image, resize_image, oversample, blobproto_to_array 等所有公开 API
- **Verification**: `programmatic`（Python 导入测试）

### AC-5: caffex/ 目录未被修改
- **Given**: caffex/ 是 vendor 代码
- **When**: 重命名操作完成
- **Then**: caffex/ 目录下的所有文件保持原样，无任何修改
- **Verification**: `programmatic`（git status 验证）

### AC-6: 无标准库 io 模块的冲突风险
- **Given**: 模块已重命名为 transforms
- **When**: 用户同时使用 `import io`（标准库）和 `from pycaffe import transforms`
- **Then**: 两者命名空间完全隔离，无任何混淆或覆盖
- **Verification**: `human-judgment`（代码审查确认）

## Open Questions
- [ ] 是否需要为 `pycaffe.io` 提供弃用警告的向后兼容 shim？（当前方案：不提供，干净重命名）
