# .agents/ 目录说明

本目录是 Caffe Standalone Docker 构建工作区的 AI 智能体规范容器，承载路由规则、构建约束等专项规范。

## 文件清单

| 文件 | 职责 |
|------|------|
| [README.md](README.md) | 本文件：.agents/ 目录说明与资产索引 |
| [context-routing.md](context-routing.md) | 任务类型→必读文件映射表（详细版） |
| [build-constraints.md](build-constraints.md) | 构建约束与隔离规则（零caffex依赖、构建上下文、镜像规范等） |

## 与上层规范的关系

- **本目录规范**：仅覆盖 standalone Docker 构建相关的专项规则
- **父目录规范**：`caffe/.agents/`（路径：`../../.agents/`）提供 Caffe 框架源码分析的架构索引
- **主权区规范**：`SpecWeave/.agents/` 通过逐层回溯提供全局核心规则、角色定义、工作流等
- **嵌套优先原则**：当本目录规范与父目录规范冲突时，以本目录为准（子项目覆盖父级）；未覆盖的场景回退到父级规范

## 规范加载流程

```
收到任务 → 读取 standalone/AGENTS.md → 按路由表加载 .agents/ 对应规范 → 执行任务
                ↓ (未覆盖的场景)
         回退 ../../AGENTS.md (caffe/) → ../../.agents/ 规范
                ↓ (仍未覆盖)
         回退 ../../../AGENTS.md (vendor/) → 继续逐层回溯到 SpecWeave 全局规范
```
