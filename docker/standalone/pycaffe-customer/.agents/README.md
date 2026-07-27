# .agents/ 目录说明

本目录是 PyCaffe Customer 客户分发镜像构建工作区的 AI 智能体规范容器，承载路由规则、构建约束、分发规范等专项规范。

## 文件清单

| 文件 | 职责 |
|------|------|
| [README.md](README.md) | 本文件：.agents/ 目录说明与资产索引 |
| [context-routing.md](context-routing.md) | 任务类型→必读文件映射表（详细版） |
| [build-constraints.md](build-constraints.md) | 构建约束与分发规则（零caffex依赖、构建上下文、客户交付规范、国内镜像支持、导出流程等） |

## 与上层规范的关系

- **本目录规范**：仅覆盖 pycaffe-customer 客户分发镜像构建与交付相关的专项规则
- **父目录规范**：`standalone/.agents/`（路径：`../.agents/`）提供 standalone 目录的通用构建约束
- **caffe 框架规范**：`caffe/.agents/`（路径：`../../.agents/`）提供 Caffe 框架源码分析的架构索引
- **主权区规范**：`SpecWeave/.agents/` 通过逐层回溯提供全局核心规则、角色定义、工作流等
- **嵌套优先原则**：当本目录规范与父目录规范冲突时，以本目录为准（子项目覆盖父级）；未覆盖的场景回退到父级规范

## 规范加载流程

```
收到任务 → 读取 pycaffe-customer/AGENTS.md → 按路由表加载 .agents/ 对应规范 → 执行任务
                ↓ (未覆盖的场景)
         回退 ../.agents/ 规范 (standalone/)
                ↓ (仍未覆盖)
         回退 ../../.agents/ 规范 (caffe/) → 继续逐层回溯到 vendor/ → xuanspace/ → SpecWeave 全局规范
```
