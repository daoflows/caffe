# Caffe

本项目基于 [BVLC/caffe](https://github.com/BVLC/caffe) 项目，利用 Conan 进行打包和发布。

## `caffe` 源码

`caffe_src` 来源于 [BVLC/caffe](https://github.com/BVLC/caffe)。

## 构建 caffe
find_package(Python3 COMPONENTS Development REQUIRED)
构建项目：
```bash
conda install -c boost conda-forge hdf5 crc32c openblas glog=0.0.5 gflags protobuf=3.20.3
conan profile detect --force
conan install . -c tools.cmake.cmaketoolchain:generator=Ninja --build=missing
cmake --preset conan-release
cmake --build --preset conan-release
```

将 `caffex/0.1.0` 包置于可编辑模式
```bash
conan editable add caffex
```
查看可编辑模式的包
```bash
conan editable list
```

## 测试

测试项目：
```bash
conan build hello --build=editable -c tools.cmake.cmaketoolchain:generator=Ninja
```

移除 caffex 包
```bash
conan editable remove --refs=caffex/1.0
```