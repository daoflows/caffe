# Caffe Standalone Docker - AI 协作者入口

> **本目录是 Caffe 独立 Docker 镜像构建工作区**：基于 ubuntu:26.04，仅使用 `caffe-slim/` 和 `tvm-ffi/` 从零构建 PyCaffe 推理镜像，零 `caffex/` 依赖。

## 启动协议（所有智能体必须遵循）

收到任务后立即按以下步骤执行，优先级高于任何 Skill 加载：

1. **读取本文件全文** — 本文件是 AI 协作者在本目录下的唯一入口
2. **内容敏感度预检** — 本目录内容为 Docker 构建配置和脚本，属于公开内容（基于开源组件），产出物存放于本目录内
3. **按上下文路由表加载规范** — 根据任务类型加载对应 `.agents/` 下的路由文件
4. **自检** — 确认已理解核心约束：独立构建、零 caffex 依赖、多阶段 Docker 构建、scikit-build-core + CMake + Ninja
5. **开始工作** — 在规范指导下执行任务

## 项目概览

| 属性 | 值 |
|------|-----|
| 项目类型 | Docker 镜像构建工作区（独立 PyCaffe 推理环境） |
| 基础镜像 | ubuntu:26.04 |
| 核心依赖 | caffe-slim (推理-only) + tvm-ffi |
| 构建系统 | Docker 多阶段构建 + scikit-build-core + CMake + Ninja |
| Python 版本 | Ubuntu 26.04 系统 Python 3（numpy >= 2） |
| 关键约束 | 零 `caffex/` 依赖，可独立编译/运行/部署 |
| 父目录 | `docker/` → `caffe/`（向上2层到 caffe/AGENTS.md） |

## 目录结构

```
standalone/                     # 本目录：独立 Docker 镜像构建区
├── AGENTS.md                   # 本文件：AI协作者入口
├── .agents/                    # Agent规范层
│   ├── README.md               # .agents/目录说明
│   ├── context-routing.md      # 任务类型→必读文件映射
│   └── build-constraints.md    # 构建约束与隔离规则
├── README.md                   # 人类开发者入口
├── REGRESSION-TEST.md          # 回归测试流程文档
├── pycaffe/                    # 基础 PyCaffe 推理镜像
│   ├── Dockerfile              # 4阶段多阶段构建文件
│   ├── CMakeLists.txt          # CMake 构建入口
│   ├── README.md               # pycaffe 镜像说明
│   └── scripts/
│       ├── verify-pycaffe.sh   # PyCaffe 导入验证脚本
│       └── verify-parity.sh    # 对标验证占位脚本（独立版本）
└── pycaffe-jupyter-ssh/        # PyCaffe + Jupyter + SSH 镜像
    ├── Dockerfile              # 4阶段多阶段构建文件
    ├── README.md               # jupyter-ssh 镜像说明
    ├── QUICKSTART.md           # 快速开始指南
    ├── build.sh                # 构建辅助脚本
    ├── entrypoint.sh           # 容器启动脚本
    ├── run.sh                  # 运行辅助脚本
    ├── config/                 # 服务配置文件
    │   ├── supervisord.conf
    │   ├── sshd_config
    │   ├── jupyter_notebook_config.py
    │   └── supervisor/conf.d/
    └── scripts/
        └── healthcheck.sh      # 容器健康检查脚本
```

## 上下文路由表

