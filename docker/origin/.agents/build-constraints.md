# 构建约束与分发规则

> 本文件定义 Caffe Origin Docker 构建的核心约束，所有 Dockerfile、脚本、配置、文档修改必须遵守。

## 1. 版本锁定约束（最高优先级）

### 1.1 基础镜像

- **必须使用** `ubuntu:22.04`（指定版本标签，禁止使用 `ubuntu:latest` 或其他版本）
- **原因**：确保构建可复现；Ubuntu 22.04 提供 Python 3.10、gcc 11、glibc 2.35，与 Caffe 原始代码兼容

### 1.2 Python 与科学计算包版本

| 包 | 版本约束 | 原因 |
|----|---------|------|
| Python | 3.10（系统Python） | Ubuntu 22.04 默认 Python 3 版本 |
| numpy | `>=1.21,<2.0` | Caffe 原始代码使用 numpy 1.x API（如 `np.float`、`np.int` 等已在 numpy 2.0 移除的别名） |
| scipy | `>=1.7` | 与 numpy 1.x 兼容 |
| protobuf | `==3.20.3`（固定版本） | Caffe 的 PyCaffe 绑定使用 protobuf 3.x API；protobuf 4.x 移除/更改了多个内部接口导致 `import caffe` 失败 |
| pip | `==24.0` | 固定pip版本确保依赖解析一致性 |
| setuptools | `==68.0.0` | 与 Python 3.10 和 Cython 兼容 |

**禁止事项**：
- ❌ 不得升级到 `protobuf>=4.0`
- ❌ 不得升级到 `numpy>=2.0`
- ❌ 不得使用 conda/miniconda/anaconda 替代系统 Python
- ❌ 不得使用 `--break-system-packages` 以外的PEP 668绕过方式

### 1.3 系统依赖（apt）

必须安装的核心系统库：
- build-essential, cmake, git, wget, curl, pkg-config
- libboost-all-dev（含 libboost-python-dev for Python 3.10）
- libprotobuf-dev, protobuf-compiler
- libgoogle-glog-dev, libgflags-dev
- libhdf5-serial-dev
- libleveldb-dev, liblmdb-dev, libsnappy-dev
- libopencv-dev
- libopenblas-dev, libatlas-base-dev
- python3-dev, python3-pip, python3-numpy
- libgtest-dev（可选，用于测试）

## 2. 构建上下文与路径约束

### 2.1 构建上下文路径

**Docker 构建上下文必须是 `caffe/` 目录**（即 docker/origin/ 向上两层），而非 origin/ 目录。

正确的构建命令（build.sh 已封装）：
```bash
cd /path/to/caffe
docker build -t caffe-cpu:origin-runtime --target runtime \
  -f docker/origin/Dockerfile .
```

原因：需要同时访问以下目录：
- `caffex/` — BVLC Caffe 源码（C++、Python、tools、examples）
- `docker/origin/` — Dockerfile、scripts、config 配置文件

### 2.2 COPY 路径相对性

Dockerfile 中 COPY 指令的源路径**相对于构建上下文**（caffe/ 根目录），不是相对于 Dockerfile 所在目录。

正确示例：
```dockerfile
COPY docker/origin/scripts/verify-caffe.sh /usr/local/bin/   # ✅ 正确
COPY caffex /workspace/caffex                                 # ✅ 正确
```

错误示例：
```dockerfile
COPY scripts/verify-caffe.sh /usr/local/bin/                  # ❌ 错误：相对于caffe/根，不是docker/origin/
COPY ../../caffex /workspace/caffex                           # ❌ 错误：COPY不支持..路径
```

### 2.3 .dockerignore 约束

`caffe/.dockerignore`（相对于本目录是 `../../.dockerignore`）必须满足：
- ✅ 排除 `caffex/build/`、`caffex/distribute/`（编译产物在容器内生成，不发送到构建上下文）
- ✅ 排除 `docker/**/build/`、`docker/**/dist/`（各docker目录的构建和导出产物）
- ✅ 排除 `*.tar`、`*.tar.gz`、`*.zip`（镜像文件和压缩包）
- ✅ 排除 `.git/`、`.trae/`、`__pycache__/`（版本控制和缓存）
- ❌ 不得排除 `caffex/` 整个目录（需要源码编译）
- ❌ 不得排除 `docker/origin/` 整个目录（需要Dockerfile和scripts）

