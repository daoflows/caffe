# PyCaffe Jupyter SSH 独立 Docker 镜像

基于 `ubuntu:26.04`，整合 PyCaffe 运行时、OpenSSH Server 和 Jupyter Notebook/Lab，通过 supervisord 管理双服务。从零构建 PyCaffe wheel，并集成 `apps/jupyter-ssh-base` 的标准化配置与启动逻辑。

## ✨ 特性

- **基础镜像**：Ubuntu 26.04（固定标签，非 latest）
- **PyCaffe 集成**：自包含编译，scikit-build-core + CMake + Ninja 构建 wheel
- **双服务管理**：Supervisord 管理 sshd + Jupyter，支持自动重启
- **企业级 SSH**：ED25519 优先密钥，非 root 用户，密码复杂度保障
- **安全增强 Jupyter**：密码/Token 认证，CORS 配置，非 root 运行
- **中文环境**：zh_CN.UTF-8 locale + Asia/Shanghai 时区
- **镜像优化**：多阶段构建，apt 缓存清理，最小化攻击面
- **灵活配置**：环境变量驱动，支持运行时自定义
- **健康检查**：内置 HEALTHCHECK，可监控服务状态
- **Tini 初始化**：使用 tini 作为 PID 1，正确处理信号和僵尸进程

## 文件结构

```
docker/standalone/pycaffe-jupyter-ssh/
├── config/
│   ├── supervisord.conf            # Supervisord 主配置
│   ├── sshd_config                 # SSH 服务完整配置
│   ├── jupyter_notebook_config.py  # Jupyter 基础配置
│   └── supervisor/
│       └── conf.d/
│           ├── sshd.conf           # SSH 进程配置
│           └── jupyter.conf        # Jupyter 进程配置
├── scripts/
│   └── healthcheck.sh              # 容器健康检查脚本
├── Dockerfile                      # 4 阶段多阶段构建文件
├── entrypoint.sh                   # 容器启动脚本
└── README.md                       # 本文档
```

## 构建流水线

```
base-system → base-builder → pycaffe-builder → runtime
  (apt换源)    (工具链+Py)   (CMake+Ninja)   (wheel+SSH+Jupyter)
```

| 阶段 | 基础镜像 | 职责 |
|------|----------|------|
| `base-system` | `ubuntu:26.04` | 阿里云镜像源、CA 证书、基础工具、Python 环境 |
| `base-builder` | `base-system` | gcc/cmake/ninja/protobuf/openblas + Python 科学计算包（numpy/scipy/matplotlib 等），创建 builder 用户 |
| `pycaffe-builder` | `base-builder` | 复制 `caffe-slim/` + `tvm-ffi/`，通过 scikit-build-core 驱动 CMake+Ninja 编译 caffe_core 和 _caffe.so，打成 wheel |
| `runtime` | `base-builder` | 安装 wheel + SSH/Jupyter 运行时包，配置 supervisord，验证 `import pycaffe`，HEALTHCHECK |

## 自包含编译原理

`caffe-slim/pycaffe/CMakeLists.txt` 一站式完成：
1. 编译 `caffe_core` 静态库（`caffe-slim/src/caffe/*.cpp`）
2. 编译 `_caffe.so` 共享库（`caffe-slim/pycaffe/caffe-slim/pycaffe/_caffe.cpp`）
3. 打包 `tvm_ffi` 共享库到 wheel

整个过程由 `scikit-build-core` 驱动，无需预先编译 Caffe 库。

## 构建

> **注意**：构建上下文必须是 `vendor/` 目录，以同时访问 `caffe/caffe-slim/`、`tvm-ffi/` 和本目录。

```bash
cd vendor

docker build -t caffe-cpu:pycaffe-jupyter-ssh --target runtime \
  -f caffe/docker/standalone/pycaffe-jupyter-ssh/Dockerfile .
```

构建阶段输出带有 `[BUILD]` 前缀的日志，便于追踪进度。构建完成后会自动进行验证：
- sshd 配置语法检查
- supervisord 可用性验证
- Python/pip 可用性验证
- Jupyter 可用性验证
- PyCaffe 导入验证
- entrypoint.sh 和 healthcheck.sh 语法检查

## 运行

### 基本运行（SSH + Jupyter）

```bash
docker run -d \
  --name pycaffe-jupyter-ssh \
  -p 2222:22 \
  -p 8888:8888 \
  -v $(pwd)/workspace:/workspace \
  -e USER_PASSWORD=your_secure_password \
  -e JUPYTER_TOKEN=your_jupyter_token \
  caffe-cpu:pycaffe-jupyter-ssh
```

### 查看日志（获取随机密码/token）

