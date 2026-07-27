# 构建约束与隔离规则

> 本文件定义 Caffe Standalone Docker 构建的核心约束，所有 Dockerfile、脚本、配置修改必须遵守。

## 1. 隔离性约束（最高优先级）

### 1.1 零 caffex 依赖规则

standalone 镜像的核心设计目标是**完全独立于 caffex/ 目录**，仅使用 `caffe-slim/` 推理引擎。

**禁止事项**：
- ❌ Dockerfile 中不得出现 `COPY caffex/`、`ADD caffex/` 或任何引用 caffex 路径的指令
- ❌ 脚本中不得硬编码 `/caffex/`、`caffex/python` 路径
- ❌ Python 代码中不得 import caffex 目录下的模块
- ❌ 配置文件中不得引用 caffex 下的 prototxt 或模型文件
- ❌ 不得将 caffex 目录纳入 Docker 构建上下文（通过 .dockerignore 排除）

**允许的 caffex 引用**（仅注释说明性文字，不影响构建）：
- ✅ Dockerfile 注释中说明"不依赖 caffex/"
- ✅ verify-parity.sh 中打印 "Parity check not applicable for slim inference-only build"
- ✅ 文档中对比 standalone 与 origin 镜像差异时提及 caffex

### 1.2 隔离性验证方法

构建前检查（源码层面）：
```bash
cd /path/to/vendor/caffe/docker/standalone
grep -rn "caffex" --include="*.sh" --include="*.py" --include="Dockerfile*" --include="*.conf" .
```

构建后检查（容器层面）：
```bash
docker exec <container> bash -c "find / -name '*caffex*' -type f 2>/dev/null | head -20"
```

## 2. 构建上下文约束

### 2.1 构建上下文路径

**Docker 构建上下文必须是 `vendor/` 目录**（即 caffe/ 的父目录），而非 standalone/ 或 pycaffe/ 目录。

原因：需要同时访问以下两个子模块：
- `caffe/caffe-slim/` — 推理引擎源码（C++、pycaffe、caffeproto）
- `tvm-ffi/` — TVM FFI 依赖

正确的构建命令：
```bash
cd /path/to/vendor    # 必须在 vendor/ 目录下
docker build -t caffe-cpu:standalone-pycaffe --target runtime \
  -f caffe/docker/standalone/pycaffe/Dockerfile .
```

错误的构建命令（会导致找不到源码）：
```bash
cd caffe/docker/standalone/pycaffe
docker build -t caffe-cpu:standalone-pycaffe .   # ❌ 错误：上下文不对
```

### 2.2 .dockerignore 约束

`../../../.dockerignore`（vendor/.dockerignore，从 standalone/ 向上3层）必须满足：
- ✅ 排除 `caffex/` 目录（不需要进入构建上下文）
- ❌ 不得排除 `tvm-ffi/3rdparty/libbacktrace/` 整个目录
- ✅ 仅排除 `tvm-ffi/3rdparty/libbacktrace/.git`（Git元数据不需要）

错误配置（曾导致构建失败）：
```
# ❌ 错误：排除了整个libbacktrace目录，CMake找不到源文件
tvm-ffi/3rdparty/libbacktrace/
```

正确配置：
```
# ✅ 正确：仅排除.git目录
tvm-ffi/3rdparty/libbacktrace/.git
```

## 3. 基础镜像与环境约束

### 3.1 基础镜像固定

- **必须使用** `ubuntu:26.04`（指定版本标签，禁止使用 `ubuntu:latest`）
- **原因**：确保构建可复现；26.04 提供 Python 3、较新的 gcc/cmake，且与 numpy 2.x 兼容

### 3.2 Python 环境

