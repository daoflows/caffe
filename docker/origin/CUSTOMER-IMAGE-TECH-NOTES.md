# 客户分发镜像技术备注

> **维护要点速查** | 最后更新：2026-07-27

## 一、架构概述

```
┌─────────────────────────────────────────────────────┐
│                  客户镜像 (customer)                  │
│  FROM caffe-cpu:jupyter                              │
│                                                      │
│  /opt/caffe-examples/          ← 预置Notebook（非VOLUME）│
│  /usr/local/bin/entrypoint-    ← wrapper启动脚本        │
│      customer.sh                                     │
│                                                      │
│  /workspace/                   ← VOLUME（基础镜像声明）  │
│    └── notebooks/              ← 工作目录（Jupyter根）    │
│         └── 01_caffe_forward_  ← wrapper首次启动时复制    │
│             pass.ipynb                               │
│                                                      │
│  ENTRYPOINT → tini → entrypoint-customer.sh          │
│                          ↓ exec                      │
│                       entrypoint-jupyter.sh (原始)    │
└─────────────────────────────────────────────────────┘
```

## 二、关键文件说明

| 文件 | 路径 | 职责 |
|------|------|------|
| Dockerfile.customer | `docker/origin/Dockerfile.customer` | 客户镜像构建定义 |
| entrypoint-customer.sh | `docker/origin/entrypoint-customer.sh` | 启动时自动复制Notebook的wrapper |
| build-customer.sh | `docker/origin/build-customer.sh` | 一键构建+导出+验证+打包脚本 |
| check-volumes.sh | `docker/origin/scripts/check-volumes.sh` | VOLUME前置检查工具 |
| 使用指南模板 | `docker/origin/scripts/templates/customer-guide.template.txt` | 非技术客户文档模板 |
| entrypoint模板 | `docker/origin/scripts/templates/entrypoint-wrapper.template.sh` | wrapper脚本模板 |
| Dockerfile模板 | `docker/origin/scripts/templates/Dockerfile.customer.template` | 客户Dockerfile模板 |

## 三、核心逻辑解读

### 3.1 为什么不能直接 COPY 到 /workspace/notebooks？

基础镜像 `caffe-cpu:jupyter` 中声明了 `VOLUME /workspace`。Docker 的 VOLUME 机制：

- **构建时**：Dockerfile 中向 VOLUME 路径 COPY 文件**可以成功**（文件会出现在镜像层中）
- **commit时**：`docker commit` **不会保存**运行中容器对 VOLUME 路径的文件修改
- **运行时**：如果宿主机挂载了该 VOLUME，镜像层中的文件会被复制到空卷中（仅首次）；如果不挂载，使用镜像层中的内容

**实际问题**：我们最初用 `docker cp + docker commit` 的方式将Notebook写入 `/workspace/notebooks/`，但commit后文件丢失——因为commit不保存VOLUME目录的运行时变更。

**解决路径对比**：

| 方案 | 是否可行 | 原因 |
|------|---------|------|
| docker cp + docker commit | ❌ | VOLUME目录文件不被commit保存 |
| Dockerfile COPY 到 /workspace | ✅ 可行 | 构建时COPY会写入镜像层 |
| Dockerfile COPY 到非VOLUME + wrapper | ✅ **推荐** | 更灵活，支持多Notebook，不覆盖用户文件 |

我们选择方案3，因为它支持：
- 幂等复制（不覆盖用户已修改的Notebook）
- 后续可向 `/opt/caffe-examples/` 添加更多预置文件
- 客户重置容器后Notebook自动恢复

### 3.2 entrypoint-customer.sh 工作流程

```
容器启动
   ↓
tini (PID 1，信号转发)
   ↓
entrypoint-customer.sh
   ├─ mkdir -p /workspace/notebooks
   ├─ 遍历 /opt/caffe-examples/*.ipynb
   │   ├─ 目标不存在 → cp（首次启动）
   │   └─ 目标已存在 → 跳过（不覆盖用户文件）
   ├─ chown 修正文件权限
   └─ exec /usr/local/bin/entrypoint-jupyter.sh "$@"  ← 转交原始入口
        ↓
      supervisord → jupyter + sshd
```

**关键点**：
- `set -e`：任何命令失败立即退出
- `[ ! -f "${DEST}/${fname}" ]`：幂等检查，只在文件不存在时复制
- `chown ... 2>/dev/null || true`：权限修正失败不阻止启动
- `exec` 替换当前进程（不fork子进程），确保信号（SIGTERM等）正确传递给Jupyter

