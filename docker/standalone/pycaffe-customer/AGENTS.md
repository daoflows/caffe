# PyCaffe Customer 分发镜像 - AI 协作者入口

> **本目录是 Caffe 客户分发镜像构建工作区**：基于 ubuntu:26.04，面向最终客户交付的生产级 PyCaffe 推理镜像，包含 Jupyter Notebook + SSH 服务、自验证脚本、ResNet-50 演示，并支持导出为 tar 分发包。

## 启动协议（所有智能体必须遵循）

收到任务后立即按以下步骤执行，优先级高于任何 Skill 加载：

1. **读取本文件全文** — 本文件是 AI 协作者在本目录下的唯一入口
2. **内容敏感度预检** — 本目录内容为 Docker 构建配置和客户分发脚本，属于公开内容（基于开源组件），产出物存放于本目录内
3. **按上下文路由表加载规范** — 根据任务类型加载对应 `.agents/` 下的路由文件
4. **自检** — 确认已理解核心约束：客户交付导向、多阶段构建、内置验证、支持国内镜像、导出分发流程
5. **开始工作** — 在规范指导下执行任务

## 项目概览

| 属性 | 值 |
|------|-----|
| 项目类型 | Docker 客户分发镜像构建工作区（生产级 PyCaffe 推理环境） |
| 基础镜像 | ubuntu:26.04 |
| 核心依赖 | caffe-slim (推理-only) + tvm-ffi |
| 包含服务 | Jupyter Notebook (8888) + SSH (22) + supervisord 进程管理 |
| 内置验证 | `caffe-verify` 自验证脚本（7项检查） |
| 内置演示 | ResNet-50 分类模型 + infer.py 推理脚本 |
| 构建系统 | Docker 多阶段构建 + scikit-build-core + CMake + Ninja |
| Python 版本 | Ubuntu 26.04 系统 Python 3（numpy >= 2） |
| 关键特性 | 非 root 用户、gosu 权限降级、SSH 加固、tini init、国内镜像支持、一键导出 |
| 父目录 | `standalone/` → `docker/` → `caffe/`（向上3层到 caffe/AGENTS.md） |

## 目录结构

```
pycaffe-customer/               # 本目录：客户分发镜像构建区
├── AGENTS.md                   # 本文件：AI协作者入口
├── .agents/                    # Agent规范层
│   ├── README.md               # .agents/目录说明
│   ├── context-routing.md      # 任务类型→必读文件映射
│   └── build-constraints.md    # 构建约束与分发规则
├── README.md                   # 中文用户指南（面向最终客户）
├── Dockerfile                  # 4阶段多阶段构建文件
├── Dockerfile.dockerignore     # Docker 构建上下文忽略规则
├── build.sh                    # 构建辅助脚本（支持 --china 国内镜像）
├── export.sh                   # 导出分发脚本（tar + sha256 校验）
├── entrypoint.sh               # 容器启动脚本（6步流程）
├── config/                     # 服务配置文件
│   ├── supervisord.conf        # supervisord 主配置
│   ├── sshd_config             # SSH 服务加固配置
│   ├── jupyter_notebook_config.py  # Jupyter 配置
│   └── supervisor/conf.d/      # 服务进程配置
│       ├── jupyter.conf        # Jupyter 进程配置
│       └── sshd.conf           # SSH 进程配置
└── scripts/                    # 容器内脚本
    ├── caffe-verify            # 自验证脚本（7项检查）
    └── healthcheck.sh          # 容器健康检查脚本
```

## 上下文路由表

| 任务类型 | 必读入口 |
|---------|---------|
| 构建客户镜像 | `Dockerfile` + `build.sh` + `.agents/build-constraints.md` |
| 使用国内镜像构建 | `build.sh --china` + `Dockerfile`（APT/PyPI 镜像源配置） |
| 修改启动流程 | `entrypoint.sh` + `config/supervisord.conf` |
| 修改服务配置 | `config/sshd_config` + `config/jupyter_notebook_config.py` + `config/supervisor/conf.d/` |
| 修改验证脚本 | `scripts/caffe-verify`（7项PASS检查） |
| 修改健康检查 | `scripts/healthcheck.sh`（SSH + Jupyter 双端口检测） |
| 导出分发包 | `export.sh`（tar + sha256 校验和生成） |
| 客户使用文档 | `README.md`（中文用户指南） |
| Docker 构建上下文 | `.agents/build-constraints.md`（构建上下文必须是 `vendor/` 目录） |
| 向上回溯 standalone | 读取 `../AGENTS.md`（standalone/ 入口） |
| 向上回溯 caffe 框架 | 读取 `../../AGENTS.md`（caffe/ 入口，caffex/ 源码分析） |
| 向上回溯 vendor | 读取 `../../../AGENTS.md`（vendor/ 区域入口） |
| 向上回溯 SpecWeave | 通过 caffe/AGENTS.md → vendor/AGENTS.md → xuanspace/AGENTS.md 逐层回溯 |

