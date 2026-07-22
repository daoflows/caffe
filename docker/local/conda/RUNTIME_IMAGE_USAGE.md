# Caffe CPU Docker 使用指南

本目录收敛为一套统一入口：

- `Dockerfile`: 统一多阶段 Dockerfile，覆盖开发镜像与运行时镜像
- `build.sh`: 构建开发镜像，默认目标为 `builder-dev`
- `run.sh`: 启动开发容器并挂载项目源码
- `build/`: runtime 镜像构建与导出脚本
- `scripts/`: Dockerfile 和构建脚本依赖的辅助验证脚本
- `config/`: pip 镜像源配置

## 目录结构

```text
docker/local/conda/
├── Dockerfile
├── RUNTIME_IMAGE_USAGE.md
├── build.sh
├── run.sh
├── build/
│   ├── build-multistage.sh
│   └── export-image.sh
├── config/
│   ├── condarc
│   └── pip.conf
└── scripts/
    ├── generate-makefile-config.sh
    └── verify-caffe.sh
```

## Dockerfile 目标

当前仅保留一个 `Dockerfile`，通过 `--target` 区分不同镜像阶段：

| 目标阶段 | 说明 | 常见入口 |
| --- | --- | --- |
| `base-system` | 公共基础层（Ubuntu 22.04 + apt 换源） | 通常由其他阶段复用 |
| `base-builder` | 基础构建环境（系统构建依赖 + Python 3.10 依赖） | 通常由其他阶段复用 |
| `builder-dev` | 开发构建环境（含源码挂载支持） | `./build.sh` |
| `builder` | CI 构建阶段（编译 Caffe 源码） | `./build/build-multistage.sh --target builder` |
| `runtime` | 完整运行时镜像（从 builder 获取编译产物） | `./build/build-multistage.sh --target runtime` |

## 快速开始

以下命令默认在项目根目录执行。

### 构建开发镜像

```bash
cd docker/local/conda
./build.sh
```

默认会生成 `caffe-cpu:latest`，目标阶段为 `builder-dev`。

### 启动开发容器

```bash
cd docker/local/conda
./run.sh
```

交互式 bash 默认接入 Caffe 源码环境，可直接 `import caffe`。

常用选项：

```bash
./run.sh -n my-build               # 指定容器名启动
./run.sh -- python3 -c "import caffe; print(caffe.__version__)"
./run.sh -- ls -la
```

### 一键构建 runtime 镜像

```bash
cd docker/local/conda
./build/build-multistage.sh --target runtime --verify
```

默认镜像标签：`caffe-cpu:runtime`

常用示例：

```bash
./build/build-multistage.sh
./build/build-multistage.sh -t v1.0
./build/build-multistage.sh --no-cache
./build/build-multistage.sh --verify --export --compress
```

`--verify` 会在 runtime 构建完成后执行 `verify-caffe.sh` 验证。

### 导出 runtime 镜像

```bash
cd docker/local/conda
./build/export-image.sh
./build/export-image.sh --compress
./build/export-image.sh --output /tmp/caffe-cpu-runtime.tar.gz --compress
```

## 验证

### 验证开发镜像可构建

```bash
cd docker/local/conda
./build.sh
```

### 验证 runtime 镜像功能

```bash
docker run --rm caffe-cpu:runtime verify-caffe.sh
```

或交互式验证：

```bash
docker run --rm -it caffe-cpu:runtime bash
python3 -c "import caffe; print('Caffe version:', caffe.__version__)"
```

## 常见路径约定

- 开发镜像入口脚本保留在 `docker/local/conda/` 顶层
- runtime 构建脚本集中到 `docker/local/conda/build/`
- Dockerfile 依赖的内部辅助脚本集中到 `docker/local/conda/scripts/`
- 共享 Shell 函数库位于 `docker/local/lib/`

如果需要从项目根目录直接执行 docker 命令：

```bash
docker build -t caffe-cpu:latest \
  --target builder-dev \
  -f docker/local/conda/Dockerfile .

docker build -t caffe-cpu:runtime \
  --target runtime \
  -f docker/local/conda/Dockerfile .
```

## 环境说明

本镜像使用 **Ubuntu 22.04 + System Python 3.10**（非 conda 环境），原因：

1. Caffe 1.0 原生支持 Python 3.x，无需 conda 额外开销
2. System Python 3.10 在 Ubuntu 22.04 中预装且稳定
3. 所有 Python 依赖通过 pip + 阿里云镜像安装，速度快且可靠

镜像内关键环境变量：

| 变量 | 值 |
| --- | --- |
| `CAFFE_ROOT` | `/workspace/caffex` |
| `PYTHONPATH` | `/workspace/caffex/python` |
| `LD_LIBRARY_PATH` | `/workspace/caffex/build/lib:/usr/lib:/usr/lib/x86_64-linux-gnu:/usr/local/lib` |

## 故障排查

### 构建失败: 网络问题

- 已默认使用阿里云 apt / pip 镜像
- 可优先重试，Docker 会尽量复用缓存

### 构建失败: 内存不足

- Docker Desktop 建议至少分配 8 GB 内存，推荐 16 GB+

### 运行时验证失败

- 优先执行 `./build/build-multistage.sh --verify`
- 如需单独排查，可手动运行容器内 `verify-caffe.sh`

### 开发容器里 `import caffe` 失败

- 确认使用了 `./run.sh` 启动（自动挂载源码并设置环境变量）
- 若使用 `docker run` 手动启动，需显式设置 `CAFFE_ROOT`、`PYTHONPATH`、`LD_LIBRARY_PATH`

### Boost.Python 库找不到

- `generate-makefile-config.sh` 自动检测多种 Boost.Python 命名方式
- 如仍失败，检查容器内 `ldconfig -p | grep boost_python` 输出

## 编译兼容性

Caffe 1.0（2017）在 Ubuntu 22.04 + Python 3.10 环境下编译存在多个兼容性问题。已萃取的编译兼容性预检清单覆盖了 6 项常见问题，可在编写 Dockerfile 之前预判风险：

- BLAS 库选择（libatlas → openblas）
- Python 版本兼容性（setuptools 废弃函数）
- OpenCV 版本（头文件路径 + imgcodecs 链接）
- protobuf 版本
- Boost 版本（库命名差异）
- C++ 标准（C++11 → C++14）

完整清单见：[老旧 C++ 项目编译兼容性预检清单](https://github.com/xinetzone/SpecWeave/blob/main/.agents/docs/retrospective/patterns/process-patterns/legacy-cpp-compilation-compatibility-checklist.md)

## 推荐使用方式

- 日常开发: `./build.sh` + `./run.sh`
- CI / 发布构建: `./build/build-multistage.sh --target runtime`
- 镜像分发: `./build/export-image.sh`