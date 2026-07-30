# caffe-ffi 迁移收尾与文档演进 - Product Requirement Document

## Overview
- **Summary**: 完成 caffe-ffi 从 `vendor/caffe/caffe-ffi` 到 `libs/caffe-ffi` 的迁移收尾工作：更新 vendor/caffe/README.md 中所有路径引用，新增四层架构演进历史章节，删除 vendor/caffe/caffe-ffi 残留目录，并原子提交所有变更。
- **Purpose**: caffe-ffi 已从 vendor 内孵化成熟并提升为 `libs/` 下的独立库，但旧目录残留和 README 中过时的路径引用会导致用户混淆、操作失败以及双份代码维护风险。本次收尾确保文档准确反映当前项目结构，消除技术债务。
- **Target Users**: caffe 项目开发者、使用 caffe-ffi 的下游用户、AI 协作者

## Goals
- 更新 vendor/caffe/README.md 中所有指向 `caffe-ffi/` 的路径为正确的新位置 `../../libs/caffe-ffi/`
- 在 README.md 中新增「架构演进历程」章节，清晰描述 caffex → caffe-slim → caffe-ffi(vendor内孵化) → caffe-ffi(libs独立库) 四个阶段的演进周期和过程
- 删除 vendor/caffe/caffe-ffi/ 残留目录（所有有用内容已迁移至 libs/caffe-ffi/）
- 所有变更原子提交，遵循 Conventional Commits 规范
- 确保删除后不破坏任何构建系统、Docker应用或下游引用

## Non-Goals (Out of Scope)
- 不修改 libs/caffe-ffi/ 内的任何源码或文档（独立库维护）
- 不修改 apps/caffe-ffi-jupyter/（已正确引用 libs/caffe-ffi 路径）
- 不修改 libs/caffe-ffi/docs/ 下的历史复盘文档（记录迁移前状态，属于历史档案）
- 不修改已完成的 spec 目录（readme-comprehensive-update 等是历史规划记录）
- 不更新 caffe-slim/ 内的任何代码（caffe-slim 不依赖 caffe-ffi）
- 不进行功能增强或新功能开发

## Background & Context
- caffe-ffi 最初在 vendor/caffe/caffe-ffi/ 内孵化开发，基于 TVM FFI 实现现代 Python 绑定
- 随着成熟度提升（v0.1.0，188+测试用例，Docker环境验证通过），caffe-ffi 被提取为独立库迁移至 `projects/xuanspace/libs/caffe-ffi/`
- 迁移后的 libs/caffe-ffi/ 包含更完整的内容：20+层实现、conda.recipe/、CMakePresets.json、scripts/开发脚本、独立AGENTS.md等
- apps/caffe-ffi-jupyter/ 的 Dockerfile 和 entrypoint 已正确引用 `libs/caffe-ffi` 路径
- caffe-slim/ 目录下无任何文件引用 caffe-ffi/ 目录
- vendor/caffe/caffe-ffi/ 目录仍然存在，内容是迁移前的旧版本（层数较少、缺少conda.recipe等）
- vendor/caffe/README.md 中存在5处过时的 `caffe-ffi/` 路径引用（环境配置、protoc命令、目录结构、参考链接、示例路径）

## Functional Requirements
- **FR-1**: README.md 中所有指向 caffe-ffi 的文件路径引用必须更新为正确的相对路径
  - L141: `caffe-ffi/environment.yml` → `../../libs/caffe-ffi/environment.yml`
  - L147: `cd caffe-ffi` → `cd ../../libs/caffe-ffi`
  - L349: `--python_out=caffe-ffi/python/...` → `--python_out=../../libs/caffe-ffi/python/...`
  - L388-406: 目录结构中 caffe-ffi/ 部分改为说明已迁移，指向 libs/caffe-ffi
  - L452: `caffe-ffi/docs/OPTIMIZATION_REPORT.md` → `../../libs/caffe-ffi/docs/OPTIMIZATION_REPORT.md`
  - L461-466: `caffe-ffi/examples/` → `../../libs/caffe-ffi/examples/`
