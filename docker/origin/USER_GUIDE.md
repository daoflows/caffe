# Caffe CPU Docker 镜像用户指南

本文档面向最终用户，介绍如何使用预编译的 BVLC Caffe CPU 版 Docker 镜像。

---

## 1. 概述

### 这是什么？

这是一个**预编译的 BVLC Caffe CPU 版 Docker 镜像**，开箱即用，无需手动编译 Caffe 或安装复杂的依赖环境。

### 包含什么？

镜像基于 Ubuntu 22.04 操作系统，预装了以下软件：

- **Python 3.10**（系统自带）
- **Caffe 1.0**（深度学习框架，CPU 版本）
- **常用 Python 科学计算包**：numpy、scipy、matplotlib、scikit-image、h5py、pandas、protobuf 等
- **Caffe 命令行工具**：caffe、convert_imageset、compute_image_mean 等

### 两个镜像版本

| 镜像版本 | 名称标签 | 适用场景 |
|---------|---------|---------|
| **origin-runtime** | `caffe-cpu:origin-runtime` | 命令行运行时，适合批处理、脚本执行、自动化任务 |
| **origin-jupyter** | `caffe-cpu:origin-jupyter` | Jupyter Notebook + SSH 交互式开发环境，适合学习、调试、远程开发 |

### 环境要求

使用本镜像**只需要安装 Docker**，不需要其他任何依赖：

- **Windows/Mac**：安装 Docker Desktop
- **Linux**：安装 Docker Engine

> 💡 本镜像不包含 GPU 支持，仅使用 CPU 运行。

---

## 2. 分发包内容

当您获取到分发的压缩包（tar 文件）后，解压会看到以下文件：

| 文件 | 说明 |
|-----|------|
| `caffe-cpu-origin-runtime_YYYYMMDD.tar` | Runtime 版本 Docker 镜像文件 |
| `caffe-cpu-origin-jupyter_YYYYMMDD.tar` | Jupyter 版本 Docker 镜像文件 |
| `run-standalone.sh` | 一键启动脚本（推荐使用） |
| `load-and-verify.sh` | 镜像加载与验证脚本 |
| `USER_GUIDE.md` | 本文档 |

---

## 3. 快速开始

只需 3 步即可开始使用：

### 步骤 1：加载镜像

**方式一（推荐）：使用脚本自动加载**

```bash
./load-and-verify.sh
```

脚本会自动加载两个镜像并验证 Caffe 安装是否正常。

**方式二：手动加载**

如果只想加载某个版本：

```bash
# 加载 Runtime 版本
docker load -i caffe-cpu-origin-runtime_YYYYMMDD.tar

# 加载 Jupyter 版本
docker load -i caffe-cpu-origin-jupyter_YYYYMMDD.tar
```

> ⏱️ 加载过程需要几分钟，请耐心等待。加载成功后会显示镜像名称和标签。

### 步骤 2：验证环境

镜像加载后，运行验证脚本确认一切正常：

```bash
docker run --rm caffe-cpu:origin-runtime verify-caffe.sh
```

**预期结果**：看到绿色的 `ALL CHECKS PASSED` 提示，表示 Caffe 安装成功。

验证脚本会自动检查：
- Python 环境是否正常
- numpy、scipy、protobuf 等依赖包是否安装
- Caffe 动态库是否存在
- `import caffe` 是否成功
- Caffe 基本功能（Blob 创建、数据读写）是否正常

### 步骤 3：启动容器

根据您的需求选择启动方式：

**启动 Runtime 命令行环境：**

```bash
./run-standalone.sh runtime
```

**启动 Jupyter Notebook 环境：**

```bash
./run-standalone.sh jupyter
```

---

## 4. 详细使用说明

### 4.1 Runtime 镜像使用

Runtime 镜像提供命令行环境，适合运行脚本、批处理任务。

#### 进入交互式命令行

```bash
./run-standalone.sh runtime
```

启动后您会看到容器内的命令提示符，此时可以直接输入 Linux 命令或 Python 命令。

**验证 Caffe 是否可用：**

```bash
python3 -c "import caffe; print('Caffe 版本:', caffe.__version__)"
```

**退出容器：**

```bash
exit
```

#### 执行一次性命令

不需要进入交互环境，直接在容器内运行命令：