如果未设置 `USER_PASSWORD` 或 `JUPYTER_TOKEN`，容器启动时会自动生成随机密码/Token 并打印到日志：

```bash
docker logs -f pycaffe-jupyter-ssh
```

### 调试模式（不启动服务，直接进入 bash）

```bash
docker run -it --rm caffe-cpu:pycaffe-jupyter-ssh bash
```

此模式下仅执行系统诊断和密码设置，不启动 supervisord 和服务，方便调试和手动操作。

## 🔌 连接方式

### SSH 连接

```bash
# 使用密码登录（端口根据实际映射调整）
ssh builder@localhost -p 2222

# 使用公钥登录（启动时传入 SSH_PUBLIC_KEY 环境变量）
ssh builder@localhost -p 2222 -i ~/.ssh/id_ed25519
```

默认用户为 `builder`（UID 1000），工作目录为 `/workspace`。

### Jupyter Notebook/Lab

打开浏览器访问：
```
http://localhost:8888/
```

使用启动时设置的 `JUPYTER_TOKEN` 或 `JUPYTER_PASSWORD` 登录。

JupyterLab 也已安装，可访问：
```
http://localhost:8888/lab
```

## ⚙️ 环境变量配置

| 环境变量 | 默认值 | 说明 |
|---------|-------|------|
| `USER_PASSWORD` | *(随机生成)* | builder 用户密码，未设置时自动生成16位随机密码并打印到日志 |
| `ROOT_PASSWORD` | *(不设置)* | root 用户密码，需同时设置 ALLOW_ROOT_SSH=yes |
| `JUPYTER_TOKEN` | *(随机生成)* | Jupyter Notebook 访问令牌 |
| `JUPYTER_PASSWORD` | *(空)* | Jupyter Notebook 密码（与 Token 二选一） |
| `ALLOW_ROOT_SSH` | `no` | 是否允许 root 通过 SSH 登录 |
| `GRANT_SUDO` | `no` | 是否允许 builder 无密码 sudo |
| `SSH_PUBLIC_KEY` | *(空)* | SSH 公钥，设置后自动注入 authorized_keys |
| `JUPYTER_PORT` | `8888` | Jupyter 监听端口（容器内部） |
| `SSH_PORT` | `22` | SSH 监听端口（容器内部） |
| `TZ` | `Asia/Shanghai` | 时区设置 |
| `DEBUG` | `0` | 调试模式（1 启用 set -x） |

## 📋 服务管理

容器内使用 supervisord 管理服务，可通过 `docker exec` 执行管理命令：

```bash
# 查看服务状态
docker exec pycaffe-jupyter-ssh supervisorctl status

# 重启服务
docker exec pycaffe-jupyter-ssh supervisorctl restart sshd
docker exec pycaffe-jupyter-ssh supervisorctl restart jupyter

# 查看日志
docker exec pycaffe-jupyter-ssh supervisorctl tail -f sshd
docker exec pycaffe-jupyter-ssh supervisorctl tail -f jupyter
```

预期状态输出：
```
jupyter                          RUNNING   pid XX, uptime X:XX:XX
sshd                             RUNNING   pid XX, uptime X:XX:XX
```

## 🔍 验证

### PyCaffe 导入验证

```bash
# 快速导入验证
docker run --rm caffe-cpu:pycaffe-jupyter-ssh \
  python -c "import pycaffe; print('pycaffe version:', pycaffe.__version__)"

# 完整验证脚本
docker run --rm caffe-cpu:pycaffe-jupyter-ssh verify-pycaffe.sh
```

### 健康检查

容器内置 HEALTHCHECK，自动检测 SSH 和 Jupyter 服务状态：

```bash
# 查看容器健康状态
docker inspect --format='{{.State.Health.Status}}' pycaffe-jupyter-ssh

# 在容器内手动执行健康检查
docker exec pycaffe-jupyter-ssh healthcheck.sh
```

健康检查同时验证：
- SSH 端口 22 是否可连接
- Jupyter HTTP 端口 8888 是否响应

### 中文环境验证

```bash
docker exec pycaffe-jupyter-ssh bash -c 'echo "LANG=$LANG"; date; ls -la /etc/localtime'
```

预期输出：
- `LANG=zh_CN.UTF-8`
- 时区显示为 CST（China Standard Time）
- `/etc/localtime` 指向 `/usr/share/zoneinfo/Asia/Shanghai`

### SSH 连接测试

```bash
# 使用密码连接（需要已设置 USER_PASSWORD 或查看日志获取随机密码）
ssh -o StrictHostKeyChecking=no -p 2222 builder@localhost "echo 'SSH connection successful'; python -c 'import pycaffe; print(pycaffe.__version__)'"
```

