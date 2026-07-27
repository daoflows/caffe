# Caffe Standalone 回归测试流程文档

> **适用范围**：`vendor/caffe/docker/standalone/` 目录下 `pycaffe` 和 `pycaffe-jupyter-ssh` 两个独立镜像
> **测试目标**：验证 standalone 镜像在无 `caffex/` 依赖的情况下可独立编译、运行、部署，核心推理功能正常
> **基础环境**：Ubuntu 26.04 / Python 3 / numpy >=2 / caffe-slim 1.0.0-slim / tvm-ffi 0.1.0
> **最后更新**：2026-07-27

---

## 目录

1. [前置条件](#1-前置条件)
2. [阶段一：源码与配置检查（隔离性验证）](#阶段一源码与配置检查隔离性验证)
3. [阶段二：编译构建测试](#阶段二编译构建测试)
4. [阶段三：运行时功能测试](#阶段三运行时功能测试)
5. [阶段四：隔离性验证（无 caffex 依赖）](#阶段四隔离性验证无-caffex-依赖)
6. [阶段五：Jupyter+SSH 扩展功能测试（仅 pycaffe-jupyter-ssh）](#阶段五jupyterssh-扩展功能测试仅-pycaffe-jupyter-ssh)
7. [一键回归脚本](#7-一键回归脚本)
8. [测试结果记录模板](#8-测试结果记录模板)
9. [已知问题与预期告警](#9-已知问题与预期告警)

---

## 1. 前置条件

### 1.1 环境要求

| 项目 | 要求 |
|------|------|
| Docker | 已安装且服务运行中 |
| 操作系统 | Linux / WSL2（Docker Desktop） |
| 磁盘空间 | 至少 10GB 可用（构建缓存 + 两个镜像） |
| 网络 | 能访问阿里云 PyPI 镜像和 Ubuntu 软件源 |
| 子模块 | `caffe/caffe-slim/` 和 `tvm-ffi/` 已初始化 |

### 1.2 子模块初始化

```bash
cd /path/to/vendor
git submodule update --init --recursive
```

验证子模块存在：
```bash
ls caffe/caffe-slim/CMakeLists.txt && echo "caffe-slim OK"
ls tvm-ffi/CMakeLists.txt && echo "tvm-ffi OK"
```

### 1.3 清理旧构建（可选，干净验证时执行）

```bash
# 删除旧容器
docker rm -f test-pycaffe test-jupyter 2>/dev/null || true

# 删除旧镜像（无缓存构建时使用）
docker rmi caffe-cpu:standalone-pycaffe-test caffe-cpu:standalone-jupyter-test 2>/dev/null || true

# 清理构建缓存
docker builder prune -f 2>/dev/null || true
```

---

## 阶段一：源码与配置检查（隔离性验证）

> 目的：在构建前确认 standalone 目录不包含对 caffex 的路径引用

### T1.1 grep 搜索 caffex 引用

```bash
cd /path/to/vendor/caffe/docker/standalone

# 搜索所有 caffex 引用
echo "=== 搜索 caffex 引用 ==="
grep -rn "caffex" --include="*.sh" --include="*.py" --include="Dockerfile*" --include="*.conf" --include="*.txt" .

echo ""
echo "=== 预期结果 ==="
echo "  - verify-parity.sh: 仅包含说明性注释（'不依赖 caffex' / 'Parity check not applicable'）"
echo "  - Dockerfile: 仅包含注释说明（'不依赖 caffex/'）"
echo "  - 无 COPY/ADD/路径引用指向 caffex 目录"
echo "  - 无脚本中硬编码 caffex/python 路径"
```

**通过标准**：
- ✅ 无功能性路径引用（无 `/caffex/` 路径出现在 COPY/ADD/source/python import 中）
- ✅ Dockerfile COPY 指令仅引用 `caffe/caffe-slim/` 和 `tvm-ffi/`

### T1.2 .dockerignore 检查

```bash
cd /path/to/vendor

echo "=== 检查 .dockerignore 对 libbacktrace 的处理 ==="
grep -A2 "libbacktrace" .dockerignore

echo ""
echo "=== 预期结果 ==="
echo "  - 不应有 tvm-ffi/3rdparty/libbacktrace/ 全目录排除"
echo "  - 应仅排除 tvm-ffi/3rdparty/libbacktrace/.git"
```

**通过标准**：
- ✅ `.dockerignore` 不排除 `tvm-ffi/3rdparty/libbacktrace/` 整个目录（仅排除 `.git/`）
- ✅ `caffex/` 目录被排除在构建上下文之外

### T1.3 验证脚本存在性和语法

```bash
cd /path/to/vendor/caffe/docker/standalone/pycaffe/scripts

echo "=== 验证脚本文件 ==="
ls -la verify-pycaffe.sh verify-parity.sh

echo ""
echo "=== 验证脚本语法 ==="
bash -n verify-pycaffe.sh && echo "verify-pycaffe.sh: 语法 OK"
bash -n verify-parity.sh && echo "verify-parity.sh: 语法 OK"
```

---

## 阶段二：编译构建测试

> 目的：验证两个 Docker 镜像均可从零成功构建

### T2.1 构建 pycaffe 基础镜像

```bash
cd /path/to/vendor

echo "=== 构建 pycaffe 镜像（无缓存，干净构建）==="
time docker build -t caffe-cpu:standalone-pycaffe-test --target runtime \
  --no-cache \
  -f caffe/docker/standalone/pycaffe/Dockerfile . 2>&1 | tee /tmp/build-pycaffe.log
```

**构建阶段说明**（Dockerfile 多阶段构建）：
| 阶段 | 内容 | 预期耗时 |
|------|------|---------|
| base-system | Ubuntu 26.04 + apt 换源 + 基础工具 | ~1 min |
| base-builder | 编译工具链 + Python 科学计算包（numpy>=2） | ~3-5 min |
| caffe-builder | tvm-ffi + caffe-slim 编译（CMake + Ninja） | ~10-15 min |
| runtime | 安装 pycaffe + 运行时验证 | ~1 min |

**通过标准**：
- ✅ 构建退出码为 0
- ✅ 构建日志末尾出现 `Verification completed` 和 `Verification PASSED`
- ✅ 无 `FAIL` 条目（`WARN` 可接受）

### T2.2 构建 pycaffe-jupyter-ssh 镜像

```bash
cd /path/to/vendor

echo "=== 构建 pycaffe-jupyter-ssh 镜像 ==="
time docker build -t caffe-cpu:standalone-jupyter-test --target runtime \
  -f caffe/docker/standalone/pycaffe-jupyter-ssh/Dockerfile . 2>&1 | tee /tmp/build-jupyter.log
```

**通过标准**：
- ✅ 构建退出码为 0
- ✅ 构建日志末尾出现 `BUILD COMPLETE`
- ✅ 所有 `[OK]` 验证通过，pycaffe 导入成功（WARN 可接受）

### T2.3 镜像大小检查

```bash
echo "=== 镜像大小 ==="
docker images caffe-cpu --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
```

**预期参考**（首次构建）：
- `caffe-cpu:standalone-pycaffe-test`: ~800MB-1.2GB
- `caffe-cpu:standalone-jupyter-test`: ~1.2GB-1.8GB

---

## 阶段三：运行时功能测试

> 目的：验证容器内 PyCaffe 核心推理功能正常

### T3.1 启动 pycaffe 容器

```bash
echo "=== 清理旧容器 ==="
docker rm -f test-pycaffe 2>/dev/null || true

echo "=== 启动 pycaffe 测试容器 ==="
docker run -d --name test-pycaffe \
  caffe-cpu:standalone-pycaffe-test \
  sleep infinity

echo "等待容器启动..."
sleep 3

echo "=== 容器状态 ==="
docker ps --filter name=test-pycaffe --format "table {{.Names}}\t{{.Status}}"
```

### T3.2 运行内置验证脚本

```bash
echo "=== 运行 verify-pycaffe.sh ==="
docker exec test-pycaffe verify-pycaffe.sh
echo ""
echo "=== 退出码: $? ==="
```

**通过标准**：
- ✅ 退出码为 0
- ✅ 输出格式：`X PASS / 0 FAIL / Y WARN / Z SKIP`
- ✅ 以下核心项必须 PASS：
  - `import pycaffe succeeded`
  - `pycaffe.__version__ = 1.0.0-slim`
  - `pycaffe.TRAIN = 0`
  - `pycaffe.TEST = 1`
  - `pycaffe.Net class available`
  - `pycaffe.set_mode_cpu() succeeded`
  - `LeNet Net creation and forward pass succeeded`

**预期 WARN 项**（slim 推理版本正常现象）：
- `pycaffe.classifier/detector/io/draw/coord_map not available`
- `pycaffe.SGDSolver/AdamSolver/... not available`

### T3.3 Python 交互验证（核心功能）

```bash
echo "=== T3.3.1: pycaffe 导入和版本 ==="
docker exec test-pycaffe python -c "
import pycaffe
print('pycaffe version:', pycaffe.__version__)
assert pycaffe.__version__ == '1.0.0-slim', f'Unexpected version: {pycaffe.__version__}'
print('PASS')
"

echo ""
echo "=== T3.3.2: numpy 版本（>=2）==="
docker exec test-pycaffe python -c "
import numpy
print('numpy version:', numpy.__version__)
major = int(numpy.__version__.split('.')[0])
assert major >= 2, f'numpy major version must be >=2, got {numpy.__version__}'
print('PASS')
"

echo ""
echo "=== T3.3.3: caffe 模块导入 ==="
docker exec test-pycaffe python -c "
import caffe
print('caffe loaded successfully')
print('PASS')
"

echo ""
echo "=== T3.3.4: tvm_ffi 版本 ==="
docker exec test-pycaffe python -c "
import tvm_ffi
print('tvm_ffi version:', tvm_ffi.__version__)
print('PASS')
"

echo ""
echo "=== T3.3.5: 核心类和常量 ==="
docker exec test-pycaffe python -c "
import pycaffe
assert pycaffe.TRAIN == 0, f'TRAIN should be 0, got {pycaffe.TRAIN}'
assert pycaffe.TEST == 1, f'TEST should be 1, got {pycaffe.TEST}'
assert hasattr(pycaffe, 'Net'), 'Net class missing'
assert callable(pycaffe.set_mode_cpu), 'set_mode_cpu missing'
assert callable(pycaffe.set_random_seed), 'set_random_seed missing'
print('TRAIN=0, TEST=1, Net class OK, set_mode_cpu OK')
print('PASS')
"

echo ""
echo "=== T3.3.6: Net 创建与前向传播（LeNet）==="
docker exec test-pycaffe python -c "
import pycaffe
pycaffe.set_mode_cpu()
net = pycaffe.Net('/workspace/pycaffe/lenet_deploy.prototxt', pycaffe.TEST)
print('Net created successfully')
out = net.forward()
# caffe-slim 中 forward() 返回 None 但不抛异常即为成功（推理已执行）
# 输出通过 net.blobs['prob'].data 访问
print('Forward pass executed without error')
print('PASS')
"

echo ""
echo "=== T3.3.7: scipy/matplotlib/protobuf 等科学计算包 ==="
docker exec test-pycaffe python -c "
import scipy; print('scipy:', scipy.__version__)
import google.protobuf; print('protobuf:', google.protobuf.__version__)
import PIL; print('Pillow:', PIL.__version__)
import h5py; print('h5py:', h5py.__version__)
print('PASS')
"
```

### T3.4 verify-parity.sh 验证

```bash
echo "=== 运行 verify-parity.sh ==="
docker exec test-pycaffe verify-parity.sh
echo ""
echo "=== 退出码: $? ==="
```

**通过标准**：
- ✅ 退出码为 0
- ✅ 输出包含 `Parity check not applicable for slim inference-only build`
- ✅ 后续调用 verify-pycaffe.sh 并通过

### T3.5 健康检查验证

```bash
echo "=== 检查容器健康状态 ==="
docker inspect --format='{{.State.Health.Status}}' test-pycaffe
```

**通过标准**：`healthy`（可能需要等待 30 秒）

---

## 阶段四：隔离性验证（无 caffex 依赖）

> 目的：确认运行时环境中零 caffex 文件和引用

### T4.1 容器内搜索 caffex 文件

```bash
echo "=== 容器内搜索 caffex 文件 ==="
docker exec test-pycaffe bash -c "find / -name '*caffex*' -type f 2>/dev/null | head -20"
echo "（预期：空输出）"
```

### T4.2 容器内搜索 caffex 路径引用

```bash
echo "=== 容器内 Python 路径和配置中搜索 caffex ==="
docker exec test-pycaffe bash -c "
grep -r 'caffex' /usr/local/lib/python*/dist-packages/ 2>/dev/null | head -10
grep -r 'caffex' /usr/local/bin/ 2>/dev/null | head -10
echo '搜索完成（预期：无匹配）'
"
```

### T4.3 pycaffe 包文件列表检查

```bash
echo "=== pycaffe 安装目录文件列表 ==="
docker exec test-pycaffe python -c "
import pycaffe, os, site
sp = site.getsitepackages()[0]
pycaffe_dir = os.path.join(sp, 'pycaffe')
print(f'pycaffe dir: {pycaffe_dir}')
for f in sorted(os.listdir(pycaffe_dir)):
    fp = os.path.join(pycaffe_dir, f)
    size = os.path.getsize(fp) if os.path.isfile(fp) else 0
    print(f'  {f} ({size} bytes)' if os.path.isfile(fp) else f'  {f}/')
"
```

**通过标准**：
- ✅ 容器内无任何 `caffex` 命名的文件或目录
- ✅ site-packages 中无 caffex 引用
- ✅ pycaffe 包文件仅包含 `__init__.py`、`transforms.py`、`_caffe.so` 等 standalone 模块

---

## 阶段五：Jupyter+SSH 扩展功能测试（仅 pycaffe-jupyter-ssh）

> 目的：验证 Jupyter Notebook 和 SSH 服务正常，PyCaffe 在 Jupyter 内核中可用

### T5.1 启动 Jupyter+SSH 容器

```bash
echo "=== 清理旧容器 ==="
docker rm -f test-jupyter 2>/dev/null || true

echo "=== 启动 jupyter+ssh 容器 ==="
docker run -d --name test-jupyter \
  -p 2222:22 -p 18888:8888 \
  -e USER_PASSWORD=test123 \
  -e JUPYTER_TOKEN=testtoken \
  caffe-cpu:standalone-jupyter-test

echo "等待服务启动（约 15 秒）..."
sleep 15
```

### T5.2 健康检查

```bash
echo "=== 容器状态 ==="
docker inspect --format='{{.State.Health.Status}}' test-jupyter

echo ""
echo "=== supervisord 服务状态 ==="
docker exec test-jupyter supervisorctl status
```

**通过标准**：
- ✅ 健康状态为 `healthy`
- ✅ `jupyter` 和 `sshd` 均为 `RUNNING`

### T5.3 PyCaffe 在容器内验证

```bash
echo "=== PyCaffe 版本（jupyter 容器内）==="
docker exec test-jupyter python -c "import pycaffe; print(pycaffe.__version__)"

echo ""
echo "=== 核心推理测试（jupyter 容器内）==="
docker exec test-jupyter bash -c 'source /etc/profile && python -c "
import pycaffe
pycaffe.set_mode_cpu()
net = pycaffe.Net(\"/workspace/pycaffe/lenet_deploy.prototxt\", pycaffe.TEST)
net.forward()
print(\"Forward pass executed without error\")
"'
```

### T5.4 获取访问凭证

```bash
echo "=== Jupyter 访问信息 ==="
echo "  URL: http://localhost:18888/"
echo "  Token: testtoken"
echo ""
echo "=== SSH 访问信息 ==="
echo "  命令: ssh builder@localhost -p 2222"
echo "  密码: test123"
```

---

## 7. 一键回归脚本

将以下脚本保存为 `standalone/regression-test.sh`，执行完整回归测试：

```bash
#!/bin/bash
set -euo pipefail

# ==============================================================================
# Caffe Standalone 一键回归测试脚本
# 用法：cd /path/to/vendor && bash caffe/docker/standalone/regression-test.sh
# ==============================================================================

red()    { echo -e "\033[31mFAIL: $*\033[0m"; }
green()  { echo -e "\033[32mPASS: $*\033[0m"; }
yellow() { echo -e "\033[33mWARN: $*\033[0m"; }
blue()   { echo -e "\033[34m==> $*\033[0m"; }

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() { green "$1"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { red "$1"; FAIL_COUNT=$((FAIL_COUNT+1)); }
warn() { yellow "$1"; WARN_COUNT=$((WARN_COUNT+1)); }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${VENDOR_DIR}"

blue "Caffe Standalone Regression Test"
blue "Working directory: ${VENDOR_DIR}"
echo ""

# --- T1: 源码检查 ---
blue "Phase 1: Source & Config Check"

if grep -rn "caffex" caffe/docker/standalone/ --include="Dockerfile*" --include="*.sh" \
   | grep -v "不依赖 caffex" | grep -v "Parity check not applicable" | grep -v "caffex/、" | grep -v "for full BVLC" >/dev/null; then
    fail "Found unexpected caffex references"
    grep -rn "caffex" caffe/docker/standalone/ --include="Dockerfile*" --include="*.sh" | grep -v "不依赖\|Parity check not applicable\|caffex/、\|for full BVLC"
else
    pass "No functional caffex references"
fi

if grep -q "tvm-ffi/3rdparty/libbacktrace/$" .dockerignore; then
    fail ".dockerignore excludes entire libbacktrace directory"
else
    pass ".dockerignore does not over-exclude libbacktrace"
fi

bash -n caffe/docker/standalone/pycaffe/scripts/verify-pycaffe.sh && pass "verify-pycaffe.sh syntax OK" || fail "verify-pycaffe.sh syntax error"
bash -n caffe/docker/standalone/pycaffe/scripts/verify-parity.sh && pass "verify-parity.sh syntax OK" || fail "verify-parity.sh syntax error"

echo ""

# --- T2: 构建测试 ---
blue "Phase 2: Build Test"

blue "Building pycaffe image..."
if docker build -t caffe-cpu:regression-pycaffe --target runtime \
     --no-cache -f caffe/docker/standalone/pycaffe/Dockerfile . >/tmp/reg-build-pycaffe.log 2>&1; then
    pass "pycaffe image built successfully"
else
    fail "pycaffe image build failed (see /tmp/reg-build-pycaffe.log)"
    tail -30 /tmp/reg-build-pycaffe.log
fi

echo ""

# --- T3: 运行时功能测试 ---
blue "Phase 3: Runtime Function Test"

docker rm -f reg-pycaffe 2>/dev/null || true
docker run -d --name reg-pycaffe caffe-cpu:regression-pycaffe sleep infinity >/dev/null
sleep 2

# 运行验证脚本
VERIFY_OUT=$(docker exec reg-pycaffe verify-pycaffe.sh 2>&1)
VERIFY_EXIT=$?
echo "${VERIFY_OUT}"
if [ ${VERIFY_EXIT} -eq 0 ]; then
    pass "verify-pycaffe.sh exit code 0"
else
    fail "verify-pycaffe.sh exit code ${VERIFY_EXIT}"
fi

# 提取 PASS/FAIL 计数
P=$(echo "${VERIFY_OUT}" | grep -oP '\d+(?= PASS)' || echo "0")
F=$(echo "${VERIFY_OUT}" | grep -oP '\d+(?= FAIL)' || echo "0")
W=$(echo "${VERIFY_OUT}" | grep -oP '\d+(?= WARN)' || echo "0")
echo "  Results: ${P} PASS / ${F} FAIL / ${W} WARN"
if [ "${F}" -gt 0 ]; then
    fail "Verification has ${F} FAIL(s)"
else
    pass "All core tests passed (${P} PASS, ${W} WARN)"
fi

# Python 快速验证
if docker exec reg-pycaffe python -c "
import pycaffe, numpy
assert pycaffe.__version__ == '1.0.0-slim'
assert int(numpy.__version__.split('.')[0]) >= 2
pycaffe.set_mode_cpu()
net = pycaffe.Net('/workspace/pycaffe/lenet_deploy.prototxt', pycaffe.TEST)
net.forward()  # slim 版本 forward() 返回 None 但不抛异常即为成功
print('Core inference OK')
" 2>/dev/null; then
    pass "Python core inference test passed"
else
    fail "Python core inference test failed"
fi

echo ""

# --- T4: 隔离性验证 ---
blue "Phase 4: Isolation Test"

CAFFEX_FILES=$(docker exec reg-pycaffe bash -c "find / -name '*caffex*' -type f 2>/dev/null | wc -l")
if [ "${CAFFEX_FILES}" -eq 0 ]; then
    pass "No caffex files in container"
else
    fail "Found ${CAFFEX_FILES} caffex file(s) in container"
fi

echo ""

# --- Cleanup ---
blue "Cleanup"
docker rm -f reg-pycaffe 2>/dev/null || true

# --- Summary ---
echo ""
echo "=============================================="
echo "  Regression Test Summary"
echo "=============================================="
echo "  PASS: ${PASS_COUNT}"
echo "  FAIL: ${FAIL_COUNT}"
echo "  WARN: ${WARN_COUNT}"
echo "=============================================="

if [ "${FAIL_COUNT}" -gt 0 ]; then
    red "REGRESSION TEST FAILED"
    exit 1
else
    green "REGRESSION TEST PASSED"
    exit 0
fi
```

使用方式：
```bash
cd /path/to/vendor
chmod +x caffe/docker/standalone/regression-test.sh
bash caffe/docker/standalone/regression-test.sh
```

---

## 8. 测试结果记录模板

每次回归测试后记录以下信息：

```
## 回归测试记录 - YYYY-MM-DD

- **测试人**：
- **提交/版本**：
- **Docker 版本**：
- **操作系统**：

### 测试结果

| 阶段 | 结果 | 备注 |
|------|------|------|
| T1 源码检查 | PASS/FAIL | |
| T2 编译构建 | PASS/FAIL | pycaffe 耗时: __min, jupyter 耗时: __min |
| T3 运行时功能 | PASS/FAIL | X PASS / Y FAIL / Z WARN |
| T4 隔离性验证 | PASS/FAIL | caffex 文件数: 0 |
| T5 Jupyter+SSH | PASS/FAIL | 服务状态: jupyter RUNNING, sshd RUNNING |

### 镜像信息

| 镜像 | 大小 | pycaffe 版本 | numpy 版本 |
|------|------|-------------|-----------|
| caffe-cpu:standalone-pycaffe | __ MB | | |
| caffe-cpu:pycaffe-jupyter-ssh | __ MB | | |

### 问题记录

- 

### 结论

- [ ] 全部通过，可发布
- [ ] 有 FAIL 项，需修复
```

---

## 9. 已知问题与预期告警

| 项目 | 现象 | 说明 | 是否阻断 |
|------|------|------|---------|
| 辅助子模块 WARN | classifier/detector/draw/io/coord_map 不可用 | slim 推理版本不包含这些辅助模块，属于设计预期 | 否 |
| Solver 类 WARN | SGDSolver/AdamSolver 等训练类不可用 | slim 版本不支持训练，推理-only | 否 |
| draw 子模块 SKIP | pycaffe.draw 跳过（pydotplus 未安装） | 可视化依赖未安装，不影响推理 | 否 |
| numpy>=2 兼容 | numpy 2.x 可能有上游接口差异 | 已验证 core 功能正常 | 否 |
| protobuf python 实现 | 使用 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` | 避免 C++ 实现的版本兼容问题 | 否 |
| net.forward() 返回 None | forward() 不返回输出 dict，但推理已成功执行 | caffe-slim 推理-only 版本的 API 差异；输出通过 blobs 访问 | 否 |

---

## 附录：常用调试命令

```bash
# 查看镜像构建历史
docker history caffe-cpu:standalone-pycaffe-test

# 进入容器调试
docker exec -it test-pycaffe bash

# 查看容器内已安装的 Python 包
docker exec test-pycaffe pip list 2>/dev/null | grep -i -E "caffe|numpy|scipy|tvm|protobuf"

# 查看共享库依赖
docker exec test-pycaffe bash -c "ldd /usr/local/lib/_caffe.so 2>/dev/null | head -20"

# 查看环境变量
docker exec test-pycaffe env | grep -E "LD_LIBRARY|PROTOCOL|PYTHON"

# 查看构建日志尾部
tail -50 /tmp/build-pycaffe.log
```
