# PyCaffe Jupyter SSH — 快速启动指南

镜像标签：`caffe-cpu:pycaffe-jupyter-ssh`
基础系统：Ubuntu 26.04 | Python 3 | Caffe 1.0.0-slim | 中文 zh_CN.UTF-8 / Asia/Shanghai
容器用户：`builder` (UID 1001)

---

## 一、构建镜像

> ⚠️ **构建上下文必须在 `vendor/` 目录下**（需要同时访问 `caffe/caffe-slim/` 和 `tvm-ffi/` 两个子模块）。
> 构建前确保子模块已初始化：`git submodule update --init --recursive`

### 方式一：使用便捷脚本（推荐）

```bash
cd /mnt/d/spaces/SpecWeave/projects/xuanspace/vendor   # WSL 路径
# 或 cd /path/to/vendor                                  # Linux 路径

# 使用脚本构建（自动检测环境、检查子模块、计时）
bash caffe/docker/standalone/pycaffe-jupyter-ssh/build.sh

# 指定标签构建
bash caffe/docker/standalone/pycaffe-jupyter-ssh/build.sh -t mytag

# 无缓存重建
bash caffe/docker/standalone/pycaffe-jupyter-ssh/build.sh --no-cache
```

### 方式二：手动 docker build

```bash
cd /mnt/d/spaces/SpecWeave/projects/xuanspace/vendor

docker build -t caffe-cpu:pycaffe-jupyter-ssh --target runtime \
  -f caffe/docker/standalone/pycaffe-jupyter-ssh/Dockerfile .
```

---

## 二、启动容器

### 方式一：使用便捷脚本（推荐，自动端口检测+密码生成）

```bash
cd /mnt/d/spaces/SpecWeave/projects/xuanspace/vendor

# 最简启动（自动分配端口、生成随机密码和 Token）
bash caffe/docker/standalone/pycaffe-jupyter-ssh/run.sh

# 指定端口、密码、挂载工作目录
bash caffe/docker/standalone/pycaffe-jupyter-ssh/run.sh \
  -p 2222 -j 8888 \
  -w /mnt/d/caffe-workspace \
  --user-password caffe123 \
  --jupyter-token mydevtoken

# 启动后立即跟踪日志
bash caffe/docker/standalone/pycaffe-jupyter-ssh/run.sh -a

# 前台交互模式（启动后直接进入容器 bash）
bash caffe/docker/standalone/pycaffe-jupyter-ssh/run.sh -it bash
```

### 方式二：手动 docker run

#### 最简启动（自动生成随机密码和 Token）

```bash
docker run -d \
  --name pycaffe-dev \
  -p 2222:22 \
  -p 8888:8888 \
  caffe-cpu:pycaffe-jupyter-ssh
```

#### 推荐启动（固定密码 + Token + 数据持久化 + sudo 权限）

```bash
docker run -d \
  --name pycaffe-dev \
  -p 2222:22 \
  -p 8888:8888 \
  -v ~/caffe-workspace:/workspace \
  -e USER_PASSWORD=caffe123 \
  -e JUPYTER_TOKEN=mydevtoken \
  -e GRANT_SUDO=yes \
  --shm-size=1g \
  caffe-cpu:pycaffe-jupyter-ssh
```

### 启动后等待服务就绪

```bash
# 查看健康状态（约 10-15 秒后变为 healthy）
docker inspect --format='{{.State.Health.Status}}' pycaffe-dev

# 实时查看启动日志
docker logs -f pycaffe-dev
```

---

## 三、获取访问凭证

如果启动时未设置 `USER_PASSWORD` 和 `JUPYTER_TOKEN`，容器会自动生成随机值并打印到日志：

```bash
docker logs pycaffe-dev 2>&1 | grep -A 15 "Container ready"
```

输出示例：

```
============================================================
  Container ready! Services managed by supervisord

  SSH access:
    ssh builder@<host> -p <mapped-port>
    Password: c889u3uuXPpnhSRY

  Jupyter access:
    URL: http://<host>:<mapped-port>/
    Token: P3HiIG6MTB4MiUv7WPxmSbUXM5x3CFrP
============================================================
```