## 核心约束（铁律）

1. **客户交付导向**：镜像开箱即用，默认配置即可运行，生产环境必须提示修改默认凭据
2. **零 caffex 依赖**：禁止 COPY/ADD/引用 `caffex/` 目录下的任何文件、代码或配置
3. **构建上下文固定**：Docker 构建上下文必须是 `vendor/` 目录（父目录的父目录的父目录），以同时访问 `caffe/caffe-slim/` 和 `tvm-ffi/`
4. **基础镜像固定**：使用 `ubuntu:26.04`（非 latest），配置时区 Asia/Shanghai
5. **numpy >= 2**：Python 科学计算环境使用 numpy 2.x 系列
6. **多阶段构建**：Dockerfile 必须使用4阶段构建（base-system → base-builder → caffe-builder → customer-runtime）
7. **无构建工具**：最终阶段 customer-runtime 不包含 gcc/cmake/ninja/git/make 等构建工具
8. **非 root 运行**：容器默认以 `builder`（UID 1000）身份运行，使用 gosu 进行权限降级
9. **SSH 安全加固**：禁用 root 登录，仅允许非 root 用户密码认证，每次启动重新生成主机密钥
10. **验证分级**：caffe-verify 7项检查必须全部 PASS（pycaffe导入、版本、Net类、LeNet推理、Jupyter、SSH、ResNet50）
11. **国内镜像支持**：build.sh 必须支持 `--china` 参数，配置 APT 北外源和 PyPI 清华源
12. **可导出分发**：export.sh 必须生成 tar 包和 sha256 校验和，支持自定义版本标签和输出目录
13. **wheel 自包含**：通过 scikit-build-core + CMake + Ninja 编译 wheel，不得依赖预编译二进制
14. **caffe-slim API 差异**：`net.forward()` 返回 None（不返回 dict），不抛异常即为推理成功；输出通过 `net.blobs['prob'].data` 访问
15. **ENTRYPOINT 为空**：Dockerfile 不设置 ENTRYPOINT，允许运行时覆盖命令（如 `bash` 进入交互模式）

## 镜像清单

| 镜像标签 | Dockerfile | 包含服务 | 典型用途 |
|---------|-----------|---------|---------|
| `caffe-cpu:customer` | `Dockerfile` | Jupyter Notebook + SSH + ResNet-50 演示 | 客户交付、生产部署、交互式推理 |

## 构建与验证速查

```bash
# 构建客户镜像（标准模式）
cd /path/to/vendor
docker build -t caffe-cpu:customer --target customer-runtime \
  -f caffe/docker/standalone/pycaffe-customer/Dockerfile .

# 使用国内镜像构建（中国大陆用户）
cd caffe/docker/standalone/pycaffe-customer
./build.sh --china

# 快速验证（运行自验证脚本）
docker run --rm caffe-cpu:customer caffe-verify

# 导出分发包
./export.sh -z -t v1.0.0 -o ./dist/ --version 1.0.0

# 运行容器（基础模式）
docker run -d -p 8888:8888 -p 2222:22 --name caffe caffe-cpu:customer

# 运行容器（自定义凭据 + 挂载工作目录）
docker run -d \
  -p 8888:8888 -p 2222:22 \
  -e USER_PASSWORD=your_secure_password \
  -e JUPYTER_TOKEN=your_secure_token \
  -v /your/local/workspace:/workspace/user-data \
  --name caffe \
  caffe-cpu:customer
```

## 注意事项

- **caffex/ 是 BVLC 原始 fork**：本镜像完全基于 caffe-slim 推理引擎，不使用 caffex 源码
- **默认凭据必须修改**：README.md 中明确提示生产环境必须修改默认 SSH 密码和 Jupyter Token
- **ResNet-50 示例内置**：镜像内 `/opt/caffe-examples/` 包含 ResNet-50 模型和 infer.py 推理脚本
- **用户工作目录**：`/workspace/user-data/` 是推荐的用户数据挂载点，`/workspace/examples/` 是示例目录符号链接
- **构建元数据**：容器内 `/etc/caffe-customer-release` 记录版本、构建日期、组件信息
- **PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python**：容器内使用 Python 实现的 protobuf，避免 C++ 实现的版本兼容问题
- **时区配置**：容器内默认时区为 UTC，可通过 `-e TZ=Asia/Shanghai` 运行时覆盖或在构建时配置
- **子模块必须初始化**：构建前确保 `caffe/caffe-slim/` 和 `tvm-ffi/` 已通过 `git submodule update --init --recursive` 初始化
- **export.sh 输出**：导出脚本生成 `<name>-<version>-<date>.tar`（或 `.tar.gz`）和对应的 `.sha256` 校验文件
