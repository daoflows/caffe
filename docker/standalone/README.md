# Caffe Standalone Docker

基于 ubuntu:26.04 的独立 PyCaffe Docker 镜像构建工作区，仅使用 `caffe-slim/` 推理引擎和 `tvm-ffi/` 依赖，从零编译构建，零 `caffex/` 依赖。

## 快速开始

```bash
# 1. 初始化子模块（首次构建前）
cd /path/to/vendor
git submodule update --init --recursive

# 2. 构建 pycaffe 基础镜像
docker build -t caffe-cpu:standalone-pycaffe --target runtime \
  -f caffe/docker/standalone/pycaffe/Dockerfile .

# 3. 快速验证
docker run --rm caffe-cpu:standalone-pycaffe \
  python -c "import pycaffe; print('pycaffe version:', pycaffe.__version__)"

# 4. 构建 Jupyter+SSH 镜像（可选）
docker build -t caffe-cpu:pycaffe-jupyter-ssh --target runtime \
  -f caffe/docker/standalone/pycaffe-jupyter-ssh/Dockerfile .
```

## 镜像清单

| 镜像 | Dockerfile | 包含服务 | 典型用途 | 预期大小 |
|------|-----------|---------|---------|---------|
| `caffe-cpu:standalone-pycaffe` | [pycaffe/Dockerfile](pycaffe/Dockerfile) | 无（纯推理运行时） | 批量推理、API服务基础镜像 | ~800MB-1.2GB |
| `caffe-cpu:pycaffe-jupyter-ssh` | [pycaffe-jupyter-ssh/Dockerfile](pycaffe-jupyter-ssh/Dockerfile) | Jupyter Notebook + SSH | 交互式开发、教学、调试 | ~1.2GB-1.8GB |

## 目录结构

```
standalone/
├── AGENTS.md                   # AI协作者入口
├── .agents/                    # Agent规范层
│   ├── README.md
│   ├── context-routing.md
│   └── build-constraints.md
├── README.md                   # 本文档
├── REGRESSION-TEST.md          # 回归测试流程文档
├── pycaffe/                    # 基础 PyCaffe 推理镜像
│   ├── Dockerfile              # 4阶段多阶段构建
│   ├── CMakeLists.txt
│   ├── README.md
│   └── scripts/
│       ├── verify-pycaffe.sh   # 核心验证脚本
│       └── verify-parity.sh    # 对标占位脚本
└── pycaffe-jupyter-ssh/        # Jupyter + SSH 扩展镜像
    ├── Dockerfile
    ├── README.md
    ├── QUICKSTART.md
    ├── build.sh
    ├── entrypoint.sh
    ├── run.sh
    ├── config/
    │   ├── supervisord.conf
    │   ├── sshd_config
    │   ├── jupyter_notebook_config.py
    │   └── supervisor/conf.d/
    └── scripts/
        └── healthcheck.sh
```

## 构建流水线

两个镜像共用相同的4阶段多阶段构建架构：

```
base-system → base-builder → caffe-builder → runtime
  (apt换源)    (工具链+Py)   (CMake+Ninja)   (wheel安装+验证)
```

| 阶段 | 职责 |
|------|------|
| `base-system` | 阿里云镜像源、CA证书、基础工具 |
| `base-builder` | gcc/cmake/ninja/protobuf/openblas + Python科学计算包（numpy>=2） |
| `caffe-builder` | 复制caffe-slim/ + tvm-ffi/，scikit-build-core驱动CMake+Ninja编译，打包wheel |
| `runtime` | 安装wheel，运行验证脚本，HEALTHCHECK |

## 验证

镜像构建完成后自动运行 `verify-pycaffe.sh`，验证结果分为三级：

- **PASS**：核心功能正常（必须全部通过）
- **WARN**：辅助功能不可用（slim推理版本预期行为，不阻断）
- **SKIP**：可选依赖缺失（不影响核心推理）

必须PASS的核心项：
- pycaffe导入成功
- 版本号为 `1.0.0-slim`
- TRAIN/TEST常量正确
- Net类可用
- CPU模式设置成功
- LeNet网络创建与前向传播成功

