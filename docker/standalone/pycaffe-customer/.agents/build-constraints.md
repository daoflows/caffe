# 构建约束与分发规则

> 本文件定义 PyCaffe Customer 客户分发镜像构建的核心约束，所有 Dockerfile、脚本、配置、文档修改必须遵守。

## 1. 客户交付导向约束

### 1.1 开箱即用要求

客户镜像必须满足开箱即用：
- ✅ 默认配置即可启动并运行所有服务
- ✅ 内置 ResNet-50 演示模型和推理脚本
- ✅ 内置 `caffe-verify` 自验证命令，7项检查全部通过
- ✅ 启动日志清晰显示访问地址和凭据信息
- ⚠️ README.md 必须明确提示生产环境修改默认凭据

### 1.2 默认凭据安全提示

README.md 和容器启动日志中必须醒目提示：
- 默认 SSH 密码：`caffepass`（用户 `builder`）
- 默认 Jupyter Token：`caffe-token`
- 生产环境必须通过环境变量修改：`-e USER_PASSWORD=xxx -e JUPYTER_TOKEN=xxx`

### 1.3 国内用户支持

build.sh 必须支持 `--china` 参数：
- APT 源：使用北京外国语大学镜像（mirrors.bfsu.edu.cn）
- PyPI 源：使用清华大学镜像（pypi.tuna.tsinghua.edu.cn）
- 构建时检测 `--china` 标志，传递 Docker build-arg 给 Dockerfile

## 2. 隔离性约束（最高优先级）

### 2.1 零 caffex 依赖规则

customer 镜像的核心设计目标是**完全独立于 caffex/ 目录**，仅使用 `caffe-slim/` 推理引擎。

**禁止事项**：
- ❌ Dockerfile 中不得出现 `COPY caffex/`、`ADD caffex/` 或任何引用 caffex 路径的指令
- ❌ 脚本中不得硬编码 `/caffex/`、`caffex/python` 路径
- ❌ Python 代码中不得 import caffex 目录下的模块
- ❌ 配置文件中不得引用 caffex 下的 prototxt 或模型文件
- ❌ 不得将 caffex 目录纳入 Docker 构建上下文（通过 .dockerignore 排除）

**允许的 caffex 引用**（仅注释说明性文字，不影响构建）：
- ✅ Dockerfile 注释中说明"不依赖 caffex/"
- ✅ 文档中对比 customer 镜像与原版 BVLC Caffe 差异时提及 caffex

### 2.2 隔离性验证方法

构建前检查（源码层面）：
```bash
cd /path/to/vendor/caffe/docker/standalone/pycaffe-customer
grep -rn "caffex" --include="*.sh" --include="*.py" --include="Dockerfile*" --include="*.conf" --include="*.md" .
```

构建后检查（容器层面）：
```bash
docker exec <container> bash -c "find / -name '*caffex*' -type f 2>/dev/null | head -20"
```

## 3. 构建上下文约束

### 3.1 构建上下文路径

**Docker 构建上下文必须是 `vendor/` 目录**（即 caffe/ 的父目录），而非 pycaffe-customer/ 目录。

原因：需要同时访问以下两个子模块：
- `caffe/caffe-slim/` — 推理引擎源码（C++、pycaffe、caffeproto）
- `tvm-ffi/` — TVM FFI 依赖
- `caffe/docker/standalone/pycaffe-customer/` — 本目录的配置和脚本

正确的构建命令（使用 build.sh）：
```bash
cd caffe/docker/standalone/pycaffe-customer
./build.sh              # 标准构建
./build.sh --china      # 国内镜像构建
```

build.sh 内部会自动切换到 vendor/ 目录执行 docker build。

直接使用 docker build 的正确命令：
```bash
cd /path/to/vendor    # 必须在 vendor/ 目录下
docker build -t caffe-cpu:customer --target customer-runtime \
  -f caffe/docker/standalone/pycaffe-customer/Dockerfile .
```

### 3.2 .dockerignore 约束

`Dockerfile.dockerignore`（本目录内）必须满足：
- ✅ 排除 `caffex/` 目录（不需要进入构建上下文）
- ✅ 排除 `.git/`、`__pycache__/`、`*.pyc` 等无关文件
- ❌ 不得排除 `tvm-ffi/3rdparty/libbacktrace/` 整个目录
- ✅ 仅排除 `tvm-ffi/3rdparty/libbacktrace/.git`（Git元数据不需要）

## 4. 基础镜像与环境约束

### 4.1 基础镜像固定

- **必须使用** `ubuntu:26.04`（指定版本标签，禁止使用 `ubuntu:latest`）
- **原因**：确保构建可复现；26.04 提供 Python 3、较新的 gcc/cmake，且与 numpy 2.x 兼容

### 4.2 时区配置

构建时必须配置时区为 Asia/Shanghai（三层保障）：
1. apt-get install tzdata
2. ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
3. echo Asia/Shanghai > /etc/timezone
4. ENV TZ=Asia/Shanghai

### 4.3 Python 环境

