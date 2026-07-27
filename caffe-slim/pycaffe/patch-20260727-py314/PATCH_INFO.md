# PyCaffe Python 3.14+ 兼容性补丁

**日期**: 2026-07-27
**目标文件**: `caffe-slim/pycaffe/pyproject.toml`、`caffe-slim/pycaffe/build.sh`
**补丁类型**: 依赖版本约束更新
**相关镜像**: caffe-cpu:standalone-pycaffe（基于 Ubuntu 26.04）

## 修复内容

### 问题描述

`pyproject.toml` 中 `requires-python` 已设置为 `">=3.14"`，但所有运行时依赖和构建依赖的版本下限严重过时，存在以下问题：

1. **依赖版本过于陈旧**：如 `numpy>=1.7.1`（2013年版本）、`scipy>=0.13.2`、`scikit-image>=0.9.3` 等，这些旧版本不支持 Python 3.14，也不兼容 numpy 2.x ABI
2. **构建依赖不完整**：`setuptools-scm`、`ninja`、`cmake` 缺少版本下限约束
3. **缺少 typing-extensions 依赖**：Docker 构建环境中已安装但未在 pyproject.toml 中声明
4. **可选依赖过时**：test 组仍使用 `nose`（已停止维护），full 组缺少现代开发工具
5. **build.sh 注释过时**：标注 "Python 3.9+" 与实际要求不符

### 具体修改

#### pyproject.toml 修改

| 区域 | 修改前 | 修改后 |
|------|--------|--------|
| **build-system.requires** | `["scikit-build-core>=0.10", "setuptools-scm", "ninja"]` | `["scikit-build-core>=0.10", "setuptools-scm>=8.0", "ninja>=1.11", "cmake>=3.26"]` |
| **classifiers** | 无 Python 版本分类器 | 添加 `Python :: 3`、`Python :: 3.14`、`Implementation :: CPython` |
| **requires-python** | `">=3.14"` | `">=3.14"`（无变化，已正确） |
| **numpy** | `>=1.7.1` | `>=2.3` |
| **scipy** | `>=0.13.2` | `>=1.14` |
| **scikit-image** | `>=0.9.3` | `>=0.22` |
| **matplotlib** | `>=1.3.1` | `>=3.8` |
| **protobuf** | `>=3.0` | `>=4.25` |
| **h5py** | `>=2.2.0` | `>=3.10` |
| **networkx** | `>=1.8.1` | `>=3.2` |
| **Pillow** | `>=2.3.0` | `pillow>=10.0`（规范化包名） |
| **pyyaml** | `>=3.10` | `>=6.0` |
| **six** | `>=1.1.0` | `>=1.16.0` |
| **python-dateutil** | `>=1.4,<2` | `>=2.8` |
| **typing-extensions** | 不存在 | `>=4.5`（新增） |
| **optional-dependencies.test** | `["nose>=1.3.0"]` | `["pytest>=8.0", "jupyter>=1.0", "ipython>=8.18", "notebook>=7.0"]` |
| **optional-dependencies.full** | `["ipython>=3.0.0", "python-gflags>=2.0", "leveldb>=0.191"]` | `["pycaffe[test]", "pandas>=2.1", "black>=24.0", "isort>=5.13", "mypy>=1.8", "graphviz>=0.20", "python-gflags>=3.1", "leveldb>=0.20"]` |
| **tool.scikit-build** | 无 minimum-version | 添加 `minimum-version = "0.10"` |

#### build.sh 修改

- 第6行注释从 `#   - conda environment with Python 3.9+` 更新为 `#   - Python 3.14+`

## 版本选择依据

| 包 | 最低版本 | 选择理由 |
|----|---------|---------|
| numpy | >=2.3 | 首个正式支持 Python 3.14 的 numpy 版本系列（2.2 及以下最高支持到 3.13） |
| scipy | >=1.14 | 与 numpy 2.x 兼容；在 Python 3.14 上 pip 会自动选择 1.17+ 版本 |
| scikit-image | >=0.22 | 支持 numpy 2.x 和 Python 3.10+ |
| matplotlib | >=3.8 | 支持 Python 3.9+ 和 numpy 2.x |
| protobuf | >=4.25 | 4.x 系列稳定支持 Python 3.8+ |
| h5py | >=3.10 | 支持 numpy 2.x |
| networkx | >=3.2 | 支持 Python 3.9+ |
| pillow | >=10.0 | 支持 Python 3.8+ |
| setuptools-scm | >=8.0 | 支持现代 Python 版本和 PEP 621 |
| cmake | >=3.26 | 与 scikit-build-core 0.10+ 兼容 |
| ninja | >=1.11 | 稳定版本 |

## 验证结果

| 检查项 | 状态 |
|--------|------|
| TOML 语法解析（tomllib） | ✅ 通过 |
| 所有版本约束可被 packaging.requirements 解析 | ✅ 28/28 通过 |
| requires-python = ">=3.14" | ✅ 正确 |
| Python 3.14 分类器存在 | ✅ 通过 |
| 构建依赖版本约束正确 | ✅ scikit-build-core>=0.10, setuptools-scm>=8.0, ninja>=1.11, cmake>=3.26 |
| numpy 不在 build-system 中（仅为运行时依赖） | ✅ 通过 |
| 运行时依赖版本下限全部正确 | ✅ 12/12 通过 |
| 可选依赖 test 组正确 | ✅ pytest/jupyter/ipython/notebook |
| 可选依赖 full 组正确 | ✅ 包含 pycaffe[test] + 7个开发/可选包 |
| 无排除 Python 3.14 的上限约束 | ✅ 通过 |
| 仅修改 pyproject.toml 和 build.sh | ✅ 通过 |
| 总计 | ✅ 44/44 项全部通过 |

## 文件清单

| 文件 | 说明 |
|------|------|
| `pyproject.toml` | 修复后的完整 pyproject.toml（可直接替换原文件） |
| `build.sh` | 修复后的 build.sh（注释已更新） |
| `PATCH_INFO.md` | 本说明文档 |

## 使用方法

### 方式一：直接替换（推荐）

```bash
# 备份原文件
cp caffe-slim/pycaffe/pyproject.toml caffe-slim/pycaffe/pyproject.toml.bak
cp caffe-slim/pycaffe/build.sh caffe-slim/pycaffe/build.sh.bak

# 替换为修复版本
cp patch-20260727-py314/pyproject.toml caffe-slim/pycaffe/pyproject.toml
cp patch-20260727-py314/build.sh caffe-slim/pycaffe/build.sh
```

### 方式二：在 Docker 构建中使用

修复后的文件已直接更新在源码树中，后续 Docker 构建（`docker/standalone/pycaffe/Dockerfile`）将自动使用更新后的版本约束。

## 影响范围

- **caffe-slim C++ 源码**：无修改
- **CMakeLists.txt**：无修改
- **Dockerfile**：无修改（Dockerfile 中 `pip install` 的版本约束与更新后的 pyproject.toml 兼容）
- **caffex/ 目录**：无修改
- **pycaffe Python 源码**：无修改
