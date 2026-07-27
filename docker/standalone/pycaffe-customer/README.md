# PyCaffe 客户分发镜像 - 用户指南

## 概述

这是一个面向生产环境的自包含 Docker 镜像，提供基于 tvm-ffi 后端的 PyCaffe（Caffe 纯 CPU 推理）。镜像包含：

- **Caffe-slim**（纯 CPU 推理构建），附带 **tvm-ffi** Python 绑定
- **Jupyter Notebook**（端口 8888）用于交互式开发
- **SSH 服务器**（端口 22）用于远程访问
- **ResNet-50** 演示模型及推理脚本
- **自验证命令**（`caffe-verify`）用于快速健康检查
- 非 root 用户（`builder`，UID 1000）保障安全运行
- 多阶段构建，镜像体积精简（约 2-2.5 GB）

> **默认凭据（生产环境请务必修改）：**
> - SSH：用户名 `builder`，密码 `caffepass`
> - Jupyter：Token `caffe-token`

---

## 快速开始（面向客户）

### 1. 加载镜像

```bash
# 从 tar 文件加载
docker load -i caffe-cpu-customer-<version>-<date>.tar

# （可选）使用 SHA256 校验和验证完整性
sha256sum -c caffe-cpu-customer-<version>-<date>.tar.gz.sha256
```

### 2. 运行容器

```bash
# 基础运行（Jupyter 8888，SSH 2222）
docker run -d \
  -p 8888:8888 \
  -p 2222:22 \
  --name caffe \
  caffe-cpu:customer

# 使用自定义凭据（推荐生产环境使用）
docker run -d \
  -p 8888:8888 \
  -p 2222:22 \
  --name caffe \
  -e USER_PASSWORD=your_secure_password \
  -e JUPYTER_TOKEN=your_secure_token \
  caffe-cpu:customer

# 禁用 SSH（仅使用 Jupyter）
docker run -d \
  -p 8888:8888 \
  -e DISABLE_SSH=yes \
  --name caffe \
  caffe-cpu:customer

# 挂载本地工作目录
docker run -d \
  -p 8888:8888 \
  -p 2222:22 \
  -v /your/local/workspace:/workspace/user-data \
  --name caffe \
  caffe-cpu:customer
```

### 3. 访问服务

等待 15-30 秒让服务启动，然后：

- **Jupyter Notebook**：在浏览器中打开 http://localhost:8888/
  - 输入 Token：`caffe-token`（或您自定义的 `JUPYTER_TOKEN`）
- **SSH**：`ssh builder@localhost -p 2222`
  - 密码：`caffepass`（或您自定义的 `USER_PASSWORD`）

### 4. 验证安装

```bash
# 运行内置验证脚本
docker exec caffe caffe-verify
```

预期输出显示所有检查通过（7/7）：

```
[PASS] pycaffe import successful
[PASS] pycaffe version: 1.0.0-slim
[PASS] pycaffe.Net class is available
[PASS] LeNet forward pass successful
[PASS] Jupyter is responding on port 8888
[PASS] SSH is listening on port 22
[PASS] ResNet50 inference completed successfully
```

### 5. 查看容器日志

```bash
# 查看启动消息和凭据
docker logs caffe

# 实时跟踪日志
docker logs -f caffe
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `USER_PASSWORD` | `caffepass` | `builder` 用户的 SSH 密码 |
| `JUPYTER_TOKEN` | `caffe-token` | Jupyter Notebook 认证 Token |
| `JUPYTER_PORT` | `8888` | Jupyter 内部端口（通常无需修改） |
| `SSH_PORT` | `22` | SSH 内部端口（通常无需修改） |
| `DISABLE_SSH` | `no` | 设置为 `yes`/`1`/`true` 以禁用 SSH 服务器 |
| `GRANT_SUDO` | `no` | 设置为 `yes` 以授予 builder 用户 sudo 权限 |
| `JUPYTER_PASSWORD` | （未设置） | 设置 Jupyter 密码替代 Token 认证 |
| `JUPYTER_ALLOW_ORIGIN` | `*` | Jupyter CORS 允许的源 |

---

## 使用 PyCaffe

### Python API

```python
import caffe
import numpy as np

# 设置 CPU 模式
caffe.set_mode_cpu()

# 加载模型
net = caffe.Net('model/deploy.prototxt', 'model/weights.caffemodel', caffe.TEST)

# 准备输入（根据需要 reshape 并加载数据）
net.blobs['data'].reshape(1, 3, 224, 224)
# net.blobs['data'].data[...] = your_preprocessed_image

# 运行推理
output = net.forward()