- **Python 版本**：使用 Ubuntu 26.04 系统 Python 3（不额外安装 Miniconda/venv）
- **包管理**：pip + `--break-system-packages` 标志（PEP 668 合规）
- **numpy 版本**：`numpy>=2`（禁止 pin 到 numpy<2）
- **protobuf**：设置 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`，避免 C++ 实现版本冲突

### 3.3 预装科学计算包

pycaffe 镜像必须预装的核心包：
- numpy, scipy, matplotlib, scikit-image, h5py, networkx, pandas
- pyyaml, pillow, six, Cython, protobuf, python-dateutil, python-gflags
- tabulate（accuracy.py 等工具依赖）

jupyter-ssh 镜像额外安装：
- notebook, jupyterlab, ipykernel, nbconvert, jupyter_server
- openssh-server, supervisor, tini

## 4. 多阶段构建约束

### 4.1 必须的构建阶段

两个 Dockerfile（pycaffe 和 pycaffe-jupyter-ssh）必须使用以下4阶段结构：

| 阶段 | 基础 | 职责 |
|------|------|------|
| `base-system` | `ubuntu:26.04` | apt换源（阿里云镜像）、CA证书、基础工具（curl/wget/git等） |
| `base-builder` | `base-system` | gcc/g++/cmake/ninja/protobuf-compiler/libopenblas-dev + Python科学计算包 |
| `caffe-builder` | `base-builder` | 复制caffe-slim/ + tvm-ffi/，scikit-build-core驱动CMake+Ninja编译，打包wheel |
| `runtime` | `base-builder` | 安装wheel、配置运行时环境、运行验证脚本、设置HEALTHCHECK |

pycaffe-jupyter-ssh 的 runtime 阶段额外：
- 安装 SSH/Jupyter/supervisord/tini
- 复制 config/ 和 scripts/
- 创建 builder 用户
- 配置 entrypoint.sh 和 healthcheck.sh

### 4.2 镜像优化规则

- 多阶段构建中，builder阶段的编译工具链不进入runtime镜像
- apt安装使用 `--no-install-recommends`，每个apt阶段后立即 `rm -rf /var/lib/apt/lists/*`
- pip安装使用 `--no-cache-dir`
- 相关RUN指令合并，减少镜像层数
- COPY使用 `--chown=builder:builder`（jupyter-ssh镜像中直接设置所有权）

## 5. 验证分级约束

### 5.1 PASS/WARN/SKIP 三级分类

verify-pycaffe.sh 输出分为三个级别：

| 级别 | 含义 | 是否阻断构建 |
|------|------|-------------|
| **PASS** | 核心功能正常，必须通过 | 是（出现FAIL则构建失败） |
| **WARN** | 辅助功能不可用，属于slim版本预期 | 否（仅记录警告） |
| **SKIP** | 可选依赖缺失，不影响核心推理 | 否（跳过即可） |

### 5.2 必须PASS的核心项

- `import pycaffe succeeded`
- `pycaffe.__version__ = 1.0.0-slim`
- `pycaffe.TRAIN = 0`, `pycaffe.TEST = 1`
- `pycaffe.Net class available`
- `pycaffe.set_mode_cpu() succeeded`
- `LeNet Net creation and forward pass succeeded`

### 5.3 预期WARN项（slim推理版本正常现象）

- `pycaffe.classifier/detector/io/draw/coord_map not available`
- `pycaffe.SGDSolver/AdamSolver/... not available`（训练类不可用）
- `pycaffe.draw` SKIP（pydotplus未安装，可视化依赖可选）

## 6. caffe-slim API 差异

standalone 镜像使用 caffe-slim（推理-only版本），与完整BVLC Caffe存在以下API差异：

| 差异 | caffe-slim 行为 | 完整BVLC Caffe行为 |
|------|----------------|-------------------|
| `net.forward()` 返回值 | 返回 `None`（推理已执行但不返回dict） | 返回输出blobs的dict |
| 获取输出数据 | 通过 `net.blobs['prob'].data` 访问 | forward()返回值或blobs均可 |
| Solver类 | 不可用（no training） | 可用（SGD/Adam等训练器） |
| 辅助子模块 | classifier/detector/draw/io不可用 | 全部可用 |
| 训练相关功能 | 不支持 | 支持（Solver/训练循环） |

验证脚本注意：检查 `net.forward()` 时，不抛异常即为成功，不要断言返回值类型。

## 7. 运行时配置约束

### 7.1 ENTRYPOINT 为空

Dockerfile 不得设置 ENTRYPOINT（或设为空数组 `[]`），以允许：
- `docker run ... bash` 进入交互shell
- `docker run ... python -c "..."` 直接执行Python命令
- `docker run ... verify-pycaffe.sh` 直接运行验证脚本

jupyter-ssh镜像通过 CMD 启动 supervisord，ENTRYPOINT 使用 tini 作为 PID 1：
```dockerfile
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/local/bin/entrypoint.sh"]
```

### 7.2 环境变量

关键环境变量必须在Dockerfile中设置：
```dockerfile
ENV LANG=zh_CN.UTF-8
ENV TZ=Asia/Shanghai
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

### 7.3 工作目录

- pycaffe镜像：`WORKDIR /workspace`
- jupyter-ssh镜像：`WORKDIR /workspace`，builder用户的home也在/workspace

## 8. 子模块依赖

构建前必须初始化两个git子模块：

```bash
cd /path/to/vendor
git submodule update --init --recursive
```

验证子模块完整性：
```bash
ls caffe/caffe-slim/CMakeLists.txt && echo "caffe-slim OK"
ls tvm-ffi/CMakeLists.txt && echo "tvm-ffi OK"
```

## 9. 健康检查约束

### 9.1 pycaffe 镜像

HEALTHCHECK 直接运行 verify-pycaffe.sh（或简化的import检查）。

### 9.2 pycaffe-jupyter-ssh 镜像

HEALTHCHECK 必须同时检测：
- SSH端口22是否可连接
- Jupyter HTTP端口8888是否响应（返回200/302/401/403均视为正常）

健康检查脚本：`pycaffe-jupyter-ssh/scripts/healthcheck.sh`

## 10. 禁止的修改模式

以下是已发现的反模式，禁止再次引入：

| 反模式 | 后果 | 正确做法 |
|--------|------|---------|
| Dockerfile中inline创建验证脚本 | 文件系统版本与镜像内版本不一致 | COPY scripts/目录下的文件 |
| .dockerignore排除libbacktrace整个目录 | CMake找不到tvm-ffi的源文件，构建失败 | 仅排除.git |
| numpy<2版本锁定 | 与Ubuntu 26.04系统Python不兼容 | 使用numpy>=2 |
| verify-parity.sh硬编码caffex路径 | 容器内找不到caffex，验证失败 | 改为占位脚本，说明不适用 |
| 验证脚本将Solver类标记为FAIL | slim版本无Solver，构建被错误阻断 | 训练相关标记为WARN |
| ENTRYPOINT设为python | `docker run ... bash` 执行python bash报错 | ENTRYPOINT为空或用tini |
| 验证脚本断言forward()返回dict | caffe-slim返回None，断言失败 | 不抛异常即为成功 |