```bash
# 查看 Caffe 版本
./run-standalone.sh runtime -- python3 -c "import caffe; print(caffe.__version__)"

# 运行 Python 脚本
./run-standalone.sh runtime -- python3 your_script.py

# 查看容器内文件
./run-standalone.sh runtime -- ls -la /workspace/caffex/
```

#### 验证 Caffe 安装

容器内提供了验证脚本，可以随时运行：

```bash
./run-standalone.sh runtime -- verify-caffe.sh
```

#### 关于数据持久化

容器内的文件默认是**临时的**，容器删除后文件会丢失。如果需要保存您的工作文件，请使用 Docker 数据卷（Volume）挂载。

**挂载本地目录到容器：**

```bash
# Linux/Mac 示例：将当前目录挂载到容器的 /workspace/myproject
docker run -it --rm \
  -v $(pwd):/workspace/myproject \
  caffe-cpu:origin-runtime bash

# Windows (PowerShell) 示例：
docker run -it --rm \
  -v ${PWD}:/workspace/myproject \
  caffe-cpu:origin-runtime bash
```

这样您在容器内 `/workspace/myproject` 目录下创建的文件会直接保存到您的本地目录。

---

### 4.2 Jupyter 镜像使用

Jupyter 镜像提供浏览器交互式 Notebook 环境，并支持 SSH 远程连接。

#### 启动 Jupyter

```bash
./run-standalone.sh jupyter
```

启动后会显示访问信息，包括：
- Jupyter 访问地址
- Jupyter Token（访问密码）
- SSH 连接地址和密码

#### 配置环境变量（可选）

启动前可以设置以下环境变量来自定义配置：

| 环境变量 | 作用 | 默认值 |
|---------|------|-------|
| `USER_PASSWORD` | SSH 登录密码 | `pass` |
| `JUPYTER_TOKEN` | Jupyter 访问 Token | `mysecret` |
| `GRANT_SUDO` | 是否授予 sudo 管理员权限 | `yes` |

**示例：使用自定义密码启动**

```bash
USER_PASSWORD=mypassword JUPYTER_TOKEN=mytoken ./run-standalone.sh jupyter
```

#### 访问 Jupyter Notebook

1. 打开浏览器，访问：`http://localhost:8888`
2. 在登录页面输入 Token（启动时显示的 Token，默认是 `mysecret`）
3. 点击 "Login" 即可进入 Jupyter 主界面

> 💡 您的 Notebook 文件请保存在 `notebooks/` 目录下，该目录已挂载到本地，可以持久化保存。

#### SSH 连接

如果需要通过 SSH 连接到容器（用于远程开发、文件传输等）：

```bash
ssh -p 2222 caffe-origin@localhost
```

- 用户名：`caffe-origin`
- 密码：启动时设置的 `USER_PASSWORD`（默认 `pass`）

**Windows 用户**：可以使用 PowerShell、Putty、VS Code Remote-SSH 等工具连接。

#### 查看容器日志

如果需要查看容器运行日志（排查问题时很有用）：

```bash
docker logs -f caffe-jupyter
```

按 `Ctrl+C` 退出日志查看。

#### 停止 Jupyter 容器

```bash
docker stop caffe-jupyter
```

或者使用脚本：

```bash
./run-standalone.sh jupyter-stop
```

---

### 4.3 手动 Docker 命令（高级用户）

如果您熟悉 Docker，也可以直接使用 `docker` 命令启动容器。

#### Runtime 镜像手动启动

**交互式 bash：**

```bash
docker run -it --rm caffe-cpu:origin-runtime bash
```

**一次性命令：**

```bash
docker run --rm caffe-cpu:origin-runtime python3 -c "import caffe; print(caffe.__version__)"
```

**挂载本地目录：**

```bash
docker run -it --rm \
  -v /your/local/path:/workspace/project \
  caffe-cpu:origin-runtime bash
```

#### Jupyter 镜像手动启动

```bash
docker run -d \
  --name caffe-jupyter \
  -p 2222:22 \
  -p 8888:8888 \
  -v $(pwd)/workspace:/workspace/notebooks \
  -e USER_PASSWORD=pass \
  -e JUPYTER_TOKEN=mysecret \
  -e GRANT_SUDO=yes \
  --restart unless-stopped \
  caffe-cpu:origin-jupyter
```

参数说明：
- `-p 2222:22`：将容器 SSH 端口映射到本地 2222 端口
- `-p 8888:8888`：将 Jupyter 端口映射到本地 8888 端口
- `-v ...`：挂载本地目录保存 Notebook 文件
- `-e ...`：设置环境变量

