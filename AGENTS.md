# Caffe (caffex) - AI协作者入口

> **本目录是 SpecWeave 外部分析对象**：BVLC Caffe 深度学习框架的最小化 protobuf 库包装项目，原始源码位于 `caffex/` 子目录。

## 启动协议（所有智能体必须遵循）

收到任务后立即按以下步骤执行，优先级高于任何 Skill 加载：

1. **读取本文件全文** — 本文件是 AI 协作者在本目录下的唯一入口
2. **按上下文路由表加载规范** — 根据任务类型加载对应 `.agents/` 下的路由文件
3. **内容敏感度预检** — Caffe 是开源项目（BSD 2-Clause License），所有源码属于公开内容，产出物存放于 SpecWeave 主工作区的 `.agents/docs/knowledge/learning/caffe-architecture-wiki/`
4. **自检** — 确认已理解项目结构：外层是 protobuf 最小化包装，真正源码在 `caffex/`
5. **开始工作** — 在规范指导下执行任务

## 项目概览

| 属性 | 值 |
|------|-----|
| 项目类型 | 外部第三方开源框架（分析对象） |
| 原始项目 | BVLC Caffe (Berkeley AI Research) |
| 许可证 | BSD 2-Clause (caffex/LICENSE) |
| 源码根 | `caffex/` |
| 外层构建 | CMake + Conan，最小化 protobuf 库 |
| 父工作区 | SpecWeave（向上递归3层到 `d:\spaces\SpecWeave\`） |

## 目录结构

```
caffe/                          # 本目录：最小化protobuf包装
├── AGENTS.md                   # 本文件：AI协作者入口
├── .agents/                    # Agent规范层（路由+索引）
│   ├── context-routing.md      # 任务类型→源码入口映射
│   ├── architecture-map.md     # 核心架构索引（8大组件文件定位）
│   └── README.md               # .agents/目录说明
├── caffex/                     # BVLC Caffe 原始源码
│   ├── include/caffe/          # C++头文件（核心抽象定义）
│   ├── src/caffe/              # C++实现（含layers/、proto/、CUDA）
│   ├── python/caffe/           # Python绑定（PyCaffe）
│   ├── matlab/+caffe/          # MATLAB绑定
│   ├── tools/                  # 命令行工具
│   ├── examples/               # 示例（MNIST、CIFAR10、ImageNet等）
│   ├── docs/                   # 官方文档与教程
│   └── cmake/                  # CMake构建脚本
├── CMakeLists.txt              # 外层构建配置
├── conanfile.py                # Conan依赖管理
└── README.md                   # 构建说明
```

## 上下文路由表

| 任务类型 | 必读入口 |
|---------|---------|
| 架构总览 | `.agents/architecture-map.md` |
| 核心抽象分析 | `.agents/context-routing.md` → 核心头文件索引 |
| 源码阅读导航 | `.agents/context-routing.md` → 文件路径映射 |
| 构建编译 | `README.md` + `CMakeLists.txt` + `caffex/INSTALL.md` |
| 深度学习概念 | 先读 `.agents/architecture-map.md` 了解 Blob/Layer/Net/Solver 四层抽象 |
| 向上回溯父工作区 | 读取 `../../AGENTS.md`（SpecWeave 主入口） |

## 核心规范入口

| 规范 | 入口 | 说明 |
|------|------|------|
| 上下文路由 | `.agents/context-routing.md` | 任务类型→源码文件映射表 |
| 架构索引 | `.agents/architecture-map.md` | 8大核心组件文件定位与一句话说明 |
| 父工作区规范 | `../../.agents/global-core-rules.md` | SpecWeave全局核心规则（向上3层） |
| 已有学习成果 | `../../.agents/docs/knowledge/learning/caffe-architecture-wiki/README.md` | 七概念方法论完成的架构深度分析 |
| 思维导图 | `../../.agents/docs/knowledge/learning/caffe-architecture-wiki/README.md` | 核心架构Mermaid思维导图 |

## 核心抽象速查（从底向上）

| 抽象层 | 头文件 | 一句话说明 |
|--------|--------|-----------|
| SyncedMemory | `caffex/include/caffe/syncedmem.hpp` | CPU/GPU内存同步，四状态机懒同步 |
| Blob | `caffex/include/caffe/blob.hpp` | 多维张量，data_/diff_对偶存储 |
| Layer | `caffex/include/caffe/layer.hpp` | 计算单元，NVI契约生命周期 |
| Net | `caffex/include/caffe/net.hpp` | DAG计算图，拓扑序执行 |
| Solver | `caffex/include/caffe/solver.hpp` | 优化器，训练循环+参数更新 |
| LayerRegistry | `caffex/include/caffe/layer_factory.hpp` | 自注册工厂，宏驱动开闭原则 |
| Caffe单例 | `caffex/include/caffe/common.hpp` | 全局运行时（模式切换、RNG、CUDA句柄） |
| Proto配置 | `caffex/src/caffe/proto/caffe.proto` | 声明式配置（BlobProto/LayerParameter/NetParameter/SolverParameter） |

## 快速开始

### 一句话引导（已完成深度学习分析时）
> 本项目已通过 SpecWeave 七概念方法论完成架构深度分析，详见核心规范入口中的「已有学习成果」链接。

### 首次阅读源码的引导路径
1. 先读 `.agents/architecture-map.md` 建立全局认知
2. 按核心抽象速查表从底向上阅读：SyncedMemory → Blob → Layer → Net → Solver
3. 对照已有学习成果理解设计模式
4. 阅读具体 Layer 实现（`caffex/src/caffe/layers/`）理解扩展机制

## 注意事项

- **不修改caffex/源码**：caffex/ 是 BVLC 原始 fork，不要直接修改其内容
- **构建使用外层CMake**：本目录的 CMakeLists.txt 是最小化 protobuf 构建，caffex/ 自带完整 CMake
- **CUDA相关代码可选**：`.cu` 文件是 CUDA 实现，无 GPU 环境可只读 `.cpp` 和 `.hpp`
- **Layer数量众多**：caffex/src/caffe/layers/ 下有75+个Layer实现，优先读核心5-10个（conv、pooling、relu、inner_product、softmax、data等）