### Jupyter HTTP 检测

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/api
```

预期返回状态码：200、302、401 或 403（均表示服务正常运行）。

## 🔒 安全特性

1. **非 root 默认用户**：builder（UID 1000），所有服务以非 root 运行
2. **SSH 安全配置**：
   - 禁用 root 登录（默认，可通过 ALLOW_ROOT_SSH=yes 启用）
   - ED25519 密钥优先
   - 禁用空密码
   - 严格模式（StrictModes yes）
3. **Jupyter 安全配置**：
   - Token/Password 认证
   - 绑定 0.0.0.0 但受端口映射控制
   - 跨域策略默认同源限制
4. **运行时密钥生成**：SSH host keys 在容器启动时生成，避免密钥复用
5. **最小化安装**：使用 --no-install-recommends，清理 apt 缓存和临时文件

## 🐍 Python 环境

- **Python 版本**：Ubuntu 26.04 系统 Python 3
- **包管理**：pip（使用 `--break-system-packages` 标志，PEP 668）
- **预装科学计算包**：numpy, scipy, matplotlib, scikit-image, h5py, networkx, pandas, pyyaml, pillow, six, Cython, protobuf, python-dateutil, python-gflags
- **Jupyter 组件**：notebook 7.2.2, jupyterlab 4.2.5, ipykernel 6.29.5, nbconvert 7.16.4, jupyter_server 2.14.1
- **PyCaffe**：从 caffe-slim 源码编译的 wheel 包

## 🔧 构建优化说明

- **4阶段构建**：逻辑分层，便于维护和缓存利用
- **层合并**：相关 RUN 指令合并，减少镜像层数
- **no-install-recommends**：最小化安装包数量
- **缓存清理**：每个 apt 阶段后立即清理
- **pip --no-cache-dir**：不缓存 pip 安装文件
- **特定版本标签**：ubuntu:26.04，避免 latest 的不确定性
- **--chown 标志**：COPY 时直接设置文件所有权，避免额外的 chown 层

## 📝 版本信息

- **基础镜像**：ubuntu:26.04
- **Python**：系统 Python 3 (Ubuntu 26.04 默认)
- **Jupyter Notebook**：7.2.2
- **JupyterLab**：4.2.5
- **OpenSSH**：Ubuntu 26.04 官方包
- **Supervisor**：Ubuntu 26.04 官方包
- **Tini**：Ubuntu 26.04 官方包
- **Caffe**：caffe-slim（自包含编译）
- **构建系统**：scikit-build-core + CMake + Ninja

## 与 jupyter-ssh-base 的关系

本镜像复用了 `apps/jupyter-ssh-base/` 的以下资源和配置模式：

- **配置文件**：sshd_config、supervisord.conf、jupyter_notebook_config.py、supervisor/conf.d/ 下的服务配置
- **启动脚本**：entrypoint.sh 的核心逻辑（6步启动流程、密码设置、SSH key 生成、Jupyter 动态配置、访问信息打印）
- **健康检查**：healthcheck.sh 双服务检测模式
- **环境变量**：USER_PASSWORD、JUPYTER_TOKEN、ALLOW_ROOT_SSH、GRANT_SUDO、SSH_PUBLIC_KEY 等
- **安全最佳实践**：非 root 用户、运行时密钥生成、最小化安装等

关键差异：
- 用户为 `builder`（与 pycaffe 保持一致）而非 `jupyteruser`
- 使用系统 Python，不使用 venv
- 集成了 PyCaffe wheel 的构建和安装
- 包含 pycaffe 验证脚本（verify-pycaffe.sh、verify-parity.sh）
- 构建上下文为 `vendor/` 目录，需访问 caffe-slim 和 tvm-ffi 源码

## 常见问题

### Q: 如何获取随机生成的密码/Token？
A: 查看容器启动日志：`docker logs pycaffe-jupyter-ssh`，搜索 `[IMPORTANT]` 标记的区域。

### Q: 如何持久化工作数据？
A: 使用卷挂载到 `/workspace` 目录，如 `-v $(pwd)/workspace:/workspace`。

### Q: 如何安装额外的 Python 包？
A: 进入容器后使用 `pip install --break-system-packages <package>`，或基于本镜像创建子镜像。

### Q: 如何启用 root SSH 登录？
A: 运行时添加 `-e ALLOW_ROOT_SSH=yes -e ROOT_PASSWORD=your_root_password`。

### Q: 构建失败提示找不到 caffe-slim 或 tvm-ffi？
A: 确保构建上下文是 `vendor/` 目录，且已执行 `git submodule update --init` 初始化子模块。

### Q: 如何启用 sudo 权限？
A: 运行时添加 `-e GRANT_SUDO=yes`，builder 用户将获得无密码 sudo 权限。
