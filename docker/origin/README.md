# Caffe Origin CPU Docker 镜像

本目录提供 BVLC Caffe 的 CPU-only Docker 镜像构建方案，基于 Ubuntu 22.04 + Python 3.10 + Make 构建系统。提供两种镜像变体：

1. **基础运行时镜像**（`Dockerfile`）：用于构建 `caffex/python` 原始模块，贴近 Caffe 原始构建方式的基线环境
2. **Jupyter + SSH 镜像**（`Dockerfile.jupyter-ssh`）：在基础镜像上叠加 SSH 服务、Jupyter Notebook/Lab 和 supervisord 进程管理，适合交互式开发和远程访问

两种镜像均**不走 scikit-build-core / pycaffe 迁移路径**，旨在提供简化、贴近 Caffe 原始构建方式的环境，便于学习、调试与对比验证。

## 目录结构

```
docker/origin/
├── config/                          # 配置文件目录
│   ├── profile.d/
│   │   └── caffe.sh                 # 环境变量配置（登录shell自动加载）
│   ├── supervisor/
│   │   └── conf.d/
│   │       ├── jupyter.conf         # Jupyter 服务配置
│   │       └── sshd.conf            # SSH 服务配置
│   ├── jupyter_notebook_config.py   # Jupyter Notebook 基础配置
│   ├── sshd_config                  # SSH 守护进程配置
│   └── supervisord.conf             # Supervisord 主配置
├── scripts/                         # 辅助脚本
│   ├── generate-makefile-config.sh  # 自动生成 Makefile.config
│   ├── healthcheck-jupyter.sh       # Jupyter 容器健康检查
│   └── verify-caffe.sh              # Caffe 安装验证脚本
├── .gitignore
├── BUILD_REPORT.md                  # 基础镜像构建验证报告
├── Dockerfile                       # 基础 CPU-only 运行时镜像（4阶段）
├── Dockerfile.jupyter-ssh           # Jupyter + SSH 镜像（4阶段，runtime-jupyter）
├── README.md                        # 本文件
├── build.sh                         # 基础镜像构建脚本
├── entrypoint-jupyter.sh            # Jupyter 容器入口脚本
├── run.sh                           # 基础容器运行脚本
└── run-jupyter.sh                   # Jupyter 容器一键管理脚本（start/stop/restart/status/logs）
```

## 快速开始

### 基础镜像

一键构建与运行命令示例：

```bash
# 构建（约 15-40 分钟）
cd docker/origin
./build.sh

# 运行容器
./run.sh

# 验证 import caffe
./run.sh -- python3 -c "import caffe; print(caffe.__version__)"
```

### Jupyter + SSH 镜像

```bash
# 构建 Jupyter+SSH 镜像
cd docker/origin
docker build -t caffe-cpu:jupyter --target runtime-jupyter -f Dockerfile.jupyter-ssh ../..

# 使用管理脚本启动（推荐）
./run-jupyter.sh start

# 查看访问信息
./run-jupyter.sh status
```

启动后访问：
- **Jupyter Notebook**: http://localhost:8888 （Token: `mysecret`）
- **SSH**: `ssh -p 2222 caffe-origin@localhost` （密码: `pass`）

## 构建

### 基础镜像构建

`build.sh` 封装了 `docker build` 调用，支持以下用法：

- `./build.sh` — 默认构建 runtime 阶段，标签 `caffe-cpu:latest`
- `./build.sh -t v1.0` — 指定标签
- `./build.sh --target builder-dev` — 构建指定阶段（可选：`base-system`、`base-builder`、`builder`、`runtime`）
- `./build.sh --no-cache` — 无缓存构建
- `./build.sh --build-arg BUILDER_UID=1001` — 传递构建参数
- `./build.sh -h` — 显示帮助

### Jupyter+SSH 镜像构建

```bash
# 构建 Jupyter 镜像
docker build -t caffe-cpu:jupyter --target runtime-jupyter \
  -f Dockerfile.jupyter-ssh ../../

# 指定构建参数
docker build -t caffe-cpu:jupyter --target runtime-jupyter \
  --build-arg BUILDER_UID=$(id -u) \
  --build-arg BUILDER_GID=$(id -g) \
  -f Dockerfile.jupyter-ssh ../../
```

