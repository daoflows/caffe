# Caffe Origin Docker - AI 协作者入口

> **本目录是 BVLC Caffe 原始构建方式的 Docker 镜像工作区**：基于 Ubuntu 22.04 + Python 3.10，直接使用 `caffex/` 源码通过 Make 编译，贴近 Caffe 原生构建方式，提供可独立分发的自包含运行时镜像。

## 启动协议（所有智能体必须遵循）

收到任务后立即按以下步骤执行，优先级高于任何 Skill 加载：

1. **读取本文件全文** — 本文件是 AI 协作者在本目录下的唯一入口
2. **内容敏感度预检** — 本目录内容为 Docker 构建配置和脚本，基于开源组件（BVLC Caffe BSD 许可），属于公开内容，产出物存放于本目录内
3. **按上下文路由表加载规范** — 根据任务类型加载对应 `.agents/` 下的路由文件
4. **自检** — 确认已理解核心约束：caffex Make构建、protobuf 3.x锁定、numpy<2、双镜像（runtime/jupyter）、自包含分发
5. **开始工作** — 在规范指导下执行任务

## 项目概览

| 属性 | 值 |
|------|-----|
| 项目类型 | Docker 镜像构建工作区（BVLC Caffe 原始构建方式，可独立分发） |
| 基础镜像 | ubuntu:22.04（固定版本，非 latest） |
| Python 版本 | Python 3.10（Ubuntu 22.04 系统 Python） |
| 核心依赖 | caffex/（BVLC原始源码，Make构建系统） |
| numpy 版本 | `>=1.21,<2.0`（numpy 1.x 系列，Caffe 原始代码不兼容 numpy 2.x） |
| protobuf 版本 | `==3.20.3`（固定版本，protobuf 4.x 不兼容 Caffe） |
| 构建系统 | Docker 多阶段构建 + Make（caffex/Makefile） |
| 构建上下文 | `caffe/` 目录（SCRIPT_DIR/../..，相对于本目录向上两层） |
| 关键特性 | 自包含可分发、不挂载宿主机目录、内置健康检查、一键导出/加载 |
| 父目录 | `docker/` → `caffe/`（向上2层到 caffe/AGENTS.md） |

## 目录结构

```
origin/                         # 本目录：原始构建方式 Docker 镜像区
├── AGENTS.md                   # 本文件：AI协作者入口
├── .agents/                    # Agent规范层
│   ├── README.md               # .agents/目录说明
│   ├── context-routing.md      # 任务类型→必读文件映射
│   └── build-constraints.md    # 构建约束与分发规则
├── Dockerfile                  # 基础运行时镜像（4阶段：base-system→base-builder→builder→runtime）
├── Dockerfile.jupyter-ssh      # Jupyter+SSH镜像（4阶段：base-system→base-builder→builder→runtime-jupyter）
├── build.sh                    # 构建脚本（支持 --jupyter/--all/--no-cache 等参数）
├── run-standalone.sh           # 独立运行脚本（分发用，不挂载宿主机目录）
├── export.sh                   # 镜像导出脚本（生成 dist/*.tar，支持gzip压缩和SHA256）
├── load-and-verify.sh          # 镜像加载与验证脚本（自动检测dist/、运行verify-caffe.sh）
├── run.sh                      # 开发用运行脚本（挂载宿主机目录，仅供本地开发）
├── run-jupyter.sh              # 开发用Jupyter管理脚本（start/stop/status/logs）
├── entrypoint-jupyter.sh       # Jupyter容器入口脚本（密码/Token/SSH/Jupyter初始化）
├── USER_GUIDE.md               # 面向非开发者的中文用户指南
├── README.md                   # 人类开发者入口（含构建/运行/FAQ完整文档）
├── BUILD_REPORT.md             # 历史构建验证报告
├── TASK_SUMMARY.md             # 任务摘要文档
├── config/                     # 服务配置文件（仅jupyter镜像使用）
│   ├── profile.d/
│   │   └── caffe.sh            # 环境变量配置（登录shell自动加载）
│   ├── supervisor/
│   │   └── conf.d/
│   │       ├── jupyter.conf    # Jupyter supervisord 配置
│   │       └── sshd.conf       # SSH supervisord 配置
│   ├── jupyter_notebook_config.py  # Jupyter Notebook基础配置
│   ├── sshd_config             # SSH守护进程配置
│   └── supervisord.conf        # Supervisord主配置
├── scripts/                    # 容器内辅助脚本（被COPY到/usr/local/bin/）
│   ├── generate-makefile-config.sh  # 自动生成Makefile.config
│   ├── verify-caffe.sh         # Caffe安装验证脚本（12项检查，带颜色输出和退出码）
│   ├── healthcheck-caffe.sh    # Runtime镜像健康检查（Python/caffe导入验证）
│   └── healthcheck-jupyter.sh  # Jupyter镜像健康检查（SSH+Jupyter端口检测）
└── dist/                       # 镜像导出目录（.gitkeep跟踪，tar文件gitignore排除）
    └── .gitkeep
```

## 上下文路由表

