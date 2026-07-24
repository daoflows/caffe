# PyCaffe 独立 Docker 镜像

基于 `ubuntu:26.04`，仅使用 `caffe-slim/` 目录（含 C++ 源码、头文件、pycaffe、caffeproto）和 `tvm-ffi/` 子模块，从零构建 PyCaffe wheel 镜像。不依赖 `caffex/`、`python-module` 或任何内部预构建镜像�?
## 文件结构

```
docker/standalone/pycaffe/
├── CMakeLists.txt          # Docker 构建入口（cmake --build build --target all�?├── Dockerfile              # 4 阶段镜像定义
├── README.md               # 本文�?└── scripts/
    └── verify-pycaffe.sh   # PyCaffe 导入验证脚本
```

## 构建流水�?
```
base-system �?base-builder �?pycaffe-builder �?runtime
  (apt换源)    (工具�?Py)   (CMake+Ninja)   (wheel安装+验证)
```

| 阶段 | 基础镜像 | 职责 |
|------|----------|------|
| `base-system` | `ubuntu:26.04` | 阿里云镜像源、CA 证书、基础工具 |
| `base-builder` | `base-system` | gcc/cmake/ninja/protobuf/openblas + Python 科学计算包（numpy/scipy/matplotlib 等） |
| `pycaffe-builder` | `base-builder` | 复制 `caffe-slim/` + `tvm-ffi/`，通过 scikit-build-core 驱动 CMake+Ninja 编译 caffe_core �?_caffe.so，打�?wheel |
| `runtime` | `base-builder` | 安装 wheel，验�?`import pycaffe`，HEALTHCHECK |

## 自包含编译原�?
`caffe-slim/pycaffe/CMakeLists.txt` 一站式完成�?
1. 编译 `caffe_core` 静态库（`caffe-slim/src/caffe/*.cpp`�?2. 编译 `_caffe.so` 共享库（`caffe-slim/pycaffe/caffe-slim/pycaffe/_caffe.cpp`�?3. 打包 `tvm_ffi` 共享库到 wheel �?
整个过程�?`scikit-build-core` 驱动，无需预先编译 Caffe 库�?
## 构建

```bash
cd vendor

# 配置
cmake -B build -S caffe/docker/standalone/pycaffe

# 构建 + 验证
cmake --build build --target all

# 清理
cmake --build build --target clean
```

或直接使�?Docker�?
```bash
cd vendor
docker build -t caffe-cpu:standalone-pycaffe --target runtime \
  -f caffe/docker/standalone/pycaffe/Dockerfile .
```

## 验证

```bash
# 导入验证
docker run --rm caffe-cpu:standalone-pycaffe \
  python -c "import pycaffe; print(pycaffe.version)"

# 完整验证
docker run --rm caffe-cpu:standalone-pycaffe verify-pycaffe.sh
```