### 构建耗时

| 构建类型 | 耗时 | 说明 |
|---------|------|------|
| 首次冷构建 | 15-40 分钟 | 从零拉取镜像 + apt/pip 安装 + Caffe 源码编译 |
| 缓存命中构建 | ~1 分钟 | base-system、base-builder 阶段命中 Docker 缓存 |

### 构建产物

| 镜像标签 | 大小 | 说明 |
|---------|------|------|
| `caffe-cpu:latest` | ~3.36GB | 基础运行时镜像 |
| `caffe-cpu:jupyter` | ~3.8-4.0GB | Jupyter+SSH 镜像（叠加 notebook、jupyterlab、openssh-server、supervisor） |

## 运行

### 基础容器运行

`run.sh` 封装了 `docker run` 调用，支持以下用法：

- `./run.sh` — 默认启动交互式 bash
- `./run.sh -n my-build` — 指定容器名
- `./run.sh -- ls -la` — 执行命令后自动删除容器
- `./run.sh -- python3 -c "import caffe; print(caffe.__version__)"` — 一次性命令
- `./run.sh --non-interactive -- python3 test.py` — 非交互式（适用于 CI/测试场景）
- `./run.sh -h` — 显示帮助

### Jupyter 容器管理

`run-jupyter.sh` 提供完整的容器生命周期管理：

| 命令 | 功能 |
|------|------|
| `./run-jupyter.sh start` | 启动容器（不存在则创建） |
| `./run-jupyter.sh stop` | 停止容器 |
| `./run-jupyter.sh restart` | 重启容器 |
| `./run-jupyter.sh status` | 查看状态和访问信息 |
| `./run-jupyter.sh logs` | 查看实时日志（Ctrl+C 退出） |
| `./run-jupyter.sh start --force-recreate` | 强制重建容器（解决配置不兼容问题） |
| `./run-jupyter.sh help` | 显示帮助 |

**环境变量配置**：

```bash
# 自定义密码和 Token
USER_PASSWORD=mypassword JUPYTER_TOKEN=mytoken ./run-jupyter.sh start

# 授予 sudo 权限（默认已开启）
GRANT_SUDO=yes ./run-jupyter.sh start
```

### 手动运行 Jupyter 容器

```bash
docker run -d \
  --name caffe-jupyter \
  --hostname caffe-jupyter \
  -p 2222:22 \
  -p 8888:8888 \
  -v $(pwd)/../../workspace:/workspace/notebooks \
  -e USER_PASSWORD=pass \
  -e JUPYTER_TOKEN=mysecret \
  -e GRANT_SUDO=yes \
  --restart unless-stopped \
  caffe-cpu:jupyter
```

### 容器内默认环境

| 配置项 | 基础镜像 | Jupyter 镜像 |
|--------|---------|-------------|
| 工作目录 | `/workspace/caffex` | `/workspace` |
| 挂载点 | 项目根目录 → `/workspace` | `workspace/` → `/workspace/notebooks` |
| 默认用户 | `builder`（UID 1000） | `caffe-origin`（UID 1000） |
| sudo 权限 | NOPASSWD | 通过 `GRANT_SUDO` 控制 |
| 默认命令 | `/bin/bash` | supervisord（启动 SSH + Jupyter） |
| 暴露端口 | 无 | 22（SSH）、8888（Jupyter） |
| 健康检查 | 无 | 每 30 秒检查 SSH 和 Jupyter 状态 |
| 时区 | UTC | Asia/Shanghai |
| 语言 | C.UTF-8 | zh_CN.UTF-8 |

## 环境变量

### 基础镜像环境变量

| 环境变量 | 值 | 说明 |
|---------|-----|------|
| `CAFFE_ROOT` | `/workspace/caffex` | Caffe 源码与编译产物根目录 |
| `PYTHONPATH` | `/workspace/caffex/python` | PyCaffe 模块搜索路径 |
| `LD_LIBRARY_PATH` | `/workspace/caffex/build/lib:/usr/lib/x86_64-linux-gnu` | 动态库搜索路径 |
| `PIP_INDEX_URL` | `https://mirrors.aliyun.com/pypi/simple` | pip 镜像源（构建期） |
| `DEBIAN_FRONTEND` | `noninteractive` | apt 非交互模式 |
| `LANG` / `LC_ALL` | `C.UTF-8` | 字符编码 |

