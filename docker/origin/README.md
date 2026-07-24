# Caffe Origin CPU Docker 镜像

本仓库提供 BVLC Caffe 的 CPU-only Docker 镜像构建方案，基于 Ubuntu 22.04 + Python 3.10 + Make 构建系统。该镜像专门用于构建 `caffex/python` 原始模块，**不走 scikit-build-core / pycaffe 迁移路径**，旨在提供一个简化、贴近 Caffe 原始构建方式的基线环境，便于学习、调试与对比验证。

## 快速开始

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

## 构建

`build.sh` 封装了 `docker build` 调用，支持以下用法：

- `./build.sh` — 默认构建 runtime 阶段，标签 `caffe-cpu:latest`
- `./build.sh -t v1.0` — 指定标签
- `./build.sh --target builder-dev` — 构建指定阶段（可选：`base-system`、`base-builder`、`builder`、`runtime`）
- `./build.sh --no-cache` — 无缓存构建
- `./build.sh --build-arg BUILDER_UID=1001` — 传递构建参数
- `./build.sh -h` — 显示帮助

### 构建耗时

- 首次构建：15-40 分钟（取决于网络带宽与 CPU 核数）
- 后续构建：利用 Docker 层缓存可大幅缩短

### 构建产物

- 镜像 `caffe-cpu:latest`
- 镜像大小约 2-3 GB

## 运行

`run.sh` 封装了 `docker run` 调用，支持以下用法：

- `./run.sh` — 默认启动交互式 bash
- `./run.sh -n my-build` — 指定容器名
- `./run.sh -- ls -la` — 执行命令后自动删除容器
- `./run.sh -- python3 -c "import caffe; print(caffe.__version__)"` — 一次性命令
- `./run.sh --non-interactive -- python3 test.py` — 非交互式（适用于 CI/测试场景）
- `./run.sh -h` — 显示帮助

### 容器内默认环境

- 工作目录：`/workspace/caffex`
- 挂载点：项目根目录 → `/workspace`
- 用户：`builder`（UID 1000，sudo NOPASSWD）

## 环境变量

容器内的关键环境变量：

| 环境变量 | 值 | 说明 |
|---------|-----|------|
| `CAFFE_ROOT` | `/workspace/caffex` | Caffe 源码与编译产物根目录 |
| `PYTHONPATH` | `/workspace/caffex/python` | PyCaffe 模块搜索路径 |
| `LD_LIBRARY_PATH` | `/workspace/caffex/build/lib:/usr/lib/x86_64-linux-gnu` | 动态库搜索路径 |
| `PIP_INDEX_URL` | `https://mirrors.aliyun.com/pypi/simple` | pip 镜像源（构建期） |
| `DEBIAN_FRONTEND` | `noninteractive` | apt 非交互模式 |
| `LANG` / `LC_ALL` | `C.UTF-8` | 字符编码 |

## 与 conda 版本的差异

与 `docker/local/conda/Dockerfile` 的对比：

| 维度 | docker/origin | docker/local/conda |
|------|---------------|-------------------|
| 构建阶段数 | 4（base-system, base-builder, builder, runtime） | 5（含 pycaffe-builder） |
| Python 模块路径 | `caffex/python`（原始） | `caffex/python` + `pycaffe/`（迁移） |
| 构建系统 | 仅 Make | Make + scikit-build-core |
| 是否构建 wheel | 否 | 是（pycaffe wheel） |
| 脚本依赖 | 自包含（不依赖 docker/local/lib/） | 依赖 docker/local/lib/log.sh 与 check_env.sh |
| 适用场景 | 简化基线、不依赖现代打包工具链 | 完整方案、wheel 可 pip 安装 |

### 何时选择 docker/origin

- 不需要 pycaffe wheel 打包
- 希望保持 Caffe 原始构建方式
- 想要更简单的 Dockerfile 结构便于学习与调试
- 不希望引入 scikit-build-core 依赖

### 何时选择 docker/local/conda