| 任务类型 | 必读入口 |
|---------|---------|
| 构建镜像（pycaffe） | `pycaffe/Dockerfile` + `pycaffe/README.md` + `.agents/build-constraints.md` |
| 构建镜像（jupyter-ssh） | `pycaffe-jupyter-ssh/Dockerfile` + `pycaffe-jupyter-ssh/README.md` |
| 修改验证脚本 | `pycaffe/scripts/verify-pycaffe.sh` + `pycaffe/scripts/verify-parity.sh` |
| 隔离性检查（caffex依赖） | `.agents/build-constraints.md` + `REGRESSION-TEST.md`（T1/T4阶段） |
| 回归测试 | `REGRESSION-TEST.md` + `regression-test.sh`（一键脚本） |
| 运行容器 | `pycaffe-jupyter-ssh/run.sh` + `pycaffe-jupyter-ssh/README.md`（运行章节） |
| Docker 构建上下文 | `.agents/build-constraints.md`（构建上下文必须是 `vendor/` 目录） |
| 向上回溯 caffe 框架 | 读取 `../../AGENTS.md`（caffe/ 入口，caffex/ 源码分析） |
| 向上回溯 vendor | 读取 `../../../AGENTS.md`（vendor/ 区域入口） |
| 向上回溯 SpecWeave | 通过 caffe/AGENTS.md → vendor/AGENTS.md 逐层回溯 |

## 核心约束（铁律）

1. **零 caffex 依赖**：禁止 COPY/ADD/引用 `caffex/` 目录下的任何文件、代码或配置；验证脚本不得硬编码 `caffex/python` 路径
2. **构建上下文固定**：Docker 构建上下文必须是 `vendor/` 目录（父目录的父目录的父目录），以同时访问 `caffe/caffe-slim/` 和 `tvm-ffi/`
3. **基础镜像固定**：使用 `ubuntu:26.04`（非 latest），确保可复现构建
4. **numpy >= 2**：Python 科学计算环境使用 numpy 2.x 系列
5. **多阶段构建**：Dockerfile 必须使用多阶段构建（base-system → base-builder → caffe-builder → runtime）
6. **验证分级**：核心功能（import、version、Net创建、forward）必须 PASS；辅助功能（classifier/detector/Solver）允许 WARN，不得阻断构建
7. **wheel 自包含**：通过 scikit-build-core + CMake + Ninja 编译 wheel，不得依赖预编译二进制
8. **caffe-slim API 差异**：`net.forward()` 返回 None（不返回 dict），不抛异常即为推理成功；输出通过 `net.blobs['prob'].data` 访问

## 镜像清单

| 镜像 | Dockerfile | 包含服务 | 典型用途 |
|------|-----------|---------|---------|
| `caffe-cpu:standalone-pycaffe` | `pycaffe/Dockerfile` | 无（纯推理运行时） | 批量推理、API服务基础镜像 |
| `caffe-cpu:pycaffe-jupyter-ssh` | `pycaffe-jupyter-ssh/Dockerfile` | Jupyter Notebook + SSH | 交互式开发、教学、调试 |

## 构建与验证速查

```bash
# 构建 pycaffe 基础镜像
cd /path/to/vendor
docker build -t caffe-cpu:standalone-pycaffe --target runtime \
  -f caffe/docker/standalone/pycaffe/Dockerfile .

# 构建 jupyter-ssh 镜像
docker build -t caffe-cpu:pycaffe-jupyter-ssh --target runtime \
  -f caffe/docker/standalone/pycaffe-jupyter-ssh/Dockerfile .

# 快速验证
docker run --rm caffe-cpu:standalone-pycaffe \
  python -c "import pycaffe; print(pycaffe.__version__)"

# 完整验证
docker run --rm caffe-cpu:standalone-pycaffe verify-pycaffe.sh

# 一键回归测试
bash caffe/docker/standalone/regression-test.sh
```

## 注意事项

- **caffex/ 是 BVLC 原始 fork**：本目录的 standalone 镜像完全基于 caffe-slim 推理引擎，不使用 caffex 源码
- **.dockerignore 关键配置**：`vendor/.dockerignore` 不得排除 `tvm-ffi/3rdparty/libbacktrace/` 整个目录（仅排除 `.git/`），否则 CMake 构建失败
- **子模块必须初始化**：构建前确保 `caffe/caffe-slim/` 和 `tvm-ffi/` 已通过 `git submodule update --init --recursive` 初始化
- **PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python**：容器内使用 Python 实现的 protobuf，避免 C++ 实现的版本兼容问题
- **ENTRYPOINT 为空**：Dockerfile 不设置 ENTRYPOINT，允许运行时覆盖命令（如 `bash` 进入交互模式）