如果端口被占用，可以修改本地端口号，例如：
- `-p 2223:22`：SSH 使用 2223 端口
- `-p 8889:8888`：Jupyter 使用 8889 端口

---

## 5. 验证镜像完整性

### 运行验证脚本

任何时候都可以运行验证脚本确认镜像状态：

```bash
docker run --rm caffe-cpu:origin-runtime verify-caffe.sh
```

### 查看容器健康状态

对于 Jupyter 镜像，可以通过 `docker ps` 查看健康状态：

```bash
docker ps
```

输出中的 `STATUS` 列会显示健康状态：
- `(healthy)`：容器运行正常，SSH 和 Jupyter 服务就绪
- `(unhealthy)`：健康检查失败，可能服务未正常启动
- `(starting)`：容器正在启动中，请等待几秒再查看

### 健康检查失败排查

如果 Jupyter 容器显示 `unhealthy`：

1. **查看日志**：`docker logs caffe-jupyter`，查看是否有错误信息
2. **检查端口占用**：确认 2222 和 8888 端口没有被其他程序占用
3. **重建容器**：停止并删除旧容器，重新启动
   ```bash
   docker stop caffe-jupyter
   docker rm caffe-jupyter
   ./run-standalone.sh jupyter
   ```

---

## 6. 常见问题 FAQ

### Q1：镜像加载失败，提示文件损坏怎么办？

**A**：这通常是因为 tar 文件下载不完整或损坏。请重新获取镜像 tar 文件，然后再次尝试加载。

---

### Q2：启动时提示端口被占用怎么办？

**A**：Jupyter 镜像默认使用 8888（Jupyter）和 2222（SSH）端口。如果这些端口被其他程序占用：

1. **停止占用端口的程序**，或者
2. **修改端口映射**，使用手动 Docker 命令启动，将本地端口改为其他未被占用的端口：
   ```bash
   docker run -d \
     --name caffe-jupyter \
     -p 2223:22 \
     -p 8889:8888 \
     -v $(pwd)/workspace:/workspace/notebooks \
     -e USER_PASSWORD=pass \
     -e JUPYTER_TOKEN=mysecret \
     caffe-cpu:origin-jupyter
   ```
   然后访问 `http://localhost:8889`，SSH 使用 `ssh -p 2223 caffe-origin@localhost`。

---

### Q3：容器内创建的文件会保存吗？

**A**：默认情况下，容器内的文件系统是**临时的**，容器删除后所有文件都会丢失。

**持久化保存文件的方法：**

1. **挂载本地目录**（推荐）：启动时使用 `-v` 参数将本地目录挂载到容器内，保存在挂载目录中的文件会直接写入本地磁盘。

2. **使用 docker cp 复制文件**：在容器停止前，将文件复制到本地：
   ```bash
   # 从容器复制到本地
   docker cp caffe-jupyter:/workspace/notebooks/your_file.ipynb ./

   # 从本地复制到容器
   docker cp ./your_file.py caffe-jupyter:/workspace/notebooks/
   ```

3. **使用 Jupyter 镜像的 notebooks 目录**：`run-standalone.sh jupyter` 启动时会自动创建 `workspace/` 目录并挂载到容器的 `/workspace/notebooks/`，保存在这里的文件会自动持久化。

---

### Q4：Jupyter 页面无法访问？

**A**：请按以下步骤排查：

1. **检查容器是否运行**：
   ```bash
   docker ps
   ```
   如果看不到 `caffe-jupyter` 容器，说明容器未启动，请重新启动。

2. **检查端口映射**：确保启动时正确映射了 8888 端口（或您自定义的端口）。

3. **检查防火墙设置**：确保本地防火墙没有阻止 8888 端口的访问。

4. **查看容器日志**：
   ```bash
   docker logs caffe-jupyter
   ```
   查看是否有错误信息。

5. **等待启动完成**：容器启动需要几秒时间初始化服务，请稍等片刻再刷新浏览器。

---

### Q5：SSH 连接被拒绝？

**A**：请检查：

1. **确认容器已启动完成**：运行 `docker ps`，STATUS 列显示 `(healthy)` 表示服务就绪。