| 任务类型 | 必读入口 |
|---------|---------|
| 构建镜像（runtime） | `build.sh` + `Dockerfile` + `.agents/build-constraints.md` |
| 构建镜像（jupyter） | `build.sh --jupyter` + `Dockerfile.jupyter-ssh` + `.agents/build-constraints.md` |
| 构建两个镜像 | `build.sh --all` |
| 修改验证脚本 | `scripts/verify-caffe.sh` + `.agents/build-constraints.md`（验证分级规则） |
| 修改健康检查 | `scripts/healthcheck-caffe.sh` 或 `scripts/healthcheck-jupyter.sh` |
| 修改运行脚本 | `run-standalone.sh`（分发用）/ `run.sh`（开发用，挂载宿主机） |
| 镜像导出与分发 | `export.sh` + `USER_GUIDE.md` + `.agents/build-constraints.md`（分发规则） |
| 镜像加载验证 | `load-and-verify.sh` |
| Jupyter配置/入口 | `config/` 目录 + `entrypoint-jupyter.sh` |
| Dockerfile修改 | 对应Dockerfile + `.agents/build-constraints.md`（核心约束） |
| 文档更新 | `README.md`（开发者文档）/ `USER_GUIDE.md`（非开发者指南） |
| 两套脚本区别 | `.agents/build-constraints.md`（开发模式vs分发模式） |
| 向上回溯 caffe 框架 | 读取 `../../AGENTS.md`（caffe/ 入口，caffex/ 源码分析） |
| 向上回溯 vendor | 读取 `../../../AGENTS.md`（vendor/ 区域入口） |
| 向上回溯 SpecWeave | 通过 caffe/AGENTS.md → vendor/AGENTS.md 逐层回溯 |

## 镜像清单

| 镜像标签 | Dockerfile | 目标阶段 | 包含服务 | 典型用途 |
|---------|-----------|---------|---------|---------|
| `caffe-cpu:origin-runtime` | `Dockerfile` | runtime | 无（纯命令行运行时） | 批处理、脚本执行、CI、API服务基础 |
| `caffe-cpu:origin-jupyter` | `Dockerfile.jupyter-ssh` | runtime-jupyter | Jupyter Notebook/Lab + SSH + supervisord | 交互式开发、教学演示、远程访问 |

## 核心约束（铁律）

1. **protobuf 固定 3.20.3**：严禁升级到 protobuf 4.x，Caffe 的 Python 绑定不兼容
2. **numpy < 2.0**：使用 `numpy>=1.21,<2.0`，Caffe 原始代码使用 numpy 1.x API
3. **基础镜像固定 ubuntu:22.04**：禁止使用 ubuntu:latest 或其他版本
4. **构建上下文固定**：Docker 构建上下文必须是 `caffe/` 目录（SCRIPT_DIR/../..），COPY 源路径相对于 caffe/ 根目录
5. **多阶段构建**：必须使用 4 阶段结构（base-system → base-builder → builder → runtime/runtime-jupyter）
6. **自包含分发**：`run-standalone.sh` 绝不使用 `-v` 挂载宿主机目录；`export.sh` 导出的镜像可在任何 Docker 20.10+ 环境加载运行
7. **两套运行脚本明确区分**：
   - `run.sh`/`run-jupyter.sh`：本地开发用，挂载宿主机目录（覆盖镜像内产物）
   - `run-standalone.sh`：分发用，不挂载，镜像完全自包含
8. **验证脚本分级**：verify-caffe.sh 使用 PASS/FAIL 分级，核心功能失败返回非零退出码
9. **HEALTHCHECK 必须**：两个镜像均内置 HEALTHCHECK，runtime 验证 caffe 导入，jupyter 验证 SSH+Jupyter 端口
10. **脚本 LF 行尾**：所有 .sh 文件必须使用 LF 换行符（.gitattributes 已配置 `*.sh text eol=lf`）

## 构建与验证速查

```bash
# 进入本目录
cd docker/origin

# 构建 runtime 镜像（默认）
./build.sh

# 构建 jupyter 镜像
./build.sh --jupyter

# 一键构建两个镜像
./build.sh --all

# 快速验证（不挂载宿主机）
docker run --rm caffe-cpu:origin-runtime verify-caffe.sh

# 独立运行（分发模式）
./run-standalone.sh runtime                    # 交互式bash
./run-standalone.sh runtime -- python3 -c "import caffe; print(caffe.__version__)"
./run-standalone.sh jupyter                    # 启动Jupyter+SSH

# 导出镜像到 dist/ 目录（用于分发）
./export.sh                    # 导出 .tar
./export.sh --compress         # 导出 .tar.gz

# 用户加载并验证（分发到用户机器后）
./load-and-verify.sh           # 自动检测dist/下最新镜像
```

## 注意事项

- **caffex/ 是 BVLC 原始 fork**：本目录镜像直接编译 caffex/ 源码，不使用 caffe-slim/ 推理引擎
- **开发脚本 vs 分发脚本**：`run.sh` 和 `run-jupyter.sh` 挂载宿主机目录用于本地开发，会覆盖镜像内编译产物；`run-standalone.sh` 不挂载，用于分发给最终用户
- **Dockerfile 路径相对性**：Dockerfile 中 `COPY docker/origin/scripts/xxx` 路径是相对于构建上下文（caffe/ 根目录），不是相对于 Dockerfile 所在目录
- **Makefile.config 自动生成**：`scripts/generate-makefile-config.sh` 在 builder 阶段自动检测系统路径生成 Makefile.config，无需手动配置
- **.dockerignore 已配置**：`caffex/build/`、`caffex/distribute/`、`dist/`、`*.tar` 等已排除，不进入构建上下文
- **Python 科学计算包**：runtime 镜像预装 numpy/scipy/matplotlib/scikit-image/h5py/pandas/pyyaml/pillow/six/Cython/protobuf/python-dateutil/python-gflags 等
- **Jupyter 镜像时区/语言**：Jupyter 镜像使用 Asia/Shanghai 时区和 zh_CN.UTF-8 语言，runtime 镜像使用 UTC/C.UTF-8
