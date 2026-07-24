# 最小化 caffe protobuf 库

参考：[caffe-proto](https://github.com/daoflows/caffe)

创建最小化的 caffe protobuf 库文件。

## 安装依赖

1. 在 [conda 环境中安装 protobuf](https://xinetzone.github.io/tao/fields/protobuf/installation.html)。

```bash
conda create -n proto-env python=3.14
conda activate proto-env
conda install -c conda-forge libprotobuf
pip install protobuf -i https://pypi.tuna.tsinghua.edu.cn/simple
```

2. CMake 构建需要额外安装 cmake、conan 和 ninja，详见 [tools/build-config/README.md](tools/build-config/README.md)。

## 生成 Python 代码

### 方式一：快速生成（推荐）

使用内置的 Python 生成脚本（自动检查版本一致性）：

```bash
python caffe-slim/scripts/gen_proto.py
```

脚本会自动：查找 protoc → 检查版本一致性 → 编译 proto → 验证生成代码。

### 方式二：CMake 构建

详见 [tools/build-config/README.md](tools/build-config/README.md)。

### 方式三：直接调用 protoc

```bash
protoc --proto_path=caffe-slim/protos --python_out=caffe-slim/caffeproto caffe-slim/protos/caffe.proto
```

## 添加新算子（四步法）

详见 [docs/adding-operators.md](docs/adding-operators.md)。