### Jupyter 镜像环境变量

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `TZ` | `Asia/Shanghai` | 时区 |
| `LANG` / `LC_ALL` | `zh_CN.UTF-8` | 中文字符编码 |
| `NON_ROOT_USER` | `caffe-origin` | 非 root 用户名 |
| `JUPYTER_PORT` | `8888` | Jupyter 监听端口 |
| `SSH_PORT` | `22` | SSH 监听端口 |
| `GRANT_SUDO` | `no` | 是否授予 sudo NOPASSWD 权限（`yes`/`no`） |
| `ALLOW_ROOT_SSH` | `no` | 是否允许 root SSH 登录 |
| `JUPYTER_ALLOW_ORIGIN` | （空） | Jupyter CORS 允许源 |
| `USER_PASSWORD` | （自动生成） | 非 root 用户 SSH 密码 |
| `ROOT_PASSWORD` | （自动生成） | root 用户密码（需 `ALLOW_ROOT_SSH=yes`） |
| `JUPYTER_TOKEN` | （自动生成） | Jupyter 访问 Token |
| `JUPYTER_PASSWORD` | （未设置） | Jupyter 密码（设置后 Token 失效） |
| `SSH_PUBLIC_KEY` | （未设置） | SSH 公钥（注入 authorized_keys） |
| `ENABLE_SUDO_NOPASSWD` | （未设置） | 设为 `1`/`yes`/`true` 等价于 `GRANT_SUDO=yes` |
| `JUPYTER_CORS_ORIGIN` | （未设置） | Jupyter CORS 源（`JUPYTER_ALLOW_ORIGIN` 的别名） |
| `DEBUG` | `0` | 设为 `1` 启用入口脚本 debug 输出 |

**密码生成说明**：
- 若未设置 `USER_PASSWORD`，容器启动时会自动生成 16 位随机密码并打印到日志
- 若未设置 `JUPYTER_TOKEN`，容器启动时会自动生成 32 位随机 Token 并打印到日志
- 自动生成的密码/Token 仅在本次容器启动时有效，重启容器会重新生成（除非通过环境变量指定）

## Jupyter 镜像服务管理

Jupyter 镜像使用 **supervisord** 管理多个服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| sshd | 22 | SSH 远程登录服务 |
| jupyter | 8888 | Jupyter Notebook/Lab 服务 |

进入容器后管理服务：
```bash
# 查看服务状态
supervisorctl status

# 重启服务
supervisorctl restart jupyter
supervisorctl restart sshd

# 停止/启动服务
supervisorctl stop jupyter
supervisorctl start jupyter

# 查看服务日志
tail -f /var/log/supervisor/jupyter-stdout*.log
tail -f /var/log/supervisor/sshd-stdout*.log
```

## 与 conda 版本的差异

与 `docker/local/conda/Dockerfile` 的对比：

| 维度 | docker/origin（基础） | docker/origin（Jupyter） | docker/local/conda |
|------|----------------------|-------------------------|-------------------|
| 构建阶段数 | 4 | 4（runtime-jupyter） | 5（含 pycaffe-builder） |
| Python 模块路径 | `caffex/python`（原始） | `caffex/python`（原始） | `caffex/python` + `pycaffe/`（迁移） |
| 构建系统 | 仅 Make | 仅 Make | Make + scikit-build-core |
| 是否构建 wheel | 否 | 否 | 是（pycaffe wheel） |
| 脚本依赖 | 自包含 | 自包含 | 依赖 docker/local/lib/ |
| SSH + Jupyter | 否 | 是 | 否 |
| 进程管理 | 无 | supervisord | 无 |
| 镜像大小 | ~3.36GB | ~3.8-4.0GB | ~5.5GB |
| 时区/语言 | UTC/C.UTF-8 | Asia/Shanghai/zh_CN | 可配置 |
| 健康检查 | 无 | 内置 | 无 |
| 适用场景 | 简化基线、CI、命令行 | 交互式开发、远程访问 | 完整方案、wheel 可 pip 安装 |