---

## 四、连接方式

### SSH 连接

```bash
# 密码登录
ssh builder@localhost -p 2222

# 首次连接可跳过主机密钥确认
ssh -o StrictHostKeyChecking=no builder@localhost -p 2222
```

- **用户名**：`builder`
- **默认密码**：启动时自动生成（查看日志），或通过 `USER_PASSWORD` 指定
- **工作目录**：`/workspace`
- **UID**：1001（挂载卷权限匹配参考）
- **sudo**：通过 `-e GRANT_SUDO=yes` 启用无密码 sudo

### Jupyter Notebook / Lab

浏览器打开：

| 服务 | URL |
|------|-----|
| Notebook | http://localhost:8888/ |
| JupyterLab | http://localhost:8888/lab |

- **Token**：启动时自动生成，或通过 `JUPYTER_TOKEN` 指定
- 如设置了 `JUPYTER_PASSWORD`，则使用密码登录
- 工作目录：`/workspace`

---

## 五、环境变量速查

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `USER_PASSWORD` | 随机16位 | builder 用户 SSH 密码 |
| `JUPYTER_TOKEN` | 随机32位 | Jupyter 访问 Token |
| `JUPYTER_PASSWORD` | 空 | Jupyter 密码（与 Token 二选一） |
| `SSH_PUBLIC_KEY` | 空 | SSH 公钥内容，自动写入 authorized_keys |
| `GRANT_SUDO` | `no` | 设为 `yes` 允许 builder 无密码 sudo |
| `ALLOW_ROOT_SSH` | `no` | 设为 `yes` 允许 root SSH 登录 |
| `ROOT_PASSWORD` | 随机 | root 密码（需 ALLOW_ROOT_SSH=yes） |

**使用公钥登录示例：**

```bash
docker run -d \
  --name pycaffe-dev \
  -p 2222:22 -p 8888:8888 \
  -e SSH_PUBLIC_KEY="$(cat ~/.ssh/id_ed25519.pub)" \
  -e JUPYTER_TOKEN=mydevtoken \
  caffe-cpu:pycaffe-jupyter-ssh
```

---

## 六、常用操作

### 查看服务状态

```bash
docker exec pycaffe-dev supervisorctl status
```

预期输出：
```
jupyter   RUNNING   pid XX, uptime X:XX:XX
sshd      RUNNING   pid XX, uptime X:XX:XX
```

### 进入容器

```bash
# 以 builder 用户进入（推荐，命令模式自动使用 gosu 降权）
docker exec -it -u builder pycaffe-dev bash

# 以 root 进入
docker exec -it -u root pycaffe-dev bash
```

### 命令模式（不启动服务，直接执行命令）

```bash
# 以 builder 用户执行单条命令（自动 gosu 降权，环境变量已加载）
docker run --rm -it caffe-cpu:pycaffe-jupyter-ssh python -c "import pycaffe; print(pycaffe.__version__)"

# 交互式 bash
docker run --rm -it caffe-cpu:pycaffe-jupyter-ssh bash
```

### 重启服务

```bash
docker exec pycaffe-dev supervisorctl restart sshd
docker exec pycaffe-dev supervisorctl restart jupyter
```

### 停止 / 删除容器

```bash
docker stop pycaffe-dev
docker rm pycaffe-dev
```

### 安装额外 Python 包

```bash
docker exec -it pycaffe-dev pip install --break-system-packages <package-name>
```

### 手动健康检查

```bash
docker exec pycaffe-dev healthcheck.sh
```

### 运行 PyCaffe 验证

```bash
docker exec -it pycaffe-dev verify-pycaffe.sh
```

---

## 七、数据持久化

将本地目录挂载到 `/workspace`，容器销毁后数据保留：

