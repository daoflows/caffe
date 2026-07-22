# .agents/ — Caffe 项目 AI 协作规范层

本目录是 Caffe 外部分析项目的 Agent 规范容器，遵循 SpecWeave 工作区发现协议的最小可行子集规范。

## 文件清单

| 文件 | 用途 | 何时读取 |
|------|------|---------|
| `context-routing.md` | 任务类型→源码文件路由映射表 | 每次执行任务前必读 |
| `architecture-map.md` | 8大核心组件的文件定位与架构概览 | 架构分析、源码阅读时 |
| `README.md` | 本文件：.agents/ 目录说明 | 首次进入时 |

## 与父工作区的关系

本 `.agents/` 目录是轻量级路由层，不包含完整的 SpecWeave 规范体系（roles/、skills/、scripts/等）。
完整的规范体系、Skill 工具、复盘模板等位于父工作区：

- **SpecWeave 主入口**：`../../AGENTS.md`（向上3层到 `d:\spaces\SpecWeave\AGENTS.md`）
- **全局核心规则**：`../../.agents/global-core-rules.md`
- **已有学习成果**：`../../.agents/docs/knowledge/learning/caffe-architecture-wiki/README.md`

## 内容敏感度

- Caffe 是 BSD 2-Clause 开源项目，所有源码属于**公开内容（Public）**
- 分析产出物存放于 SpecWeave 主工作区的 `.agents/docs/knowledge/learning/caffe-architecture-wiki/`
- 不在本 `.agents/` 目录下存放分析产出物