手动验证：
```bash
# 完整验证脚本
docker run --rm caffe-cpu:standalone-pycaffe verify-pycaffe.sh

# Python交互测试
docker run --rm -it caffe-cpu:standalone-pycaffe bash
python -c "
import pycaffe
pycaffe.set_mode_cpu()
net = pycaffe.Net('/workspace/pycaffe/lenet_deploy.prototxt', pycaffe.TEST)
net.forward()  # caffe-slim返回None但不抛异常即为成功
print('Forward pass OK')
"
```

## 运行 Jupyter+SSH 镜像

### 方式一：使用 run.sh 辅助脚本（推荐）

```bash
cd caffe/docker/standalone/pycaffe-jupyter-ssh
./run.sh                     # 自动检测端口、生成随机密码
./run.sh -p 2222 -j 8888     # 指定端口启动
./run.sh -w ~/notebooks      # 挂载本地工作目录
./run.sh -it bash            # 交互模式
```

`run.sh` 会自动处理端口冲突检测、随机密码/Token生成、卷挂载、容器清理等，启动后直接打印 SSH 和 Jupyter 访问信息。

### 方式二：手动 docker run

```bash
docker run -d \
  --name pycaffe-jupyter \
  --restart unless-stopped \
  --shm-size=1g \
  -p 2222:22 \
  -p 8888:8888 \
  -v $(pwd)/workspace:/workspace \
  -e USER_PASSWORD=your_password \
  -e JUPYTER_TOKEN=your_token \
  -e GRANT_SUDO=yes \
  caffe-cpu:pycaffe-jupyter-ssh
```

访问方式：
- Jupyter: http://localhost:8888/ （使用设置的Token登录）
- SSH: `ssh builder@localhost -p 2222`（使用设置的密码登录）

> **注意**：若未设置 `USER_PASSWORD` 或 `JUPYTER_TOKEN`，容器启动时会自动生成随机密码/Token，通过 `docker logs pycaffe-jupyter` 查看。

详细环境变量和配置选项见 [pycaffe-jupyter-ssh/README.md](pycaffe-jupyter-ssh/README.md)。

## 回归测试

完整的回归测试流程见 [REGRESSION-TEST.md](REGRESSION-TEST.md)，涵盖5个阶段：

1. **源码与配置检查**（T1）：隔离性验证，无caffex引用
2. **编译构建测试**（T2）：两个镜像均可从零构建
3. **运行时功能测试**（T3）：PyCaffe核心推理功能正常
4. **隔离性验证**（T4）：容器内零caffex文件和引用
5. **Jupyter+SSH扩展测试**（T5）：双服务正常运行

一键回归：
```bash
cd /path/to/vendor
bash caffe/docker/standalone/regression-test.sh
```

## 核心约束

1. **零caffex依赖**：不引用caffex/下的任何代码、资源或配置
2. **构建上下文为vendor/**：需同时访问caffe-slim/和tvm-ffi/
3. **ubuntu:26.04**：固定基础镜像版本，不用latest
4. **numpy>=2**：使用numpy 2.x系列
5. **scikit-build-core + CMake + Ninja**：wheel编译系统
6. **caffe-slim API差异**：`net.forward()`返回None，输出通过blobs访问

详细构建约束见 [.agents/build-constraints.md](.agents/build-constraints.md)。

## 与其他镜像的关系

| 镜像 | 位置 | 与standalone的区别 |
|------|------|-------------------|
| `origin/` | [docker/origin/](../origin/) | 基于完整BVLC Caffe（含caffex），支持训练 |
| `local/conda/` | [docker/local/conda/](../local/conda/) | 基于Conda环境，含Python 3.14等自定义环境 |
| `modules/pycaffe/` | [docker/modules/pycaffe/](../modules/pycaffe/) | 模块化构建，依赖caffex |
| **standalone/** | **本目录** | 基于caffe-slim，零caffex依赖，推理-only |

## AI协作者说明

AI智能体在本目录工作时，必须首先读取 [AGENTS.md](AGENTS.md) 遵循启动协议，再按 [.agents/context-routing.md](.agents/context-routing.md) 加载对应规范文件。核心构建约束见 [.agents/build-constraints.md](.agents/build-constraints.md)。