## 3. 多阶段构建约束

### 3.1 必须的构建阶段（runtime镜像）

Dockerfile 必须使用以下4阶段结构：

| 阶段 | FROM | 职责 | 产物 |
|------|------|------|------|
| `base-system` | `ubuntu:22.04` | apt换源（阿里云镜像）、CA证书、基础工具 | 基础OS层 |
| `base-builder` | `base-system` | gcc/g++/build-essential、Python科学计算包、系统依赖库、环境变量 | 编译环境 |
| `builder` | `base-builder` | 复制caffex/源码、生成Makefile.config、make all/test/pycaffe/tools/distribute | 编译产物 |
| `runtime` | `base-builder` | COPY --from=builder 编译产物、COPY scripts/、运行验证、HEALTHCHECK、CMD | 最终镜像 |

### 3.2 必须的构建阶段（jupyter镜像）

Dockerfile.jupyter-ssh 必须使用以下4阶段结构：

| 阶段 | FROM | 职责 |
|------|------|------|
| `base-system` | `ubuntu:22.04` | 同runtime |
| `base-builder` | `base-system` | 同runtime（包含中文locale、时区Asia/Shanghai） |
| `builder` | `base-builder` | 同runtime（caffex编译） |
| `runtime-jupyter` | `base-builder` | COPY编译产物 + 安装SSH/Jupyter/supervisord/tini + COPY config/ + entrypoint + HEALTHCHECK |

注意：jupyter镜像不基于runtime阶段（独立从base-builder构建），因为需要额外的系统包安装和不同用户配置。

### 3.3 镜像优化规则

- 多阶段构建中，builder阶段的编译工具链（build-essential等）存在于runtime镜像中（base-builder包含），这是为了保持镜像可调试性
- apt安装使用 `--no-install-recommends`，每个apt阶段后立即 `rm -rf /var/lib/apt/lists/*`
- pip安装使用 `--no-cache-dir`
- 相关RUN指令合并为单个指令，减少镜像层数
- 使用 `set -eux` 在RUN脚本开头确保失败即停且有日志输出
- 构建末尾在runtime阶段运行 `verify-caffe.sh`，验证失败则构建失败

## 4. 自包含分发约束

### 4.1 核心原则

分发给用户的镜像必须**完全自包含**：
- ✅ 所有编译产物、Python依赖、系统库均在镜像内
- ✅ 不依赖宿主机的任何文件或目录
- ✅ 用户 `docker load` 后无需额外安装任何依赖
- ✅ 可在任何 Docker 20.10+ 环境（Linux/macOS/Windows+WSL2）运行

### 4.2 run-standalone.sh 铁律

`run-standalone.sh` 作为分发用运行脚本，必须遵守：
- ❌ **禁止使用 `-v` 或 `--volume` 参数**挂载宿主机目录
- ❌ **禁止依赖** 宿主机上的caffex源码、模型文件、配置文件
- ✅ 端口绑定使用 `127.0.0.1:HOST_PORT:CONTAINER_PORT`（安全绑定localhost）
- ✅ 一次性命令模式自动添加 `--rm`（命令结束清理容器）
- ✅ Jupyter模式后台运行(-d)，启动后等待5秒显示访问信息
- ✅ 镜像不存在时给出友好提示和构建命令

### 4.3 export.sh 要求

- 默认导出两个镜像到 `dist/` 目录
- 文件名格式：`caffe-cpu-origin-{runtime|jupyter}_{YYYYMMDD}.tar`
- 支持 `--compress/-z` gzip压缩
- 导出后必须验证：文件存在、大小>0、包含manifest.json、SHA256校验和
- 导出前检查磁盘可用空间（至少8GB）
- 一个镜像导出失败不阻断另一个，最后汇总成功/失败

### 4.4 load-and-verify.sh 要求