# 获取结果
predictions = output['prob'][0]
```

### 运行 ResNet-50 演示

在容器内或通过 `docker exec` 运行：

```bash
# 运行内置 ResNet-50 分类演示
python /opt/caffe-examples/infer.py

# 使用自定义图片
python /opt/caffe-examples/infer.py --image /path/to/your/image.jpg

# 使用自定义模型
python /opt/caffe-examples/infer.py \
  --prototxt /path/to/deploy.prototxt \
  --caffemodel /path/to/model.caffemodel \
  --image /path/to/image.jpg \
  --topk 5
```

### 使用 Jupyter Notebook

1. 打开 http://localhost:8888/
2. 导航到 `examples/` 文件夹（指向 `/opt/caffe-examples/` 的符号链接）
3. 打开并运行示例 Notebook
4. 通过 Jupyter UI 上传您自己的 Notebook

---

## 容器管理

```bash
# 停止容器
docker stop caffe

# 启动已停止的容器
docker start caffe

# 删除容器（挂载卷中的数据会保留）
docker rm -f caffe

# 在运行中的容器内打开 shell
docker exec -it caffe bash

# 以 root 身份打开 shell（用于维护）
docker exec -it -u root caffe bash
```

---

## 构建镜像（面向分发者）

### 前置条件

- Docker 20.10+，启用 BuildKit
- Git 子模块已初始化：`git submodule update --init --recursive`

### 构建命令

```bash
# 进入 pycaffe-customer 目录
cd vendor/caffe/docker/standalone/pycaffe-customer

# 标准构建（使用官方源，国际网络环境）
./build.sh

# 使用国内镜像构建（面向中国大陆用户，使用阿里云镜像）
./build.sh --china

# 使用自定义标签构建
./build.sh -t v1.0.0

# 干净重建（不使用缓存，用于排查构建问题）
./build.sh --no-cache

# 传递额外构建参数
./build.sh --build-arg "IMAGE_VERSION=1.0.0"
```

**构建过程预期时间**：15-30分钟（取决于网络速度和CPU性能），主要耗时在：
1. apt 包安装（~3-5分钟）
2. pip Python 包安装（~5-8分钟）
3. tvm-ffi 编译（~2-3分钟）
4. caffe-slim 编译（~5-10分钟）
5. 最终配置和验证（~1分钟）

**构建成功标志**：构建日志末尾显示 `Final verification passed` 和 `Successfully tagged caffe-cpu:customer`。

**构建验证**：构建完成后，运行以下命令验证镜像：
```bash
# 查看镜像
docker images caffe-cpu:customer

# 检查镜像大小（预期 1.5-2.5 GB）
docker image inspect caffe-cpu:customer --format '{{.Size}}' | numfmt --to=iec

# 快速启动测试
docker run --rm --name caffe-test caffe-cpu:customer echo "Container started OK"

# 完整功能验证（启动容器并运行自检）
docker run -d -p 18888:8888 -p 12222:22 --name caffe-verify-test caffe-cpu:customer
sleep 20  # 等待服务启动
docker exec caffe-verify-test caffe-verify
docker rm -f caffe-verify-test
```

### 导出分发

```bash
# 导出为 tar 文件
./export.sh

# 使用 gzip 压缩导出（体积更小，推荐用于分发）
./export.sh -z

# 使用自定义版本标签和输出目录导出
./export.sh -t v1.0.0 -o ./dist/ --version 1.0.0

# 跳过校验和生成（不推荐）
./export.sh --no-checksum
```

导出脚本会自动：
1. 验证镜像存在并可用
2. 使用 `docker save` 将镜像导出为 tar
3. 如果使用 `-z`，用 gzip 压缩（可减少约 40-50% 体积）
4. 生成 SHA256 校验和文件
5. 打印文件大小和校验信息
6. 输出客户侧加载命令

导出脚本生成：
- `caffe-cpu-customer-<version>-<date>.tar`（使用 `-z` 时为 `.tar.gz`）
- `caffe-cpu-customer-<version>-<date>.tar.sha256`（SHA256 校验和）

**验证导出文件**：
```bash
# 检查文件大小（tar 格式预期 1.5-2.5 GB，tar.gz 预期 1-1.5 GB）
ls -lh dist/caffe-cpu-customer-*.tar*

# 验证校验和
cd dist && sha256sum -c caffe-cpu-customer-*.sha256