```bash
# WSL 示例
docker run -d --name pycaffe-dev \
  -p 2222:22 -p 8888:8888 \
  -v /mnt/d/caffe-workspace:/workspace \
  -e USER_PASSWORD=caffe123 \
  -e JUPYTER_TOKEN=mydevtoken \
  -e GRANT_SUDO=yes \
  --shm-size=1g \
  caffe-cpu:pycaffe-jupyter-ssh

# Linux/Mac 示例
docker run -d --name pycaffe-dev \
  -p 2222:22 -p 8888:8888 \
  -v $HOME/caffe-workspace:/workspace \
  -e USER_PASSWORD=caffe123 \
  -e JUPYTER_TOKEN=mydevtoken \
  -e GRANT_SUDO=yes \
  caffe-cpu:pycaffe-jupyter-ssh
```

> **权限提示**：容器内 builder 用户 UID 为 1001。如遇权限问题，可在宿主机执行 `sudo chown -R 1001:1001 /path/to/caffe-workspace`，或启动时加 `--user root` 以 root 运行（不推荐）。

---

## 八、端口映射参考

| 容器端口 | 服务 | 推荐宿主机映射 | 说明 |
|---------|------|--------------|------|
| 22 | SSH | 2222 | SSH 远程连接 |
| 8888 | Jupyter | 8888 | Notebook/Lab Web 界面 |

如需修改宿主机端口，将 `-p` 左边的端口号改掉即可，例如 `-p 2223:22 -p 8889:8888`。使用 `run.sh` 脚本时端口会自动检测可用端口。

---

## 九、调试模式

不启动服务，直接进入容器排查问题：

```bash
docker run -it --rm caffe-cpu:pycaffe-jupyter-ssh bash
```

此模式自动使用 gosu 降权到 builder 用户，仅完成环境初始化和密码设置，不启动 supervisord。`LD_LIBRARY_PATH` 等环境变量通过 `/etc/profile.d/pycaffe.sh` 自动加载。

---

## 十、已知说明

- **PyCaffe 导入**：`import pycaffe` 存在上游 Python 3 + tvm-ffi 接口兼容性问题（原始 `pycaffe/Dockerfile` 同样存在），wheel 和 `.so` 文件已正确安装到 site-packages，`LD_LIBRARY_PATH` 已通过 profile.d 和 ldconfig 正确配置，等待上游修复 `_caffe.py` tvm-ffi 加载器后即可正常导入。
- **SSH 主机密钥**：每次容器启动时自动重新生成，不会复用镜像中的密钥。
- **Jupyter 配置**：运行时动态生成配置文件（`/home/builder/.jupyter/jupyter_server_config.d/runtime.py`），不会修改镜像内的静态配置。
- **命令模式权限**：使用 `docker run ... <command>` 时，entrypoint 会通过 gosu 自动从 root 降权到 builder 用户执行，避免文件权限问题。
- **构建上下文**：`vendor/.dockerignore` 已配置，构建时自动排除 `.git/`、`__pycache__/`、caffemodel 等大文件，减小构建上下文大小。

---

## 快速复制粘贴版

### 一条命令构建 + 启动 + 查看凭证

```bash
cd /mnt/d/spaces/SpecWeave/projects/xuanspace/vendor && \
bash caffe/docker/standalone/pycaffe-jupyter-ssh/build.sh && \
docker rm -f pycaffe-dev 2>/dev/null; \
docker run -d --name pycaffe-dev \
  -p 2222:22 -p 8888:8888 \
  -v /mnt/d/caffe-workspace:/workspace \
  -e USER_PASSWORD=caffe123 \
  -e JUPYTER_TOKEN=mydevtoken \
  -e GRANT_SUDO=yes \
  --shm-size=1g \
  caffe-cpu:pycaffe-jupyter-ssh && \
sleep 10 && \
echo "=== 服务状态 ===" && \
docker exec pycaffe-dev supervisorctl status && \
echo "" && \
echo "=== SSH ===" && \
echo "  ssh builder@localhost -p 2222  (密码: caffe123)" && \
echo "" && \
echo "=== Jupyter ===" && \
echo "  http://localhost:8888/?token=mydevtoken"
```
