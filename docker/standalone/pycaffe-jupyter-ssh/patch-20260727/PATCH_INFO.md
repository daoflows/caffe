# PyCaffe Jupyter SSH 镜像修复补丁

**日期**: 2026-07-27
**基础镜像**: caffe-cpu:standalone-pycaffe (Ubuntu 24.04 / Python 3.12)
**修复镜像**: caffe-cpu:pycaffe-jupyter-ssh

## 修复的 Bug

### Bug 1: Dockerfile 基础镜像错误导致 PyCaffe ABI 不兼容（严重）

**现象**: 容器启动后执行 `import caffe` 报错：
```
ImportError: dynamic module does not define module export function (PyInit__caffe)
```

**根因**: 原 Dockerfile 从 `ubuntu:26.04` 开始全新构建 PyCaffe wheel，但该构建过程与 `caffe-cpu:standalone-pycaffe` 基础镜像中的 Python 环境不匹配，导致 `_caffe.so` C 扩展的 ABI 不兼容。

**修复**: 将 Dockerfile 改为**分层扩展模式**，直接基于已验证可用的 `caffe-cpu:standalone-pycaffe` 镜像：
```dockerfile
# 修复前
FROM ubuntu:26.04 AS runtime
...（重新编译 caffe + pycaffe wheel，~15-30 分钟构建）

# 修复后
FROM caffe-cpu:standalone-pycaffe AS runtime
...（仅安装 SSH + Jupyter 层，~2-5 分钟构建）
```

**影响文件**: `Dockerfile`

---

### Bug 2: entrypoint.sh 中 `set -u` 导致容器静默崩溃（严重）

**现象**: 容器启动后只打印 banner 就以 exit code 1 退出，supervisord 未启动：
```
============================================================
  PyCaffe Jupyter SSH Container starting...
  Time: ...
  Host: ...
============================================================
```
无任何错误日志，容器状态为 `Exited (1)`。

**根因**: entrypoint.sh 使用 `set -euo pipefail`，在 source `/etc/profile.d/*.sh` 时，Ubuntu 24.04 自带的 `debuginfod.sh` 脚本引用了未定义的 `$DEBUGINFOD_URLS` 变量。在 `set -u`（nounset）模式下，未定义变量引用是 fatal error，会导致 shell 立即退出，且 `|| true` 无法捕获这种 shell 级别的致命错误。

**修复**: 在 source 系统 profile 脚本时临时禁用 nounset：
```bash
# 修复前
if [ -d /etc/profile.d ]; then
    for f in /etc/profile.d/*.sh; do
        if [ -f "$f" ] && [ "$f" != "/etc/profile.d/pycaffe.sh" ]; then
            . "$f" 2>/dev/null || true   # 无法捕获 set -u 的 fatal error
        fi
    done
fi

# 修复后
set +u  # 临时禁用 nounset
if [ -f /etc/profile.d/pycaffe.sh ]; then
    . /etc/profile.d/pycaffe.sh
fi
if [ -d /etc/profile.d ]; then
    for f in /etc/profile.d/*.sh; do
        if [ -f "$f" ] && [ "$f" != "/etc/profile.d/pycaffe.sh" ]; then
            . "$f" 2>/dev/null || true
        fi
    done
fi
set -u   # 恢复 nounset
```

**影响文件**: `entrypoint.sh`

---

### Bug 3: build.sh 构建提示过时与缺少基础镜像检查（轻微）

**现象**: build.sh 提示"首次构建可能需要 15-30 分钟"，但基于分层扩展后实际只需 2-5 分钟；缺少对基础镜像 `caffe-cpu:standalone-pycaffe` 是否存在的前置检查。

**修复**: 
- 更新构建时间提示为 2-5 分钟
- 添加基础镜像存在性检查，若不存在则给出构建指引

**影响文件**: `build.sh`

## 验证结果

| 检查项 | 状态 |
|--------|------|
| 镜像构建 | ✅ 成功（基于 standalone-pycaffe 分层扩展） |
| 容器启动 | ✅ `Up (healthy)`，supervisord 管理 sshd + jupyter |
| SSH 服务 | ✅ 端口 2222 返回 SSH-2.0-OpenSSH_9.6p1 banner |
| Jupyter HTTP | ✅ HTTP 200（带 token 可直接访问） |
| Jupyter API | ✅ `/api/status` 返回正常 JSON |
| PyCaffe 导入 | ✅ `import caffe` 正常，`caffe.Net` 可用 |
| PyCaffe 前向推理 | ✅ Conv→ReLU→Pool→FC→Softmax 全流程通过 |
| 端口冲突自动处理 | ✅ 自动检测并递增端口，有彩色 WARN 日志 |
| 健康检查 | ✅ HEALTHCHECK 通过，容器标记 healthy |

## 文件清单

| 文件 | 说明 |
|------|------|
| `Dockerfile` | 修复后的 Dockerfile（分层扩展模式） |
| `entrypoint.sh` | 修复后的入口脚本（set -u 问题修复） |
| `run.sh` | 启动脚本（端口冲突自动处理，无需修改） |
| `build.sh` | 构建脚本（更新提示+基础镜像检查） |
| `examples/pycaffe_quickstart.ipynb` | Jupyter Notebook 入门示例 |

## 使用方法

```bash
# 1. 确保基础镜像已构建
cd vendor
docker build -t caffe-cpu:standalone-pycaffe --target runtime \
  -f caffe/docker/standalone/pycaffe/Dockerfile .

# 2. 构建 Jupyter+SSH 镜像
cd caffe/docker/standalone/pycaffe-jupyter-ssh
bash build.sh

# 3. 启动容器
bash run.sh -p 2222 -j 8888 --user-password your_password --jupyter-token your_token

# 4. 访问 Jupyter
#    浏览器打开: http://localhost:8888/?token=your_token

# 5. SSH 登录
#    ssh builder@localhost -p 2222
```

## caffe-slim PyCaffe API 说明

本镜像使用的是 caffe-slim 版本，API 与原版 BVLC/Caffe 有以下差异：

| 操作 | 原版 Caffe | caffe-slim (本镜像) |
|------|-----------|---------------------|
| 创建网络 | `caffe.Net(prototxt, phase, weights)` | 同左 |
| 设置输入 | `net.blobs['data'].data[...] = arr` | `net.set_input_data('data', arr)` |
| 前向传播 | `out = net.forward()` 返回 dict | `net.forward()` 返回 None |
| 获取 blob | `net.blobs['name'].data` | `net.blob_data('name')` |
| 获取形状 | `net.blobs['name'].data.shape` | `net.blob_shape('name')` |
| 列出 blobs | `net.blobs.keys()` | `net.blob_names` |
| 图像预处理 | `caffe.io.Transformer` | 手动 numpy 预处理（见示例 notebook） |
| 设置模式 | `caffe.set_mode_cpu()` | 同左 |
| 设置随机种子 | `caffe.set_random_seed()` | 同左 |