- **Python 版本**：使用 Ubuntu 26.04 系统 Python 3（不额外安装 Miniconda/venv）
- **包管理**：pip + `--break-system-packages` 标志（PEP 668 合规）
- **numpy 版本**：`numpy>=2`（禁止 pin 到 numpy<2）
- **protobuf**：设置 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`，避免 C++ 实现版本冲突

### 4.4 预装软件包

customer 镜像必须预装的核心包：
- **Python科学计算**：numpy, scipy, matplotlib, scikit-image, h5py, networkx, pandas
- **Caffe依赖**：pyyaml, pillow, six, Cython, protobuf, python-dateutil, python-gflags, tabulate
- **Jupyter生态**：notebook, jupyterlab, ipykernel, nbconvert, jupyter_server
- **服务组件**：openssh-server, supervisor, tini, gosu
- **系统工具**：curl, wget, git, ca-certificates

## 5. 多阶段构建约束

### 5.1 必须的构建阶段

Dockerfile 必须使用以下4阶段结构：

| 阶段 | 基础 | 职责 |
|------|------|------|
| `base-system` | `ubuntu:26.04` | 时区配置、CA证书、基础工具（curl/wget/git等）、apt源配置（支持中国镜像） |
| `base-builder` | `base-system` | gcc/g++/cmake/ninja/protobuf-compiler/libopenblas-dev + Python科学计算包 + 构建依赖 |
| `caffe-builder` | `base-builder` | 复制caffe-slim/ + tvm-ffi/，scikit-build-core驱动CMake+Ninja编译，打包wheel |
| `customer-runtime` | `base-system` | 安装wheel、安装Jupyter/SSH/supervisord、复制config/scripts/examples、配置用户、设置HEALTHCHECK、清理构建工具 |

### 5.2 镜像优化规则

- 多阶段构建中，builder阶段的编译工具链（gcc/cmake/ninja等）**不得**进入customer-runtime镜像
- customer-runtime阶段只保留运行时必需的软件包
- apt安装使用 `--no-install-recommends`，每个apt阶段后立即 `rm -rf /var/lib/apt/lists/*`
- pip安装使用 `--no-cache-dir`
- 相关RUN指令合并，减少镜像层数
- COPY使用 `--chown=builder:builder` 直接设置所有权
- 最终镜像体积控制在 2-2.5 GB 左右

## 6. 安全约束

### 6.1 非 root 用户运行

- 容器内创建非 root 用户 `builder`（UID 1000, GID 1000）
- 默认以 `builder` 用户身份运行服务
- 使用 `gosu` 在 entrypoint 中进行权限降级
- 可选 `GRANT_SUDO=yes` 环境变量授予 sudo 权限（默认不授予）

### 6.2 SSH 安全加固

- 禁用 root 用户 SSH 登录（`PermitRootLogin no`）
- 仅允许非 root 用户密码认证
- 禁用空密码登录
- 使用 ED25519 主机密钥优先
- **每次容器启动时重新生成 SSH 主机密钥**（entrypoint.sh 中执行 `ssh-keygen -A`）
- 支持 `DISABLE_SSH=yes` 环境变量完全禁用 SSH 服务

### 6.3 进程管理与信号处理

- 使用 `tini` 作为 PID 1（ENTRYPOINT），正确处理信号和僵尸进程
- 使用 `supervisord` 管理 Jupyter 和 SSH 双服务，支持自动重启
- HEALTHCHECK 同时检测 SSH(22) 和 Jupyter(8888) 端口

### 6.4 无构建工具

customer-runtime 阶段必须完全移除编译器工具链：
- ❌ 不得包含 gcc、g++、cmake、ninja、make、git 等构建工具
- ❌ 不得包含 Python 开发头文件（python3-dev）
- ✅ 仅保留运行时必需的共享库和 Python 包

## 7. 验证约束

### 7.1 caffe-verify 7项检查

`scripts/caffe-verify` 必须包含以下7项检查，全部PASS才算验证通过：

| 序号 | 检查项 | 说明 |
|------|--------|------|
| 1 | pycaffe import successful | 能成功 `import caffe` |
| 2 | pycaffe version: 1.0.0-slim | 版本号正确 |
| 3 | pycaffe.Net class is available | Net类可实例化 |
| 4 | LeNet forward pass successful | LeNet模型前向推理成功 |
| 5 | Jupyter is responding on port 8888 | Jupyter HTTP服务可访问 |
| 6 | SSH is listening on port 22 | SSH端口在监听 |
| 7 | ResNet50 inference completed successfully | ResNet-50演示模型推理成功 |

运行方式：
```bash
docker exec <container> caffe-verify
```

### 7.2 caffe-slim API 差异

customer 镜像使用 caffe-slim（推理-only版本），与完整BVLC Caffe存在以下API差异：

| 差异 | caffe-slim 行为 | 完整BVLC Caffe行为 |
|------|----------------|-------------------|
| `net.forward()` 返回值 | 返回 `None`（推理已执行但不返回dict） | 返回输出blobs的dict |
| 获取输出数据 | 通过 `net.blobs['prob'].data` 访问 | forward()返回值或blobs均可 |
| Solver类 | 不可用（no training） | 可用（SGD/Adam等训练器） |
| 辅助子模块 | classifier/detector/draw/io不可用 | 全部可用 |
| 训练相关功能 | 不支持 | 支持（Solver/训练循环） |

验证脚本注意：检查 `net.forward()` 时，不抛异常即为成功，不要断言返回值类型。

## 8. 运行时配置约束

### 8.1 ENTRYPOINT 与 CMD

- 使用 `tini` 作为 ENTRYPOINT：`ENTRYPOINT ["/usr/bin/tini", "--"]`
- CMD 启动 entrypoint.sh：`CMD ["/usr/local/bin/entrypoint.sh"]`
- entrypoint.sh 最终启动 supervisord
- 运行时可覆盖 CMD：`docker run ... bash` 进入交互shell

### 8.2 环境变量

支持的环境变量（均有默认值）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `USER_PASSWORD` | `caffepass` | builder用户SSH密码 |
| `JUPYTER_TOKEN` | `caffe-token` | Jupyter认证Token |
| `JUPYTER_PORT` | `8888` | Jupyter内部端口 |
| `SSH_PORT` | `22` | SSH内部端口 |
| `DISABLE_SSH` | `no` | 设为yes/1/true禁用SSH |
| `GRANT_SUDO` | `no` | 设为yes授予builder sudo权限 |
| `JUPYTER_PASSWORD` | （未设置） | 设置Jupyter密码替代Token |
| `TZ` | `UTC` | 时区（可设为Asia/Shanghai） |

必须在Dockerfile中设置的环境变量：
```dockerfile
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

### 8.3 工作目录与数据卷

- `WORKDIR /workspace`
- `/workspace/examples/` → 符号链接到 `/opt/caffe-examples/`（演示模型和脚本）
- `/workspace/user-data/` → 推荐的用户数据挂载点
- builder用户主目录：`/home/builder/`

### 8.4 暴露端口

- `EXPOSE 8888` — Jupyter Notebook
- `EXPOSE 22` — SSH

客户运行时通过 `-p 8888:8888 -p 2222:22` 映射到主机。

## 9. 导出与分发约束

### 9.1 export.sh 功能要求

export.sh 必须支持：
- `-z`：使用 gzip 压缩（生成 .tar.gz）
- `-t <tag>`：Docker镜像标签（默认 `caffe-cpu:customer`）
- `-o <dir>`：输出目录（默认当前目录）
- `--version <ver>`：版本号（默认从 `/etc/caffe-customer-release` 读取或使用日期）

### 9.2 导出产物

export.sh 必须生成：
1. 镜像文件：`caffe-cpu-customer-<version>-<date>.tar`（或 `.tar.gz`）
2. 校验文件：`caffe-cpu-customer-<version>-<date>.tar.sha256`（SHA256校验和）

### 9.3 构建元数据

容器内 `/etc/caffe-customer-release` 必须包含：
- 镜像版本号
- 构建日期
- Caffe版本
- tvm-ffi版本
- Python版本
- 构建模式（standard/china）

## 10. 子模块依赖

构建前必须初始化两个git子模块：

```bash
cd /path/to/vendor
git submodule update --init --recursive
```

验证子模块完整性：
```bash
ls caffe/caffe-slim/CMakeLists.txt && echo "caffe-slim OK"
ls tvm-ffi/CMakeLists.txt && echo "tvm-ffi OK"
ls caffe/docker/standalone/pycaffe-customer/Dockerfile && echo "pycaffe-customer OK"
```

## 11. 禁止的修改模式

以下是已发现的反模式，禁止再次引入：

| 反模式 | 后果 | 正确做法 |
|--------|------|---------|
| Dockerfile中inline创建验证脚本 | 文件系统版本与镜像内版本不一致 | COPY scripts/目录下的文件 |
| .dockerignore排除libbacktrace整个目录 | CMake找不到tvm-ffi的源文件，构建失败 | 仅排除.git |
| numpy<2版本锁定 | 与Ubuntu 26.04系统Python不兼容 | 使用numpy>=2 |
| 验证脚本将Solver类标记为FAIL | slim版本无Solver，构建被错误阻断 | 训练相关标记为WARN（或不检查） |
| ENTRYPOINT设为python | `docker run ... bash` 执行python bash报错 | ENTRYPOINT用tini，CMD启动entrypoint |
| 验证脚本断言forward()返回dict | caffe-slim返回None，断言失败 | 不抛异常即为成功 |
| 以root用户运行服务 | 安全风险 | 使用builder用户+gosu降级 |
| 不重新生成SSH主机密钥 | 所有容器共享相同密钥，安全风险 | entrypoint.sh中每次启动ssh-keygen -A |
| 最终镜像包含构建工具 | 镜像体积过大、攻击面大 | 多阶段构建，customer-runtime不包含gcc/cmake等 |
| README中不提示修改默认凭据 | 客户部署后存在安全风险 | 醒目位置提示生产环境修改密码 |
| 不支持国内镜像源 | 中国大陆用户构建缓慢/失败 | build.sh --china支持APT/PyPI镜像 |