### 何时选择哪个镜像

**选择 docker/origin 基础镜像**：
- 不需要 Jupyter Notebook 界面
- 不需要 SSH 远程登录
- 希望保持 Caffe 原始构建方式
- 用于 CI/CD 自动化测试
- 想要最小的镜像体积

**选择 docker/origin Jupyter 镜像**：
- 需要交互式 Notebook 开发环境
- 需要 SSH 远程访问容器
- 需要 supervisord 管理多个服务
- 适合教学演示和远程开发
- 需要中文环境和上海时区

**选择 docker/local/conda**：
- 需要 `pip install` 安装 pycaffe
- 希望使用现代 Python 打包工具链
- 需要 Python 3.13/3.14 版本
- 需要完整的开发与发布流程

## 常见问题

### 基础镜像相关

#### Q1: 构建失败提示 `boost_python310` 找不到

**原因**：系统未安装 `libboost-all-dev` 或 Boost.Python 库名称不匹配。

**解决**：
- 确认 `base-builder` 阶段已安装 `libboost-all-dev`
- 检查 `Makefile.config` 中 `PYTHON_LIBRARIES` 的值
- 在容器内执行 `ldconfig -p | grep boost_python` 查看可用的 Boost.Python 库
- 若库名称不同，修改 `scripts/generate-makefile-config.sh` 中的回退逻辑

#### Q2: protobuf 版本冲突

**原因**：Caffe 使用 protobuf 3.x，新版 protobuf 4.x 不兼容。

**解决**：
- 确认 `base-builder` 阶段固定 `protobuf==3.20.3`
- 若已安装 protobuf 4.x，卸载后重新安装 3.20.3：`pip uninstall protobuf && pip install protobuf==3.20.3`

#### Q3: HDF5 头文件找不到

**原因**：Ubuntu 22.04 的 HDF5 头文件位于 `/usr/include/hdf5/serial`，不在默认搜索路径。

**解决**：
- 确认 `Makefile.config` 中 `INCLUDE_DIRS` 包含 `/usr/include/hdf5/serial`
- 确认 `LIBRARY_DIRS` 包含 `/usr/lib/x86_64-linux-gnu/hdf5/serial`
- `generate-makefile-config.sh` 会自动检测并添加这些路径

#### Q4: run.sh 挂载导致镜像产物被覆盖

**现象**：使用 `./run.sh -- python3 -c "import caffe"` 时报 `ModuleNotFoundError: No module named 'caffe._caffe'`。

**原因**：`run.sh` 将宿主机 `vendor/caffe/` 目录挂载到容器 `/workspace`，**覆盖**了镜像内已编译的产物。

**解决**：
- **验证镜像产物**：使用 `docker run --rm caffe-cpu:latest <command>`（不挂载宿主机目录）
- **开发场景**：`run.sh` 的挂载行为是设计意图，需先在容器内执行 `make pycaffe` 重新编译

### Jupyter 镜像相关

#### Q5: 无法通过 SSH 登录，提示密码错误

**原因**：未设置 `USER_PASSWORD` 时容器会自动生成随机密码。

**解决**：
- 查看容器启动日志获取自动生成的密码：`./run-jupyter.sh logs`
- 启动时指定密码：`USER_PASSWORD=yourpass ./run-jupyter.sh start`
- 使用 SSH 公钥认证：设置 `SSH_PUBLIC_KEY` 环境变量

#### Q6: Jupyter 页面打不开或提示 Token 错误

**原因**：未设置 `JUPYTER_TOKEN` 时容器会自动生成随机 Token。

**解决**：
- 查看容器启动日志获取自动生成的 Token：`./run-jupyter.sh logs`
- 启动时指定 Token：`JUPYTER_TOKEN=yourtoken ./run-jupyter.sh start`
- 设置 Jupyter 密码替代 Token：`JUPYTER_PASSWORD=yourpass ./run-jupyter.sh start`
- 使用 `./run-jupyter.sh status` 快速查看访问信息