### 3.3 Dockerfile.customer 关键配置

```dockerfile
FROM caffe-cpu:jupyter                    # 基于已构建的Jupyter镜像

ENV JUPYTER_TOKEN=caffe-notebook-2026     # 客户默认Token
ENV USER_PASSWORD=caffepass               # SSH密码（如需SSH访问）
ENV GRANT_SUDO=yes                        # 允许sudo

COPY *.ipynb /opt/caffe-examples/         # 预置文件到非VOLUME路径
COPY entrypoint-customer.sh /usr/local/bin/

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint-customer.sh"]
```

## 四、一键构建命令

```bash
cd docker/origin/

# 完整构建（推荐）：构建 → 导出 → 验证 → 打包ZIP
./build-customer.sh

# 快速构建（跳过验证）
./build-customer.sh --skip-verify

# 自定义Token和标签
./build-customer.sh -t v2.0 --token my-secret-token

# 仅重新打包ZIP（不重新构建镜像）
./build-customer.sh --skip-build --skip-export --skip-verify

# 查看帮助
./build-customer.sh --help
```

**产物**：`dist/Caffe-Notebook-客户分发包_*.zip`（含tar镜像+使用指南+校验文件）

## 五、常见维护场景

### 添加新的预置Notebook

1. 将新的 `.ipynb` 文件放入 `workspace/` 目录
2. 重新运行 `./build-customer.sh`
3. wrapper会自动发现 `/opt/caffe-examples/` 下所有 `.ipynb` 文件并复制
4. 如果需要支持其他文件类型，修改 entrypoint-customer.sh 中的 `*.ipynb` 通配符

### 修改默认Token/密码

```bash
# 方式1：构建时指定
./build-customer.sh --token new-token --password new-pass

# 方式2：客户启动时覆盖
docker run -d --name caffe-notebook -p 8888:8888 \
  -e JUPYTER_TOKEN=custom-token \
  caffe-cpu:customer-notebook
```

### 更新基础镜像后重新构建客户镜像

```bash
# 1. 重新构建Jupyter基础镜像
./build.sh --jupyter

# 2. 重新构建客户镜像
./build-customer.sh --no-cache
```

### VOLUME检查（构建新类型镜像时）

```bash
# 检查镜像有哪些VOLUME
./scripts/check-volumes.sh caffe-cpu:jupyter

# 检查特定路径是否受VOLUME影响
./scripts/check-volumes.sh caffe-cpu:jupyter /workspace/data /app/config
```

### 从模板创建新的客户分发产品

```bash
# 1. 复制模板
cp scripts/templates/Dockerfile.customer.template Dockerfile.newproduct
cp scripts/templates/entrypoint-wrapper.template.sh entrypoint-newproduct.sh

# 2. 修改模板变量（搜索 __ 替换为实际值）
#    __PRODUCT__ → newproduct
#    __BASE_IMAGE__ → your-base-image:tag
#    __ORIGINAL_ENTRYPOINT__ → 原始entrypoint路径
#    等等...

# 3. 参考 build-customer.sh 创建对应的构建脚本
```

## 六、验证清单

分发包发布前确认：

- [ ] 镜像能正常启动：`docker run -d -p 8888:8888 caffe-cpu:customer-notebook`
- [ ] Jupyter可访问：curl返回200/302
- [ ] Notebook自动出现在 `/workspace/notebooks/`
- [ ] Caffe可正常导入：`docker exec <container> python3 -c "import caffe"`
- [ ] Token正确：`caffe-notebook-2026`
- [ ] tar文件SHA256校验通过
- [ ] ZIP包能在客户机器上加载（如有条件请实际测试）
- [ ] 使用指南中的命令与实际配置一致（Token、端口、镜像名）

## 七、排错速查

| 问题 | 排查命令 | 常见原因 |
|------|---------|---------|
| Notebook文件不存在 | `docker exec <c> ls /workspace/notebooks/` | entrypoint没执行；检查Dockerfile ENTRYPOINT是否正确 |
| Jupyter无法访问 | `docker logs <c>` | 等待时间不够；端口映射错误；Token不对 |
| 权限被拒绝 | `docker exec <c> ls -la /workspace/notebooks/` | chown失败；检查OWNER_USER是否与基础镜像用户一致 |
| 客户加载后镜像名不对 | `docker images \| grep caffe` | tar中的镜像名是 `caffe-cpu:customer-notebook`，客户需要用这个名字 |
| ZIP解压后中文文件名乱码 | 用7-Zip或WinRAR解压 | Windows自带解压可能对UTF-8文件名支持不好 |