- 需要 `pip install` 安装 pycaffe
- 希望使用现代 Python 打包工具链
- 需要完整的开发与发布流程

## 常见问题

### Q1: 构建失败提示 `boost_python310` 找不到

**原因**：系统未安装 `libboost-all-dev` 或 Boost.Python 库名称不匹配。

**解决**：

- 确认 `base-builder` 阶段已安装 `libboost-all-dev`
- 检查 `Makefile.config` 中 `PYTHON_LIBRARIES` 的值
- 在容器内执行 `ldconfig -p | grep boost_python` 查看可用的 Boost.Python 库
- 若库名称不同，修改 `scripts/generate-makefile-config.sh` 中的回退逻辑

### Q2: protobuf 版本冲突

**原因**：Caffe 使用 protobuf 3.x，新版 protobuf 4.x 不兼容。

**解决**：

- 确认 `base-builder` 阶段固定 `protobuf==3.20.3`
- 若已安装 protobuf 4.x，卸载后重新安装 3.20.3：`pip uninstall protobuf && pip install protobuf==3.20.3`

### Q3: HDF5 头文件找不到

**原因**：Ubuntu 22.04 的 HDF5 头文件位于 `/usr/include/hdf5/serial`，不在默认搜索路径。

**解决**：

- 确认 `Makefile.config` 中 `INCLUDE_DIRS` 包含 `/usr/include/hdf5/serial`
- 确认 `LIBRARY_DIRS` 包含 `/usr/lib/x86_64-linux-gnu/hdf5/serial`
- `generate-makefile-config.sh` 会自动检测并添加这些路径

### Q4: 镜像体积过大

**原因**：`base-builder` 阶段保留了所有编译工具链。

**优化建议**：

- 当前 `runtime` 阶段复用 `base-builder`（便于调试），如需更小镜像可改为基于 `ubuntu:22.04` 仅安装运行时依赖
- 清理 apt 缓存：`rm -rf /var/lib/apt/lists/*`（已包含）
- 清理 pip 缓存：`pip cache purge`（已通过 `PIP_NO_CACHE_DIR=1` 实现）

### Q5: Python 3.10 兼容性

**说明**：Caffe 1.0 原生支持 Python 3，在 Python 3.10 下编译需注意：

- `Cython >= 0.29` 兼容 Python 3.10
- `numpy < 2.0` 避免 ABI 不兼容
- `protobuf == 3.20.3` 兼容 Caffe proto 定义
- C++ 代码使用 `-std=c++14` 编译（在 `Makefile.config` 中配置）

### Q6: WSL2 中构建中断或卡住

**解决**：

- 检查 Docker Desktop 内存限制（建议 ≥ 8GB）
- 检查磁盘空间（建议 ≥ 10GB 可用）
- 查看详细构建日志：`./build.sh --no-cache` 或在 `docker build` 命令中添加 `--progress=plain`
- 向上滚动找到第一个 `error:` 行定位问题

### Q7: 挂载目录权限问题

**原因**：容器内 `builder` 用户 UID 1000 与宿主机用户 UID 不匹配。

**解决**：

- 构建时指定 UID：`./build.sh --build-arg BUILDER_UID=$(id -u) --build-arg BUILDER_GID=$(id -g)`
- 或在容器内通过 sudo 修改文件权限：`sudo chown -R builder:builder /workspace`

## 相关文档

- 参考模板：[../local/conda/Dockerfile](../local/conda/Dockerfile)
- 构建脚本说明：[build.sh](build.sh)（`./build.sh -h` 查看完整选项）
- 运行脚本说明：[run.sh](run.sh)（`./run.sh -h` 查看完整选项）
- Makefile.config 生成：[scripts/generate-makefile-config.sh](scripts/generate-makefile-config.sh)
- 验证脚本：[scripts/verify-caffe.sh](scripts/verify-caffe.sh)
- Caffe 源码：[../../caffex/](../../caffex/)（只读，不修改）
