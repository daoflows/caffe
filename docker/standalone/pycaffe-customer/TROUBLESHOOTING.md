# PyCaffe Customer 镜像故障排查指南

> 本文档列出了客户在加载、运行和使用 `caffe-cpu:customer` Docker 镜像时可能遇到的常见问题及解决方案。
> 按照问题分类组织，每个问题包含：**症状**、**可能原因**、**诊断步骤**、**解决方案**。

---

## 目录

1. [镜像加载问题](#1-镜像加载问题)
2. [容器启动问题](#2-容器启动问题)
3. [Jupyter Notebook 访问问题](#3-jupyter-notebook-访问问题)
4. [SSH 访问问题](#4-ssh-访问问题)
5. [PyCaffe/Caffe 导入和运行问题](#5-pycaffecaffe-导入和运行问题)
6. [模型推理问题](#6-模型推理问题)
7. [性能问题](#7-性能问题)
8. [权限和安全问题](#8-权限和安全问题)
9. [网络和端口问题](#9-网络和端口问题)
10. [存储和数据持久化问题](#10-存储和数据持久化问题)
11. [获取帮助](#11-获取帮助)

---

## 1. 镜像加载问题

### 1.1 `docker load` 报错 "invalid argument" 或 "Unrecognized archive format"

**症状**：
```
$ docker load -i caffe-cpu-customer-1.0.0.tar
open /var/lib/docker/tmp/...: no such file or directory
Error processing tar file(exit status 1): Unrecognized archive format
```

**可能原因**：
- tar 文件下载不完整或已损坏
- 文件传输过程中被截断
- 文件被错误地解压或重新打包

**诊断步骤**：
1. 检查文件大小是否合理（预期约 1.5-2.5 GB）：
   ```bash
   ls -lh caffe-cpu-customer-*.tar
   ```
2. 校验 SHA256 校验和（如果随包提供了 `.sha256` 文件）：
   ```bash
   sha256sum -c caffe-cpu-customer-1.0.0-<date>.tar.sha256
   ```
3. 验证 tar 文件格式：
   ```bash
   file caffe-cpu-customer-*.tar
   # 应输出 "POSIX tar archive" 或 "gzip compressed data"
   ```

**解决方案**：
- 重新下载/获取镜像 tar 文件
- 如果使用 gzip 压缩版本（`.tar.gz`），先解压再加载，或使用 `gunzip` 管道：
  ```bash
  gunzip -c caffe-cpu-customer-1.0.0.tar.gz | docker load
  ```
- 确认传输方式使用二进制模式（如果通过 FTP/SFTP 传输）

---

### 1.2 `docker load` 后 `docker images` 看不到镜像

**症状**：`docker load` 显示 "Loaded image" 成功，但 `docker images` 列表中没有 `caffe-cpu:customer`。

**可能原因**：镜像加载时使用了不同的 tag 名称。

**诊断步骤**：
```bash
docker images | grep -i caffe
# 或列出所有镜像
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}"
```

**解决方案**：
```bash
# 如果镜像以其他名称加载，重新打标签
docker tag <IMAGE_ID> caffe-cpu:customer
```

---

### 1.3 Docker 版本兼容性错误

**症状**：
```
failed to register layer: Error processing tar file(...): archive/tar: invalid tar header
```
或
```
docker: image operating system "linux" cannot be used on this platform.
```

**可能原因**：
- Docker 版本太旧（需要 Docker 17.06+，建议 20.10+）
- 在 Windows/macOS 上运行 Linux 容器时容器模式不匹配
- 在 ARM 架构（如 Apple Silicon M1/M2）上运行为 x86_64 构建的镜像

**诊断步骤**：
```bash
docker version --format '{{.Server.Version}}'
docker info --format '{{.OSType}} / {{.Architecture}}'
# 检查镜像架构
docker image inspect caffe-cpu:customer --format '{{.Architecture}}/{{.Os}}'
```

**解决方案**：
- **版本过旧**：升级 Docker Engine/Docker Desktop 到最新版本
- **架构不匹配（ARM Mac）**：使用 `--platform linux/amd64` 参数运行：
  ```bash
  docker run --platform linux/amd64 -d -p 8888:8888 -p 2222:22 caffe-cpu:customer
  ```
  注意：在 ARM 上通过 QEMU 模拟运行 x86 镜像性能会显著下降。

---

## 2. 容器启动问题

### 2.1 容器启动后立即退出（Exited (0/1/127/139)）

**症状**：`docker run` 后容器状态是 `Exited` 而非 `Up`。

**诊断步骤**：
1. 检查退出码：
   ```bash
   docker ps -a
   # 查看 STATUS 列，例如 "Exited (1) 5 seconds ago"
   ```
2. 查看容器日志：
   ```bash
   docker logs <container_name>
   # 或实时追踪
   docker logs -f <container_name>
   ```

**常见退出码和解决方案**：

| 退出码 | 可能原因 | 解决方案 |
|--------|---------|---------|
| **0** | 容器正常退出（没有启动服务） | 启动时不要加额外命令；或使用 `-d` 后台运行服务模式 |
| **1** | 启动脚本错误/配置错误 | 查看日志具体错误信息；检查 `docker logs` |
| **127** | 找不到命令/入口点 | 镜像可能损坏；重新 `docker load` |
| **139** | Segmentation fault (SIGSEGV) | 通常是架构不兼容或库版本冲突；检查 `docker run` 时是否加了 `--platform` |

**使用诊断模式启动**：
```bash
# 以交互模式启动，不启动服务，直接进入 shell 诊断
docker run --rm -it --entrypoint bash caffe-cpu:customer
# 在容器内手动验证
caffe-verify
python -c "import caffe; print(caffe.__version__)"
supervisord --version
sshd -t
```

---

### 2.2 容器启动但服务没有运行（健康检查失败）

**症状**：
```bash
docker ps
# STATUS 列显示 "unhealthy"
```

**诊断步骤**：
```bash
# 查看健康检查输出
docker inspect --format='{{json .State.Health}}' <container_name> | python -m json.tool

# 查看 supervisord 和各服务日志
docker exec <container_name> supervisorctl status
docker exec <container_name> cat /var/log/supervisor/jupyter-stderr.log
```

**解决方案**：
- 重启容器：`docker restart <container_name>`
- 检查端口是否被占用（见 [端口问题](#9-网络和端口问题)）
- 进入容器手动启动服务排查：
  ```bash
  docker exec -it <container_name> bash
  # 手动启动 jupyter 查看错误
  su - builder -c "jupyter notebook"
  ```

---

### 2.3 启动时权限错误 (Permission denied)

**症状**：日志中出现 `Permission denied`、`chmod: cannot access`、`chown: invalid user`。

**可能原因**：
- 使用了 `--user` 参数覆盖了默认用户
- 挂载的宿主机目录权限不匹配
- 镜像文件系统损坏

**解决方案**：
- 不指定 `--user` 参数（容器内部自动处理用户权限）
- 如果挂载了数据卷，确保目录权限正确：
  ```bash
  # 临时方案：让 builder 用户可以读写挂载目录
  chmod -R 777 /your/host/data/directory
  # 或者在 Linux 上指定 UID 映射
  docker run -d -p 8888:8888 -v $(pwd)/data:/workspace/data \
    --user root caffe-cpu:customer -c "chown -R builder:builder /workspace/data && gosu builder entrypoint.sh"
  ```

---

## 3. Jupyter Notebook 访问问题

### 3.1 浏览器无法访问 http://localhost:8888

**症状**：浏览器显示 "Unable to connect" / "This site can't be reached"。

**诊断步骤**：
1. 确认容器正在运行且端口映射正确：
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   # 应看到 "0.0.0.0:8888->8888/tcp"
   ```
2. 检查 Jupyter 是否在容器内运行：
   ```bash
   docker exec <container_name> curl -s http://127.0.0.1:8888/api | head -c 200
   # 正常应返回 JSON 内容
   ```
3. 检查宿主机防火墙是否阻止了 8888 端口

**解决方案**：
- **端口未映射**：重新运行容器，确保加了 `-p 8888:8888` 参数
  ```bash
  docker run -d -p 8888:8888 -p 2222:22 --name caffe caffe-cpu:customer
  ```
- **端口冲突**：宿主机 8888 端口被占用时，映射到其他端口：
  ```bash
  docker run -d -p 9999:8888 -p 2222:22 --name caffe caffe-cpu:customer
  # 访问 http://localhost:9999
  ```
- **防火墙问题**：在 Linux 上允许端口：
  ```bash
  sudo ufw allow 8888/tcp  # Ubuntu/Debian
  # 或
  sudo firewall-cmd --add-port=8888/tcp --permanent && sudo firewall-cmd --reload  # CentOS/RHEL
  ```
- **Docker Desktop (Windows/Mac)**：确认 Docker Desktop 正在运行，尝试使用 `http://127.0.0.1:8888` 而不是 `localhost`

---

### 3.2 Token/密码不正确，无法登录 Jupyter

**症状**：Jupyter 页面要求输入 token/password，但输入默认 token `caffe-token` 后提示无效。

**诊断步骤**：
1. 查看启动日志中的实际 token：
   ```bash
   docker logs <container_name> 2>&1 | grep -i "token\|Token"
   ```
2. 检查容器内 Jupyter 配置：
   ```bash
   docker exec <container_name> cat /home/builder/.jupyter/jupyter_server_config.d/runtime.py
   ```

**可能原因和解决方案**：

| 原因 | 解决方案 |
|------|---------|
| 设置了 `JUPYTER_PASSWORD` 环境变量 | 输入你设置的密码（不是 token） |
| 设置了 `JUPYTER_TOKEN` 环境变量 | 使用你设置的自定义 token |
| Token 被浏览器缓存 | 使用隐私/无痕模式打开，或清除浏览器缓存 |
| 容器重启后 token 未更新 | 查看 `docker logs` 中打印的当前 token |

**重置 token（如果忘记）**：
```bash
# 方式1：重启容器时指定新 token
docker restart <container_name>
# 不，这不会改变 token... 需要重新创建容器

# 方式2：设置固定 token
docker rm -f <container_name>
docker run -d -p 8888:8888 -p 2222:22 \
  -e JUPYTER_TOKEN=my-secret-token \
  --name caffe caffe-cpu:customer

# 方式3：获取当前 token
docker exec <container_name> jupyter server list
```

---

### 3.3 Jupyter 中无法执行 Python/Import caffe 失败

**症状**：在 Notebook 中执行 `import caffe` 报 `ModuleNotFoundError` 或 `ImportError`。

**诊断步骤**：
```bash
# 在容器内验证
docker exec <container_name> caffe-verify

# 进入容器手动检查
docker exec -it <container_name> bash
python -c "import sys; print(sys.path)"
python -c "import caffe; print(caffe.__file__)"
python -c "import pycaffe; print(pycaffe.__version__)"
```

**解决方案**：
- 如果 `caffe-verify` 通过但 Notebook 中不行，可能是 Notebook kernel 问题：
  ```bash
  docker exec -it <container_name> bash
  # 检查 kernel
  jupyter kernelspec list
  # 重启 kernel（在 Jupyter 菜单: Kernel → Restart Kernel）
  ```
- 如果 `caffe-verify` 也失败，参考 [第5节](#5-pycaffecaffe-导入和运行问题)

---

### 3.4 Jupyter 内核启动失败 / Kernel 一直显示 "Busy"

**症状**：Notebook 中执行代码一直显示 `In [*]:` 且不返回结果。

**诊断步骤**：
```bash
docker exec <container_name> cat /var/log/supervisor/jupyter-stderr.log | tail -50
docker exec <container_name> ps aux | grep ipykernel
```

**解决方案**：
- 内存不足：增加 Docker Desktop 的内存限制（建议至少 4GB）
- 重启 Jupyter 内核：在 Jupyter 菜单中选择 Kernel → Restart
- 重启容器：`docker restart <container_name>`

---

## 4. SSH 访问问题

### 4.1 SSH 连接被拒绝 (Connection refused)

**症状**：
```
$ ssh builder@localhost -p 2222
ssh: connect to host localhost port 2222: Connection refused
```

**可能原因**：
- SSH 被禁用（`DISABLE_SSH=yes`）
- 端口映射不正确
- sshd 进程未启动

**诊断步骤**：
```bash
# 检查端口映射
docker port <container_name> 22

# 检查 sshd 是否运行
docker exec <container_name> pgrep -a sshd

# 检查 SSH 是否被禁用
docker exec <container_name> supervisorctl status
# 如果看到 "sshd: removed" 或没有 sshd 进程，说明 SSH 被禁用
```

**解决方案**：
- 如果 SSH 被禁用，重新创建容器时不设置 `DISABLE_SSH`（默认启用）：
  ```bash
  docker run -d -p 8888:8888 -p 2222:22 -e DISABLE_SSH=no --name caffe caffe-cpu:customer
  ```
- 确认端口映射正确：`-p 2222:22`（宿主机端口:容器端口）

---

### 4.2 SSH 密码认证失败 (Permission denied)

**症状**：
```
builder@localhost's password: caffepass
Permission denied, please try again.
```

**可能原因**：
- 密码被 `USER_PASSWORD` 环境变量覆盖
- 密码在启动时被随机生成（不太可能，但可以检查）
- 键盘交互式认证被禁用

**诊断步骤**：
1. 确认你使用的密码：
   - 默认密码是 `caffepass`
   - 如果启动时设置了 `-e USER_PASSWORD=mypassword`，则使用 `mypassword`
2. 在容器内验证密码：
   ```bash
   docker exec -it <container_name> bash -c "echo 'builder:caffepass' | chpasswd && echo 'Password reset to caffepass'"
   ```

**解决方案**：
- 使用正确的密码（查看 `docker logs` 中的启动信息）
- 重置密码：
  ```bash
  docker exec -it <container_name> bash -c "echo 'builder:caffepass' | chpasswd"
  ```
- 重新创建容器并设置明确密码：
  ```bash
  docker run -d -p 8888:8888 -p 2222:22 \
    -e USER_PASSWORD=your_password \
    --name caffe caffe-cpu:customer
  ```

---

### 4.3 SSH 连接成功但立即断开 / PTY allocation error

**症状**：
```
$ ssh builder@localhost -p 2222
PTY allocation request failed on channel 0
```
或连接后立即返回 shell prompt。

**解决方案**：
- 使用 `-t` 强制分配 PTY：
  ```bash
  ssh -t builder@localhost -p 2222
  ```
- 确保使用正确的 shell：
  ```bash
  ssh builder@localhost -p 2222 -t "bash -l"
  ```

---

## 5. PyCaffe/Caffe 导入和运行问题

### 5.1 `import caffe` 或 `import pycaffe` 失败

**症状**：
```python
>>> import caffe
ImportError: libxxx.so: cannot open shared object file: No such file or directory
```
或
```python
>>> import pycaffe
ModuleNotFoundError: No module named 'pycaffe'
```

**诊断步骤**：
1. 运行自检脚本（输出详细错误信息）：
   ```bash
   docker exec <container_name> caffe-verify
   ```
2. 手动检查库路径：
   ```bash
   docker exec -it <container_name> bash
   ldd /usr/local/lib/_caffe.so 2>&1 | grep "not found"
   python -c "import sys; print('\n'.join(sys.path))"
   ldconfig -p | grep caffe
   ```

**常见错误和解决方案**：

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `libopenblas.so.0: cannot open shared object file` | OpenBLAS 库缺失 | 镜像不完整，重新 `docker load` |
| `libprotobuf.so.32: cannot open shared object file` | Protobuf 库缺失 | 同上，重新加载镜像 |
| `libgomp.so.1: cannot open shared object file` | OpenMP 运行时库缺失 | 同上 |
| `libtvm_ffi.so: cannot open shared object file` | tvm-ffi 库缺失 | 镜像构建可能有问题，重新构建 |
| `No module named 'caffe'` | Python 路径问题 | 检查 `caffe-verify` 输出，确保 PYTHONPATH 正确 |

如果 `ldd` 显示 "not found" 的库，这说明镜像可能已损坏或构建不完整。重新 `docker load` 或重新构建镜像。

---

### 5.2 `_caffe.so: wrong ELF class: ELFCLASS32` 或架构错误

**症状**：ImportError 提示 ELF class 不匹配。

**原因**：在 ARM 架构（如 Apple Silicon M1/M2）上运行为 x86_64 构建的镜像，且未启用 QEMU 模拟。

**解决方案**：
- 在 Docker Desktop for Mac (Apple Silicon) 上：
  1. 打开 Docker Desktop → Settings → Features in Development
  2. 启用 "Use Rosetta for x86/AMD64 emulation on Apple Silicon"
  3. 重启 Docker Desktop
  4. 运行时加 `--platform linux/amd64`：
     ```bash
     docker run --platform linux/amd64 -d -p 8888:8888 -p 2222:22 caffe-cpu:customer
     ```
- 如果性能不可接受，需要在 x86_64 Linux 机器上使用本镜像

---

### 5.3 Protocol Buffer 版本不兼容错误

**症状**：
```
[libprotobuf ERROR] This program requires version 3.x of the Protocol Buffer
runtime, but the installed version is 2.x.
```
或
```
TypeError: Descriptors cannot not be created directly.
```

**原因**：protobuf Python 包和系统 libprotobuf 库版本不匹配。

**解决方案**：
- 镜像中已固定了兼容的版本，正常不会出现此问题
- 如果因为挂载了外部 Python 包路径导致冲突：
  ```bash
  # 在容器内检查 Python 路径优先级
  python -c "import google.protobuf; print(google.protobuf.__file__)"
  # 确保不要将宿主机的 Python 包挂载到容器的 PYTHONPATH 中
  ```
- 运行时避免设置 `PYTHONPATH` 环境变量指向外部路径

---

## 6. 模型推理问题

### 6.1 ResNet50 示例推理失败

**症状**：运行 `python /opt/caffe-examples/infer.py` 报错。

**诊断步骤**：
```bash
# 首先运行完整自检
docker exec <container_name> caffe-verify

# 手动运行 ResNet50 推理
docker exec -it <container_name> bash
cd /opt/caffe-examples
ls -la resnet50/  # 确认模型文件存在
python infer.py
```

**常见错误**：

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| `FileNotFoundError: ResNet-50-model.caffemodel` | 模型文件不存在 | 镜像可能构建时未包含示例文件，确认使用正确的镜像 |
| `Check failed: ReadProtoFromBinaryFile` | 模型文件损坏 | 重新加载镜像 |
| `Cannot copy to a Tensor` | 输入图像格式错误 | 检查输入图像预处理 |
| `F0804 ... Check failed: status == CUBLAS_STATUS_SUCCESS` | GPU模式错误 | 本镜像为 CPU-only，确认代码中调用了 `caffe.set_mode_cpu()` |

**验证 ResNet50 demo 文件完整性**：
```bash
docker exec <container_name> ls -lh /opt/caffe-examples/resnet50/
docker exec <container_name> ls -lh /opt/caffe-examples/infer.py
# 预期看到:
# -rw-r--r-- ... ResNet-50-deploy.prototxt (~30KB)
# -rw-r--r-- ... ResNet-50-model.caffemodel (~97MB)
# drwxr-xr-x ... data/
```

---

### 6.2 加载自己的模型时出错

**症状**：加载自定义 `.prototxt` 或 `.caffemodel` 文件时报错。

**诊断步骤**：
1. 确认模型文件格式正确（Caffe 格式，不是 ONNX/TensorFlow/PyTorch 格式）
2. 检查文件路径是否正确（建议挂载到 `/workspace` 目录）：
   ```bash
   docker run -d -p 8888:8888 -p 2222:22 \
     -v /path/to/your/models:/workspace/models \
     --name caffe caffe-cpu:customer
   ```
3. 确认使用 CPU 模式：
   ```python
   import caffe
   caffe.set_mode_cpu()
   net = caffe.Net('/workspace/models/deploy.prototxt', 
                   '/workspace/models/weights.caffemodel', 
                   caffe.TEST)
   ```

**限制说明**：
- 本镜像是 **CPU-only** 推理版本，不支持 GPU 推理（`caffe.set_mode_gpu()` 会报错或无效）
- 本镜像为 slim 推理版本，不包含训练功能（Solver 类不可用）
- 如果需要训练，请使用完整的 BVLC Caffe 镜像

---

### 6.3 推理结果不正确/输出异常值

**诊断步骤**：
1. 确认输入图像预处理方式与模型训练时一致
2. 检查均值文件（mean.binaryproto）是否正确加载
3. 确认输入 blob 的维度顺序（NCHW）和数据范围

**解决方案**：
- 参考 `/opt/caffe-examples/infer.py` 中的预处理流程
- 使用 pycaffe 的 Transformer 类进行标准预处理：
  ```python
  from pycaffe import Transformer
  transformer = Transformer({'data': (1, 3, 224, 224)})
  transformer.set_transpose('data', (2, 0, 1))
  transformer.set_mean('data', mean)  # 加载均值
  transformer.set_raw_scale('data', 255)
  transformer.set_channel_swap('data', (2, 1, 0))  # RGB→BGR
  ```

---

## 7. 性能问题

### 7.1 推理速度很慢

**可能原因和解决方案**：

| 原因 | 解决方案 |
|------|---------|
| 在 ARM Mac 上通过 Rosetta/QEMU 模拟 | 使用 x86_64 Linux 机器获得最佳性能 |
| Docker Desktop 分配的 CPU/内存不足 | 在 Docker Desktop 设置中增加 CPU 核心数和内存（建议至少 4 核 8GB） |
| OpenBLAS 未使用所有 CPU 核心 | 设置线程数：`OPENBLAS_NUM_THREADS=4 docker run ...` |
| 模型太大或批量太大 | 减小 batch size |

**设置 OpenBLAS 线程数**：
```bash
docker run -d -p 8888:8888 -p 2222:22 \
  -e OPENBLAS_NUM_THREADS=4 \
  -e OMP_NUM_THREADS=4 \
  --name caffe caffe-cpu:customer
```

---

### 7.2 Jupyter Notebook 响应慢

**可能原因**：
- 容器内存不足
- Notebook 中输出结果过大
- 大量计算占用了所有 CPU

**解决方案**：
- 增加 Docker 内存限制
- 清理 Notebook 输出（Cell → All Output → Clear）
- 限制计算进程的 CPU 使用

---

## 8. 权限和安全问题

### 8.1 在 Notebook/SSH 中无法安装 pip 包

**症状**：
```
$ pip install some-package
error: externally-managed-environment
```

**原因**：Ubuntu 26.04 使用 PEP 668 外部管理环境标记。

**解决方案**：
- 使用 `--break-system-packages` 标志（容器内环境是隔离的，安全）：
  ```bash
  pip install --break-system-packages some-package
  ```
- 或使用虚拟环境（推荐用于持久化）：
  ```bash
  python -m venv /workspace/venv
  source /workspace/venv/bin/activate
  pip install some-package
  ```

---

### 8.2 sudo 需要密码

**症状**：在容器内使用 `sudo` 时要求输入密码。

**原因**：默认 `GRANT_SUDO=no`，builder 用户没有 sudo 权限。

**解决方案**：
- 启动容器时启用 sudo：
  ```bash
  docker run -d -p 8888:8888 -p 2222:22 \
    -e GRANT_SUDO=yes \
    --name caffe caffe-cpu:customer
  ```
- 默认密码是 `caffepass`（或通过 `USER_PASSWORD` 设置的密码）
- **注意**：启用 sudo 会降低安全性，仅在需要时使用

---

### 8.3 如何修改默认密码/token

**默认凭证**（生产环境务必修改）：
- SSH 密码：`caffepass`
- Jupyter token：`caffe-token`

**修改方式**：
```bash
docker run -d -p 8888:8888 -p 2222:22 \
  -e USER_PASSWORD=your_strong_password \
  -e JUPYTER_TOKEN=your_secure_token \
  --name caffe caffe-cpu:customer
```

**使用 SSH 公钥认证**（更安全）：
```bash
docker run -d -p 8888:8888 -p 2222:22 \
  -e SSH_PUBLIC_KEY="$(cat ~/.ssh/id_rsa.pub)" \
  -e USER_PASSWORD=!disabled! \
  --name caffe caffe-cpu:customer
```

---

## 9. 网络和端口问题

### 9.1 端口已被占用

**症状**：
```
docker: Error response from daemon: driver failed programming external connectivity:
Bind for 0.0.0.0:8888 failed: port is already allocated.
```

**诊断步骤**：
```bash
# 查看哪个进程占用了端口
# Linux:
sudo lsof -i :8888
sudo netstat -tlnp | grep 8888
# Windows (PowerShell):
netstat -ano | findstr :8888
```

**解决方案**：
- 停止占用端口的其他容器/进程
- 或映射到不同的宿主机端口：
  ```bash
  docker run -d -p 9999:8888 -p 2222:22 --name caffe caffe-cpu:customer
  # 访问 http://localhost:9999
  ```

---

### 9.2 容器内无法访问外网（无法 pip install / wget）

**症状**：容器内 `pip install` 或 `wget` 报网络连接错误。

**可能原因**：
- 宿主机防火墙/DNS 配置问题
- Docker 网络配置问题
- 企业代理需要配置

**诊断步骤**：
```bash
docker exec <container_name> curl -I https://pypi.org
docker exec <container_name> cat /etc/resolv.conf
docker exec <container_name> ping -c 1 8.8.8.8
```

**解决方案**：
- 配置 Docker 使用宿主 DNS：在 Docker Desktop → Settings → Docker Engine 中添加 DNS：
  ```json
  { "dns": ["8.8.8.8", "114.114.114.114"] }
  ```
- 配置 HTTP 代理（如果在企业网络中）：
  ```bash
  docker run -d -p 8888:8888 -p 2222:22 \
    -e HTTP_PROXY=http://proxy.company.com:8080 \
    -e HTTPS_PROXY=http://proxy.company.com:8080 \
    -e NO_PROXY=localhost,127.0.0.1 \
    --name caffe caffe-cpu:customer
  ```

---

### 9.3 在远程服务器上访问 Jupyter

**场景**：容器运行在远程服务器上，需要在本地浏览器访问 Jupyter。

**解决方案**：
1. **SSH 端口转发**（推荐）：
   ```bash
   # 在本地机器上执行
   ssh -L 8888:localhost:8888 user@remote-server
   # 然后本地访问 http://localhost:8888
   ```
2. **直接映射到 0.0.0.0**（注意安全风险）：
   ```bash
   # 在远程服务器上
   docker run -d -p 0.0.0.0:8888:8888 -p 0.0.0.0:2222:22 \
     -e JUPYTER_PASSWORD=secure_password \
     -e USER_PASSWORD=secure_password \
     caffe-cpu:customer
   # 访问 http://remote-server:8888
   ```
   **重要**：直接暴露到公网时必须设置强密码和/或限制 IP 访问。

---

## 10. 存储和数据持久化问题

### 10.1 容器重启后 Notebooks/数据丢失

**症状**：重新创建容器后，之前在 Jupyter 中创建的 Notebook 不见了。

**原因**：容器文件系统是临时的，删除容器后所有更改丢失。

**解决方案**：使用数据卷挂载持久化数据：
```bash
# 将本地目录挂载到容器的 /workspace
docker run -d -p 8888:8888 -p 2222:22 \
  -v $(pwd)/workspace:/workspace \
  --name caffe caffe-cpu:customer

# Windows PowerShell:
docker run -d -p 8888:8888 -p 2222:22 \
  -v ${PWD}\workspace:/workspace \
  --name caffe caffe-cpu:customer
```

**重要目录**：
- `/workspace` — Jupyter 根目录，你的 Notebook 和数据应放在这里
- `/opt/caffe-examples` — 内置示例（只读，不需要持久化）

---

### 10.2 挂载目录后权限错误

**症状**：Jupyter 中无法保存文件，或 SSH 中无法写入挂载目录。

**原因**：容器内 builder 用户的 UID（1000）和宿主机目录的所有者 UID 不匹配。

**解决方案**：
- Linux：修改宿主机目录的所有者
  ```bash
  sudo chown -R 1000:1000 ./workspace
  ```
- 或使用 named volume（自动处理权限）：
  ```bash
  docker volume create caffe-workspace
  docker run -d -p 8888:8888 -p 2222:22 \
    -v caffe-workspace:/workspace \
    --name caffe caffe-cpu:customer
  ```

---

## 11. 获取帮助

### 11.1 收集诊断信息（提交问题时请提供）

运行以下命令收集信息，在报告问题时提供：

```bash
# 1. 容器基本信息
docker ps -a
docker inspect <container_name> --format 'ID={{.ID}}, Image={{.Config.Image}}, Status={{.State.Status}}'

# 2. 镜像信息
docker images caffe-cpu:customer
docker image inspect caffe-cpu:customer --format 'Arch={{.Architecture}}, OS={{.Os}}, Size={{.Size}}'

# 3. 容器日志（最后100行）
docker logs --tail 100 <container_name>

# 4. 自检结果
docker exec <container_name> caffe-verify

# 5. 版本信息
docker exec <container_name> cat /etc/caffe-customer-release

# 6. Docker 版本
docker version
docker info
```

### 11.2 快速诊断清单

在报告问题前，请确认：

- [ ] Docker 版本 ≥ 20.10（`docker --version`）
- [ ] 镜像已正确加载（`docker images | grep caffe`）
- [ ] 容器正在运行（`docker ps`）
- [ ] 端口映射正确（`docker port <container_name>`）
- [ ] 已运行 `caffe-verify` 自检
- [ ] 已查看容器日志（`docker logs <container_name>`）
- [ ] 宿主机架构与镜像架构匹配（x86_64/amd64）

---

## 附录：快速参考命令

```bash
# 加载镜像
docker load -i caffe-cpu-customer-1.0.0.tar

# 运行容器（默认凭证）
docker run -d -p 8888:8888 -p 2222:22 --name caffe caffe-cpu:customer

# 运行容器（自定义凭证）
docker run -d -p 8888:8888 -p 2222:22 \
  -e USER_PASSWORD=mypassword \
  -e JUPYTER_TOKEN=mytoken \
  --name caffe caffe-cpu:customer

# 查看容器日志
docker logs -f caffe

# 运行自检
docker exec caffe caffe-verify

# 进入容器 shell
docker exec -it caffe bash

# 通过 SSH 进入
ssh builder@localhost -p 2222

# 停止/启动/重启
docker stop caffe
docker start caffe
docker restart caffe

# 删除容器
docker rm -f caffe

# 查看镜像构建信息
docker run --rm caffe-cpu:customer cat /etc/caffe-customer-release
```
