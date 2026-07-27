# .agents/ 目录说明

本目录是 Caffe Origin Docker 构建工作区的 AI 智能体规范容器，承载路由规则、构建约束、分发规则等专项规范。

## 文件清单

| 文件 | 职责 |
|------|------|
| [README.md](README.md) | 本文件：.agents/ 目录说明与资产索引 |
| [context-routing.md](context-routing.md) | 任务类型→必读文件映射表（详细版） |
| [build-constraints.md](build-constraints.md) | 构建约束与分发规则（版本锁定、Dockerfile规范、自包含分发、两套脚本区分） |

## 与上层规范的关系

- **本目录规范**：仅覆盖 origin Docker 构建与分发相关的专项规则
- **父目录规范**：`caffe/.agents/`（路径：`../../.agents/`）提供 Caffe 框架源码分析的架构索引
- **主权区规范**：`SpecWeave/.agents/` 通过逐层回溯提供全局核心规则、角色定义、工作流等
- **嵌套优先原则**：当本目录规范与父目录规范冲突时，以本目录为准（子项目覆盖父级）；未覆盖的场景回退到父级规范

## 规范加载流程

```
收到任务 → 读取 origin/AGENTS.md → 按路由表加载 .agents/ 对应规范 → 执行任务
                ↓ (未覆盖的场景)
         回退 ../../AGENTS.md (caffe/) → ../../.agents/ 规范
                ↓ (仍未覆盖)
         回退 ../../../AGENTS.md (vendor/) → 继续逐层回溯到 SpecWeave 全局规范
```

## 与 docker/standalone/ 的区别

| 维度 | docker/origin/（本目录） | docker/standalone/ |
|------|------------------------|-------------------|
| 基础镜像 | ubuntu:22.04 | ubuntu:26.04 |
| Python | 3.10（系统Python） | 3（ubuntu:26.04系统Python） |
| Caffe源码 | caffex/（BVLC原始fork，Make构建） | caffe-slim/（推理-only，CMake+scikit-build-core） |
| numpy | 1.x（<2.0） | >= 2 |
| protobuf | 固定 3.20.3 | Python实现（兼容） |
| 构建系统 | Make + Docker多阶段 | CMake + Ninja + scikit-build-core |
| 目标 | 贴近Caffe原始构建方式，基线环境 | 独立推理镜像，零caffex依赖 |
| 分发 | 支持（export.sh/load-and-verify.sh） | 支持（regression-test.sh） |