#### Q7: Jupyter 中无法 import caffe

**原因**：Jupyter 镜像的工作目录是 `/workspace`，Caffe 源码在 `/workspace/caffex/`（镜像内置，不随挂载覆盖）。

**解决**：
- 镜像内已配置好 `PYTHONPATH` 和 `CAFFE_ROOT`，新建 Notebook 可直接 `import caffe`
- 若在 `/workspace/notebooks/` 下工作，环境变量已通过 `/etc/profile.d/caffe.sh` 自动加载
- 若仍有问题，在 Notebook 中验证：
  ```python
  import sys
  print(sys.path)
  import os
  print(os.environ.get('PYTHONPATH'))
  ```

#### Q8: 容器启动后立即退出

**原因**：supervisord 启动失败或入口脚本报错。

**解决**：
- 查看日志定位错误：`./run-jupyter.sh logs`
- 检查端口是否被占用：`netstat -tlnp | grep -E '2222|8888'`
- 使用 `--force-recreate` 重建容器：`./run-jupyter.sh start --force-recreate`

#### Q9: Windows/WSL2 中挂载目录权限问题

**原因**：Windows 文件系统与 Linux 权限模型不兼容。

**解决**：
- Jupyter 镜像默认 UID/GID 为 1000，WSL2 中通常匹配
- 构建时自定义 UID：使用 `--build-arg BUILDER_UID=$(id -u)` 构建
- 容器内通过 sudo 修改权限：`sudo chown -R caffe-origin:caffe-origin /workspace/notebooks`

#### Q10: 如何安装额外的 Python 包？

**解决**：
- 进入容器安装（临时）：`docker exec -it caffe-jupyter pip install <package>`
- 基于镜像创建新 Dockerfile（持久化）：
  ```dockerfile
  FROM caffe-cpu:jupyter
  RUN pip install <package1> <package2>
  ```
- Jupyter Notebook 中使用 `!pip install <package>`（当前会话有效）

### 通用问题

#### Q11: 镜像体积过大

**原因**：`base-builder` 阶段保留了所有编译工具链。

**优化建议**：
- 当前镜像保留 build-essential 等工具便于调试
- 如需更小镜像可改为基于 `ubuntu:22.04` 的多阶段构建，仅复制运行时依赖
- 清理 apt/pip 缓存（已在 Dockerfile 中实现）

#### Q12: WSL2 中构建中断或卡住

**解决**：
- 检查 Docker Desktop 内存限制（建议 ≥ 8GB）
- 检查磁盘空间（建议 ≥ 10GB 可用）
- 查看详细构建日志：`./build.sh --no-cache` 或添加 `--progress=plain`
- 向上滚动找到第一个 `error:` 行定位问题

## 相关文档

- 基础镜像构建验证报告：[BUILD_REPORT.md](BUILD_REPORT.md)
- 构建脚本说明：[build.sh](build.sh)（`./build.sh -h` 查看完整选项）
- 基础运行脚本：[run.sh](run.sh)（`./run.sh -h` 查看完整选项）
- Jupyter 管理脚本：[run-jupyter.sh](run-jupyter.sh)（`./run-jupyter.sh help` 查看完整选项）
- Jupyter 入口脚本：[entrypoint-jupyter.sh](entrypoint-jupyter.sh)
- Makefile.config 生成：[scripts/generate-makefile-config.sh](scripts/generate-makefile-config.sh)
- Caffe 验证脚本：[scripts/verify-caffe.sh](scripts/verify-caffe.sh)
- Jupyter 健康检查：[scripts/healthcheck-jupyter.sh](scripts/healthcheck-jupyter.sh)
- SSH 配置：[config/sshd_config](config/sshd_config)
- Supervisord 配置：[config/supervisord.conf](config/supervisord.conf)
- Jupyter 配置：[config/jupyter_notebook_config.py](config/jupyter_notebook_config.py)
- 参考模板：[../local/conda/Dockerfile](../local/conda/Dockerfile)
- Caffe 源码：[../../caffex/](../../caffex/README.md)（只读，不修改）