2. **确认 USER_PASSWORD 已设置**：如果启动时没有设置 `USER_PASSWORD`，容器会自动生成随机密码并打印在日志中，运行 `docker logs caffe-jupyter` 查看密码。

3. **检查端口是否正确**：默认 SSH 端口是 2222，如果您修改了端口映射，请使用对应的端口号连接。

4. **首次连接提示**：第一次 SSH 连接会提示 "Are you sure you want to continue connecting?"，输入 `yes` 回车即可。

---

### Q6：如何从容器内复制文件到宿主机？

**A**：使用 `docker cp` 命令：

```bash
# 从容器复制文件到本地当前目录
docker cp caffe-jupyter:/workspace/notebooks/my_notebook.ipynb ./

# 从容器复制整个目录到本地
docker cp caffe-jupyter:/workspace/notebooks/ ./my_notebooks_backup/

# 从本地复制文件到容器
docker cp ./my_script.py caffe-jupyter:/workspace/notebooks/
```

> 💡 如果容器正在运行也可以复制，不需要停止容器。

---

### Q7：这个镜像支持 GPU 吗？

**A**：**不支持**。本文档介绍的是 CPU 版本镜像，只能使用 CPU 运行 Caffe。如果您需要 GPU 加速，请使用支持 GPU 的 Caffe 镜像（需要 NVIDIA GPU 和 nvidia-docker）。

---

### Q8：如何修改默认密码/Token？

**A**：启动容器时通过环境变量设置：

```bash
# 设置自定义 SSH 密码和 Jupyter Token
USER_PASSWORD=your_ssh_password JUPYTER_TOKEN=your_jupyter_token ./run-standalone.sh jupyter
```

如果您想要设置 Jupyter 密码（而不是 Token），可以设置 `JUPYTER_PASSWORD` 环境变量：

```bash
USER_PASSWORD=your_ssh_password JUPYTER_PASSWORD=your_jupyter_password ./run-standalone.sh jupyter
```

设置密码后，Jupyter 登录时输入密码即可，不需要 Token。

---

### Q9：如何在容器内安装额外的 Python 包？

**A**：

- **临时安装**（容器重启后失效）：
  ```bash
  # 进入容器
  docker exec -it caffe-jupyter bash
  # 安装包
  pip install package_name
  ```

- **在 Jupyter Notebook 中安装**（当前会话有效）：
  ```python
  !pip install package_name
  ```

> 💡 如果需要持久化安装额外的包，建议基于本镜像创建新的 Dockerfile，或者将您的脚本和依赖放在挂载的本地目录中。

---

## 7. 目录结构说明

容器内的关键路径：

| 路径 | 说明 |
|-----|------|
| `/workspace/` | 工作目录（启动时默认进入此目录） |
| `/workspace/caffex/` | Caffe 安装根目录（包含源码、编译产物） |
| `/workspace/caffex/python/` | PyCaffe Python 模块路径（已加入 PYTHONPATH） |
| `/workspace/caffex/build/tools/` | Caffe 命令行工具目录（已加入 PATH） |
| `/workspace/notebooks/` | Jupyter Notebook 工作目录（Jupyter 镜像，已挂载到本地） |

### 常用 Caffe 命令行工具

在 `/workspace/caffex/build/tools/` 目录下可以找到以下工具（已加入 PATH，可直接在命令行使用）：

| 工具 | 用途 |
|-----|------|
| `caffe` | Caffe 主程序，用于训练、测试模型 |
| `convert_imageset` | 将图片数据集转换为 Caffe 支持的 lmdb/leveldb 格式 |
| `compute_image_mean` | 计算图像数据集的均值文件 |
| `upgrade_net_proto_text` | 升级旧版本的网络定义 prototxt 文件 |
| `upgrade_solver_proto_text` | 升级旧版本的求解器 prototxt 文件 |

### 使用 Caffe Python 模块

在容器内任何位置都可以直接导入 Caffe：

```python
import caffe
import numpy as np

# 查看 Caffe 版本
print("Caffe 版本:", caffe.__version__)

# 创建 Blob（Caffe 的基本数据结构）
blob = caffe.Blob([1, 3, 224, 224])
print("Blob 形状:", blob.shape)
```

环境变量已预先配置好，不需要额外设置 `CAFFE_ROOT` 或 `PYTHONPATH`。

---

> 📌 **提示**：如果您在使用过程中遇到本文档未覆盖的问题，可以查看容器内的验证脚本输出或日志信息定位问题。