- **FR-2**: README.md 中三层架构概览表更新，caffe-ffi 行标注「已迁移至 libs/caffe-ffi」
- **FR-3**: README.md 新增「架构演进历程」章节，包含四个阶段的时间线和关键事件
- **FR-4**: 安全删除 vendor/caffe/caffe-ffi/ 目录（使用 git rm 确保版本控制追踪）
- **FR-5**: README.md 目录结构部分反映删除后的真实状态，标注 caffe-ffi 新位置

## Non-Functional Requirements
- **NFR-1**: 文档格式符合项目开发规范（Markdown表格、标题层级、无HTML实体转义、无emoji符号）
- **NFR-2**: 删除操作可回滚（通过git版本控制）
- **NFR-3**: 所有相对路径在删除旧目录后仍然有效（指向 libs/caffe-ffi/）
- **NFR-4**: 原子提交遵循 Conventional Commits 规范，中文描述，单一职责
- **NFR-5**: 删除前确认无构建脚本、CI配置、应用代码引用 vendor/caffe/caffe-ffi/ 路径

## Constraints
- **Technical**: 工作在 vendor/caffe/ 子模块内，需遵循子模块提交规范
- **Business**: 不破坏现有功能，不影响 libs/caffe-ffi 独立库
- **Dependencies**: libs/caffe-ffi/ 必须存在且完整（已确认）

## Assumptions
- libs/caffe-ffi/ 包含了 vendor/caffe/caffe-ffi/ 的所有有用内容（CHANGELOG.md 已确认迁移来源）
- libs/caffe-ffi/docs/ 下历史文档中的相对路径引用是历史档案性质，不需要也不应该修改
- 没有未被发现的脚本或配置引用旧路径（已通过grep扫描确认：仅README.md和旧目录自身文档有引用）
- 用户在 vendor/caffe/ 目录下阅读README，因此到 libs/caffe-ffi/ 的相对路径是 `../../libs/caffe-ffi/`

## Acceptance Criteria

### AC-1: README路径更新完整
- **Given**: vendor/caffe/README.md 当前包含过时的 caffe-ffi/ 路径引用
- **When**: 更新所有路径引用
- **Then**: README.md 中不再有指向已删除目录 vendor/caffe/caffe-ffi/ 的相对路径，所有 caffe-ffi 相关路径指向 ../../libs/caffe-ffi/
- **Verification**: `programmatic`
- **Notes**: 使用 grep 验证无残留 `caffe-ffi/` 开头的相对路径（排除历史文档引用说明）

### AC-2: 架构演进历史章节清晰
- **Given**: README.md 当前缺少演进历史说明
- **When**: 添加「架构演进历程」章节
- **Then**: 章节包含四个阶段（caffex原始fork → caffe-slim精简推理 → caffe-ffi vendor内孵化 → caffe-ffi libs独立库），每个阶段有时间/版本/关键事件/定位说明
- **Verification**: `human-judgment`

### AC-3: 旧目录安全删除
- **Given**: vendor/caffe/caffe-ffi/ 目录存在
- **When**: 执行删除操作
- **Then**: 目录被删除，git 状态显示为删除(D)，libs/caffe-ffi/ 不受影响
- **Verification**: `programmatic`
- **Notes**: 使用 `git rm -r` 而非直接删除文件系统，确保版本控制正确追踪

### AC-4: 删除后无功能破坏
- **Given**: 旧目录已删除
- **When**: 检查所有引用路径
- **Then**: apps/caffe-ffi-jupyter/ Docker构建不受影响，caffe-slim/构建不受影响，README中所有链接路径有效
- **Verification**: `programmatic`

### AC-5: 文档格式规范
- **Given**: README.md 更新完成
- **When**: 按开发规范检查格式
- **Then**: 无HTML实体转义错误（如&gt;=），无Unicode emoji符号，表格语法正确，标题层级合理
- **Verification**: `programmatic` + `human-judgment`

### AC-6: 原子提交规范
- **Given**: 所有变更完成
- **When**: 执行原子提交
- **Then**: 提交信息遵循 Conventional Commits 格式（type(scope): subject），中文描述单一职责，工作区干净无残留
- **Verification**: `programmatic`

## Open Questions
- 无
