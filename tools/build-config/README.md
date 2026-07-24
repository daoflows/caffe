# CMake + Conan 构建配置

本目录包含 Caffe protobuf 最小化库的 CMake + Conan 构建系统配置文件。

## 安装依赖

1. 安装 cmake、conan 和 ninja

```bash
conda install -c conda-forge ninja
pip install cmake -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install conan -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 确保已安装 protobuf（[conda 环境安装指南](https://xinetzone.github.io/tao/fields/protobuf/installation.html)）。

## CMake 构建（方式二）

```bash
# 检测 Conan 环境
conan profile detect --force
# 安装依赖（指定 tools/build-config/ 为源码目录）
conan install tools/build-config/ -c tools.cmake.cmaketoolchain:generator=Ninja --build=missing
# 配置 CMake
cmake --preset conan-release
# 构建项目
cmake --build --preset conan-release
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `CMakeLists.txt` | CMake 构建配置，使用 `protobuf_generate_python` 生成 Python 代码 |
| `conanfile.py` | Conan 依赖管理，定义 `protobuf/6.30.1` 依赖 |
| `.conanrc` | Conan 本地配置，指定 conan_home 路径 |