- 自动检测 dist/ 目录下最新的匹配tar文件
- 支持 .tar 和 .tar.gz 格式
- 加载后运行 verify-caffe.sh 验证（使用 `--entrypoint verify-caffe.sh` 绕过jupyter的entrypoint）
- 验证成功后显示快速启动命令
- 处理加载错误（文件损坏、Docker未运行、文件不存在）

## 5. 开发模式 vs 分发模式（两套脚本严格区分）

### 5.1 开发模式脚本（run.sh / run-jupyter.sh）

- **用途**：本地开发调试
- **行为**：挂载宿主机caffex目录到容器内，覆盖镜像内编译产物
- **使用场景**：修改源码后在容器内 make pycaffe 快速测试
- **禁止用于分发**：这些脚本依赖宿主机源码，分发给用户会导致caffe导入失败

### 5.2 分发模式脚本（run-standalone.sh / export.sh / load-and-verify.sh）

- **用途**：构建可分发包和最终用户使用
- **行为**：不挂载宿主机任何目录，使用镜像内置产物
- **使用场景**：镜像导出、分发给用户、用户加载运行
- **必须配合**：export.sh导出 → 用户load-and-verify.sh加载 → run-standalone.sh运行

### 5.3 文档区分要求

- README.md（开发者文档）必须明确说明两套脚本的区别和使用场景
- USER_GUIDE.md（用户指南）**只介绍分发模式脚本**，不提及开发脚本
- 新增脚本时必须在AGENTS.md和.agents/规范中标明属于哪种模式

## 6. 验证脚本约束

### 6.1 verify-caffe.sh 验证项（12项，均为PASS级别）

| # | 检查项 | 类型 | 失败处理 |
|---|--------|------|---------|
| 1 | Python版本检查（python3 --version） | 必选 | FAIL |
| 2 | numpy导入和版本（<2.0） | 必选 | FAIL |
| 3 | scipy导入和版本 | 必选 | FAIL |
| 4 | google.protobuf版本（==3.x，拒绝4.x） | 必选 | FAIL |
| 5 | libcaffe.so动态库文件存在 | 必选 | FAIL |
| 6 | _caffe*.so Python扩展文件存在 | 必选 | FAIL |
| 7 | caffe模块导入（验证PYTHONPATH和LD_LIBRARY_PATH） | 必选 | FAIL |
| 8 | caffe版本号输出 | 必选 | FAIL |
| 9 | caffe.proto/caffe_pb2导入 | 必选 | FAIL |
| 10 | Blob创建测试（1x1x1x1 shape验证） | 必选 | FAIL |
| 11 | Blob数据读写测试（np.allclose验证） | 必选 | FAIL |
| 12 | caffe命令行工具检查 | 可选 | WARN |

### 6.2 输出格式要求

- 带颜色输出（非TTY自动禁用颜色）：绿色[PASS]、红色[FAIL]、黄色[WARN]、蓝色[INFO]、青色标题
- 最终汇总：总检查数、PASS数、FAIL数、WARN数
- 退出码：全部PASS→0；有FAIL→1
- 脚本必须可在容器内任意目录执行（CAFFE_ROOT默认/workspace/caffex）

## 7. 健康检查约束

### 7.1 runtime镜像HEALTHCHECK

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck-caffe.sh
```

healthcheck-caffe.sh 检查项：
1. Python3可用（python3 --version）
2. caffe可导入（`import caffe; caffe.set_mode_cpu()`）
3. libcaffe.so文件存在

### 7.2 jupyter镜像HEALTHCHECK

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD /usr/local/bin/healthcheck-jupyter.sh
```

- start-period较长（45s），因为supervisord启动SSH和Jupyter需要时间
- 检查sshd进程+端口22连通性
- 检查jupyter进程+端口8888 HTTP响应（200/302/401/403均视为健康）

## 8. 环境变量约束

### 8.1 runtime镜像必须设置的环境变量

在base-builder阶段设置：
```dockerfile
ENV WORKSPACE_DIR=/workspace \
    CC=gcc \
    CXX=g++ \
    CAFFE_ROOT=/workspace/caffex \
    PATH=/workspace/caffex/build/tools:${PATH} \
    LD_LIBRARY_PATH=/workspace/caffex/build/lib:/usr/lib:/usr/lib/x86_64-linux-gnu:/usr/local/lib \
    PYTHONPATH=/workspace/caffex/python
```

