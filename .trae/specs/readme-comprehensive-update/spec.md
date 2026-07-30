# Caffe 仓库 README 全面更新 - Product Requirement Document

## Overview
- **Summary**: 对 `vendor/caffe` 仓库根目录 `README.md` 进行全面重构，使其准确反映当前三层模块架构（caffex/caffe-slim/caffe-ffi），提供清晰的模块定位、功能说明、版本信息、安装指南、使用示例和重要变更记录。
- **Purpose**: 现有 README 仅描述 protobuf 最小化库功能，完全缺失三个核心模块的信息，导致新开发者无法理解项目结构和各模块用途。更新后 README 将作为项目唯一入口文档，帮助开发者快速理解项目全貌并选择合适的模块。
- **Target Users**: Caffe 深度学习框架开发者、研究人员、贡献者；需要使用 Caffe 进行推理或基于 TVM FFI 进行扩展的工程师。

## Goals
- 提供项目整体架构概览，清晰展示三层模块关系
- 为每个模块（caffex/caffe-slim/caffe-ffi）提供独立的功能说明章节
- 包含各模块的版本信息、Python 版本要求、依赖说明
- 提供各模块的快速开始/安装指南
- 包含模块对比表格，帮助用户选择合适的模块
- 包含重要变更记录（Changelog）
- 保持文档格式规范、语言清晰易懂（中文）
- 更新 protobuf 代码生成说明，反映当前实际脚本路径
- 保留"添加新算子"指南的链接引用

## Non-Goals (Out of Scope)
- 不修改 caffex/ 内的任何源码文件
- 不修改 caffe-slim/ 或 caffe-ffi/ 内的源码或文档
- 不创建新的子文档（仅更新根 README.md）
- 不翻译为英文（保持中文文档）
- 不添加 CI/CD 状态徽章（项目无公开 CI）
- 不重构 docs/adding-operators.md 等现有子文档