# 测试导入（在另一台机器上或当前机器上）
docker load -i dist/caffe-cpu-customer-<version>-<date>.tar
docker images | grep caffe-cpu
```

---

## 镜像架构

### 多阶段构建

| 阶段 | 用途 | 内容 |
|---|---|---|
| `base-system` | 最小化 Ubuntu 26.04 基础 | CA 证书、基础工具、安全补丁 |
| `base-builder` | 构建工具链 | gcc、cmake、ninja、Python 开发包、pip 依赖 |
| `caffe-builder` | 编译 Caffe 和 tvm-ffi | tvm-ffi 编译、caffe-slim 构建、产物收集 |
| `customer-runtime` | 最终运行时镜像 | 仅运行时库、Python 包、Jupyter、SSH、示例 |

最终阶段（`customer-runtime`）**不包含任何构建工具**（无 gcc、cmake、ninja、git、make），以最小化镜像体积和攻击面。

### 安全特性

- **非 root 用户**：容器以 `builder`（UID 1000）身份运行，而非 root
- **gosu**：服务启动时的权限降级
- **SSH 加固**：禁用 root 登录，仅允许非 root 用户密码认证
- **全新 SSH 密钥**：每次容器启动时重新生成主机密钥
- **安全补丁**：构建时应用 `apt-get upgrade`
- **无构建工具**：编译器工具链已从最终镜像中完全移除
- **tini init**：正确的 PID 1 信号处理和僵尸进程回收

### 容器内目录结构

| 路径 | 用途 |
|---|---|
| `/workspace/` | 工作目录（用户数据挂载点） |
| `/workspace/examples/` | 指向 `/opt/caffe-examples/` 的符号链接 |
| `/opt/caffe-examples/` | 演示模型和脚本（ResNet-50、infer.py） |
| `/home/builder/` | builder 用户的主目录 |
| `/usr/local/bin/` | 入口点脚本（`entrypoint.sh`、`caffe-verify`、`healthcheck.sh`） |
| `/etc/caffe-customer-release` | 构建元数据（版本、日期、组件） |

---

## 故障排查

遇到问题时，请先参考独立的故障排查文档：[TROUBLESHOOTING.md](TROUBLESHOOTING.md)，其中包含以下场景的详细诊断步骤：

- [镜像加载问题](TROUBLESHOOTING.md#1-镜像加载问题)（损坏、格式错误、架构不匹配）
- [容器启动问题](TROUBLESHOOTING.md#2-容器启动问题)（退出码、健康检查失败、权限错误）
- [Jupyter Notebook 访问问题](TROUBLESHOOTING.md#3-jupyter-notebook-访问问题)（连接失败、Token错误、内核问题）
- [SSH 访问问题](TROUBLESHOOTING.md#4-ssh-访问问题)（连接被拒绝、密码错误、PTY错误）
- [PyCaffe 导入和运行问题](TROUBLESHOOTING.md#5-pycaffecaffe-导入和运行问题)（库缺失、架构错误、Protobuf版本）
- [模型推理问题](TROUBLESHOOTING.md#6-模型推理问题)（ResNet50失败、自定义模型加载错误）
- [性能、网络、存储等问题](TROUBLESHOOTING.md#7-性能问题)

### 快速诊断

```bash
# 第一步：运行容器内自验证
docker exec caffe caffe-verify

# 第二步：查看容器日志
docker logs caffe

# 第三步：查看镜像信息
docker exec caffe cat /etc/caffe-customer-release
```

---

## 系统要求

| 资源 | 最低配置 | 推荐配置 |
|---|---|---|
| Docker | 20.10+ | 24.0+ |
| 内存 | 2 GB | 4 GB+ |
| 磁盘 | 4 GB（镜像） | 8 GB+ |
| CPU | 任何支持 SSE4.2 的 x86_64 | 多核以获得更快推理速度 |

---

## 技术规格

| 组件 | 版本 |
|---|---|
| 基础镜像 | Ubuntu 26.04 |
| Caffe | 1.0.0-slim（纯 CPU） |
| tvm-ffi | 0.1.0 |
| Python | 3.12（系统 Python 3） |
| Jupyter Notebook | 7.2.2 |
| JupyterLab | 4.2.5 |
| NumPy | 2.x |
| Protocol Buffers | Python 实现（无 C++ 扩展） |
| 默认区域设置 | C.UTF-8 |
| 默认时区 | UTC |

---

## 支持与维护

- **镜像版本**：参见容器内 `/etc/caffe-customer-release`
- **维护者**：Caffe Standalone Docker 维护团队
- **源代码**：https://github.com/xinetzone/SpecWeave
- **许可证**：BSD-2-Clause（Caffe），所有依赖许可证位于 `/usr/share/doc/`

### 检查镜像版本

```bash
docker exec caffe cat /etc/caffe-customer-release
```

### 更新

当新版本发布时，只需：
1. 停止并删除旧容器：`docker rm -f caffe`
2. 加载新镜像：`docker load -i caffe-cpu-customer-<new-version>.tar`
3. 使用您常用的 `docker run` 命令启动新容器

---

*最后更新：2026-03-26*