### 8.2 jupyter镜像额外环境变量

```dockerfile
ENV TZ=Asia/Shanghai \
    LANG=zh_CN.UTF-8 \
    LC_ALL=zh_CN.UTF-8
```

## 9. 用户与工作目录约束

| 配置 | runtime镜像 | jupyter镜像 |
|------|-----------|------------|
| 默认用户 | `builder`（UID 1000） | `caffe-origin`（UID 1000） |
| sudo权限 | NOPASSWD（builder用户） | 通过GRANT_SUDO环境变量控制 |
| WORKDIR | `/workspace` | `/workspace` |
| HOME | `/home/builder` | `/home/caffe-origin` |
| 默认CMD | `/bin/bash` | supervisord（通过entrypoint-jupyter.sh启动） |
| ENTRYPOINT | 无（空） | `/usr/bin/tini --` + CMD为entrypoint-jupyter.sh |

## 10. 禁止的修改模式

以下是已发现的反模式，禁止再次引入：

| 反模式 | 后果 | 正确做法 |
|--------|------|---------|
| protobuf升级到4.x | `import caffe` 失败，PyCaffe不兼容 | 锁定protobuf==3.20.3 |
| numpy升级到2.x | Caffe Python代码使用已移除的numpy别名导致运行错误 | 使用numpy>=1.21,<2.0 |
| COPY路径缺少docker/origin/前缀 | 构建上下文是caffe/，找不到scripts文件 | 使用`COPY docker/origin/scripts/xxx` |
| Dockerfile中inline创建脚本 | 文件系统版本与镜像内版本不一致 | COPY scripts/目录下的文件 |
| run-standalone.sh添加-v挂载 | 破坏自包含分发原则 | 绝不挂载；如需持久化使用docker volume或docker cp |
| 使用ubuntu:latest | 构建不可复现，未来版本可能破坏依赖 | 固定ubuntu:22.04 |
| verify-caffe.sh使用set -e | 第一个失败后退出，无法汇总所有结果 | 使用PASS/FAIL计数，最后汇总退出 |
| 开发脚本和分发脚本混用 | 用户拿到的镜像无法独立运行 | 严格区分两套脚本，USER_GUIDE只提分发脚本 |
| Jupyter端口绑定到0.0.0.0且暴露公网 | 安全风险 | 绑定到127.0.0.1（run-standalone.sh中） |
| .sh文件使用CRLF行尾 | Linux容器内执行报错 `/bin/bash^M: bad interpreter` | .gitattributes配置`*.sh text eol=lf`确保LF |
| 验证脚本将caffe命令行工具标记为FAIL | 工具可能未编译或路径问题不应阻断核心验证 | 标记为WARN，不返回失败 |

## 11. 脚本可执行权限

- 所有 .sh 文件必须设置可执行权限（`chmod +x`）
- Dockerfile中COPY脚本后必须在同一层或后续RUN中设置chmod +x
- git中通过 `.gitattributes` 的 `eol=lf` 保证行尾，但chmod需要显式设置

## 12. Jupyter镜像特殊约束

### 12.1 服务管理

- 使用 **tini** 作为PID 1（ENTRYPOINT），处理信号和僵尸进程
- 使用 **supervisord** 管理 jupyter 和 sshd 两个服务，配置autorestart=true
- entrypoint-jupyter.sh 负责：密码生成/设置、SSH host key生成、Jupyter配置、权限设置、打印访问信息、exec supervisord

### 12.2 默认凭证（可通过环境变量覆盖）

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `USER_PASSWORD` | `pass` | SSH密码（未设置时使用此默认值，非自动生成） |
| `JUPYTER_TOKEN` | `mysecret` | Jupyter访问Token |
| `GRANT_SUDO` | `yes` | 是否授予sudo NOPASSWD权限 |

### 12.3 端口映射

- Jupyter：`127.0.0.1:8888:8888`
- SSH：`127.0.0.1:2222:22`
- 绑定到localhost是安全默认，用户需要公网访问时可自行修改端口映射