## Background & Context
- 本仓库是 BVLC Caffe 深度学习框架的 fork 与演进版本，已发展为三层架构：
  1. **caffex/**: BVLC Caffe 原始 fork（BSD 2-Clause），版本 1.0.0，完整框架含 CUDA/cuDNN/Matlab/Python 绑定
  2. **caffe-slim/**: CPU-only 精简推理版，版本 1.0.0-slim，C++17，依赖 tvm-ffi header-only，Python 3.10-3.13，scikit-build-core 构建，含 TVM Relax 算子
  3. **caffe-ffi/**: 基于 TVM FFI 原生对象系统的现代绑定，版本 0.1.0（Alpha），要求 Python 3.14+，双类对象模型+零拷贝 DLPack 张量+三层日志+类型化异常，188+ 测试通过
- 现有 README.md 创建于项目早期（仅做 protobuf 库），已严重过时
- 项目使用中文作为主要文档语言

## Functional Requirements
- **FR-1**: README 必须包含项目标题和一句话简介
- **FR-2**: README 必须包含三层架构概览图/表，说明 caffex/caffe-slim/caffe-ffi 的定位关系
- **FR-3**: README 必须为每个模块提供独立章节，包含：功能描述、版本、Python 要求、核心特性、依赖、构建方式
- **FR-4**: README 必须包含模块对比表格（功能覆盖、Python 版本、性能特性、适用场景）
- **FR-5**: README 必须包含环境准备/安装章节（conda 环境配置、依赖安装）
- **FR-6**: README 必须包含快速开始章节，至少覆盖 caffe-ffi 的基本使用示例（创建 Blob、前向传播等）
- **FR-7**: README 必须包含 protobuf 代码生成说明（更新为当前实际路径和方法）
- **FR-8**: README 必须包含重要变更记录（基于 git log 提取关键里程碑）
- **FR-9**: README 必须包含目录结构说明
- **FR-10**: README 必须包含添加新算子指南的链接引用
- **FR-11**: README 必须包含许可证信息
- **FR-12**: README 语言为中文，术语准确，格式使用标准 Markdown

## Non-Functional Requirements
- **NFR-1**: 文档内容必须与实际代码状态一致（版本号、依赖版本、文件路径等必须可验证）
- **NFR-2**: 文档长度适中（300-500 行），信息密度合理，避免冗余
- **NFR-3**: 文档结构清晰，使用正确的 Markdown 标题层级（H1→H2→H3）
- **NFR-4**: 代码示例必须可运行或基于实际 API
- **NFR-5**: 链接引用必须使用相对路径且有效

## Constraints
- **Technical**: 仅修改根目录 README.md 单个文件；Markdown 格式；中文语言
- **Business**: 内容必须准确反映三个模块的当前状态；不得包含虚假或过时信息
- **Dependencies**: 依赖 caffex/caffe-slim/caffe-ffi 目录中已有文件的事实信息

## Assumptions
- 用户有基本的 C++/Python 开发环境（conda、cmake、C++编译器）
- 用户了解深度学习基本概念（Blob/Layer/Net）
- caffe-ffi 是推荐使用的现代模块，caffe-slim 用于兼容旧代码推理，caffex 作为参考源码
- 文档主要面向中文开发者

## Acceptance Criteria

### AC-1: 项目概览准确
- **Given**: README.md 已更新
- **When**: 读者打开 README.md
- **Then**: 第一屏能看到项目名称、一句话简介、三层架构概览
- **Verification**: `human-judgment`
- **Notes**: 概览表需清晰区分三个模块的定位

### AC-2: 三模块功能说明完整
- **Given**: README.md 已更新
- **When**: 读者阅读各模块章节
- **Then**: 每个模块包含功能描述、版本号、Python 要求、核心特性、关键依赖、构建方式
- **Verification**: `programmatic`
- **Notes**: 通过文件内容检查确认所有字段存在

### AC-3: 模块对比表格存在且准确
- **Given**: README.md 已更新
- **When**: 读者查看对比表格
- **Then**: 表格包含至少：模块名称、版本、Python版本、核心特性、适用场景五个维度
- **Verification**: `programmatic`

### AC-4: 安装指南可操作
- **Given**: README.md 已更新
- **When**: 读者按安装指南操作
- **Then**: 环境配置命令（conda create/activate/install）可直接复制执行
- **Verification**: `programmatic`
- **Notes**: 命令格式正确，版本号与 environment.yml/pyproject.toml 一致

### AC-5: 快速开始代码示例有效
- **Given**: README.md 已更新
- **When**: 读者复制快速开始代码
- **Then**: 代码使用 caffe_ffi 的实际 API（Blob、from_numpy、data_tensor 等）
- **Verification**: `programmatic`
- **Notes**: 示例代码中的类名、方法名必须与实际 Python 模块一致

### AC-6: 变更记录基于实际提交历史
- **Given**: README.md 已更新
- **When**: 读者查看变更记录
- **Then**: 关键里程碑与 git log 记录一致（零拷贝优化、TVM FFI集成、C++测试框架等）
- **Verification**: `programmatic`

### AC-7: 目录结构反映实际文件布局
- **Given**: README.md 已更新
- **When**: 读者查看目录结构
- **Then**: 列出的目录和关键文件实际存在
- **Verification**: `programmatic`

### AC-8: 文档格式规范
- **Given**: README.md 已更新
- **When**: 审查文档格式
- **Then**: 使用标准 Markdown，标题层级正确，无语法错误，中文表达清晰
- **Verification**: `human-judgment`

### AC-9: 链接有效性
- **Given**: README.md 已更新
- **When**: 检查所有相对路径链接
- **Then**: 所有相对路径链接指向的文件实际存在（如 docs/adding-operators.md、caffex/LICENSE 等）
- **Verification**: `programmatic`

### AC-10: protobuf 生成说明更新
- **Given**: README.md 已更新
- **When**: 读者查看 protobuf 代码生成章节
- **Then**: 使用 caffe-slim/scripts/gen_proto.py 路径，与当前实际脚本位置一致
- **Verification**: `programmatic`

## Open Questions
- [ ] 是否需要包含 Docker 部署相关说明？（当前 apps/caffe-ffi-jupyter 在主仓库，不在 vendor/caffe 内，建议不在此 README 中包含）
- [ ] caffe-slim 中 pycaffe/patch-20260727-py314 是否需要特别说明？（建议作为 caffe-slim 章节的补充说明）
