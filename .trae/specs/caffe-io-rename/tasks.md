---
version: "1.0"
---
# PyCaffe io.py 模块重命名 - The Implementation Plan (Decomposed and Prioritized Task List)

## [x] Task 1: 重命名 io.py 为 transforms.py
- **Priority**: high
- **Depends On**: None
- **Description**: 
  - 将 `python/pycaffe/python/pycaffe/io.py` 物理重命名为 `python/pycaffe/python/pycaffe/transforms.py`
  - 使用 git mv 以保留文件历史（如在git仓库中）
  - 确认 transforms.py 内容与原 io.py 完全一致，无任何内容修改
- **Acceptance Criteria Addressed**: [AC-1]
- **Test Requirements**:
  - `programmatic` TR-1.1: 文件 transforms.py 存在于 pycaffe 包目录
  - `programmatic` TR-1.2: 文件 io.py 不再存在于 pycaffe 包目录
  - `programmatic` TR-1.3: transforms.py 文件大小和内容与原 io.py 一致（diff 为空）
- **Notes**: 不修改文件内容，仅重命名

## [x] Task 2: 更新 __init__.py 导入
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 修改 `python/pycaffe/python/pycaffe/__init__.py`
  - 将第7行 `from . import io` 改为 `from . import transforms`
  - 将第8行 `from .io import DataProcessor, Transformer, load_image, load_image_batch, resize_image, oversample` 改为 `from .transforms import DataProcessor, Transformer, load_image, load_image_batch, resize_image, oversample`
- **Acceptance Criteria Addressed**: [AC-2]
- **Test Requirements**:
  - `programmatic` TR-2.1: __init__.py 中不再包含 `.io` 字符串
  - `programmatic` TR-2.2: __init__.py 中包含 `.transforms` 的正确导入
  - `programmatic` TR-2.3: 导入的符号列表保持不变（DataProcessor, Transformer, load_image, load_image_batch, resize_image, oversample）
- **Notes**:

## [x] Task 3: 更新 pycaffe.py 导入
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 修改 `python/pycaffe/python/pycaffe/pycaffe.py`
  - 将第14行 `from . import io` 改为 `from . import transforms`
  - 检查 pycaffe.py 中是否有其他对 `io.` 的引用（当前分析中未发现，但需确认）
- **Acceptance Criteria Addressed**: [AC-2]
- **Test Requirements**:
  - `programmatic` TR-3.1: pycaffe.py 中不再包含 `from . import io`
  - `programmatic` TR-3.2: pycaffe.py 中包含 `from . import transforms`
  - `programmatic` TR-3.3: pycaffe.py 中无 `io.` 前缀的引用
- **Notes**: pycaffe.py 中只是导入模块但未直接使用 io.xxx 调用（io 被导入但未在该文件中引用其属性？需要确认）

## [x] Task 4: 更新 classifier.py 导入和引用
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 修改 `python/pycaffe/python/pycaffe/classifier.py`
  - 将第10行 `from . import io` 改为 `from . import transforms`
  - 将第32行 `self.transformer = io.Transformer(` 改为 `self.transformer = transforms.Transformer(`
  - 将第72行 `input_[ix] = io.resize_image(in_, self.image_dims)` 改为 `input_[ix] = transforms.resize_image(in_, self.image_dims)`
  - 将第76行 `input_ = io.oversample(input_, self.crop_dims)` 改为 `input_ = transforms.oversample(input_, self.crop_dims)`
- **Acceptance Criteria Addressed**: [AC-2]
- **Test Requirements**:
  - `programmatic` TR-4.1: classifier.py 中不再包含 `from . import io`
  - `programmatic` TR-4.2: classifier.py 中所有 `io.` 前缀替换为 `transforms.`
  - `programmatic` TR-4.3: 替换后代码语法正确
- **Notes**: 共3处 io.xxx 引用

## [x] Task 5: 更新 detector.py 导入和引用
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 修改 `python/pycaffe/python/pycaffe/detector.py`
  - 将第21行 `from . import io` 改为 `from . import transforms`
  - 将第44行 `self.transformer = io.Transformer(` 改为 `self.transformer = transforms.Transformer(`
  - 将第76行 `image = io.load_image(image_fname).astype(np.float32)` 改为 `image = transforms.load_image(image_fname).astype(np.float32)`
  - 将第177行 `context_crop = io.resize_image(context_crop, (crop_h, crop_w))` 改为 `context_crop = transforms.resize_image(context_crop, (crop_h, crop_w))`
- **Acceptance Criteria Addressed**: [AC-2]
- **Test Requirements**:
  - `programmatic` TR-5.1: detector.py 中不再包含 `from . import io`
  - `programmatic` TR-5.2: detector.py 中所有 `io.` 前缀替换为 `transforms.`
  - `programmatic` TR-5.3: 替换后代码语法正确
- **Notes**: 共3处 io.xxx 引用

## [x] Task 6: 更新 python/scripts/test_new_features.sh
- **Priority**: medium
- **Depends On**: Task 1
- **Description**: 
  - 修改 `python/scripts/test_new_features.sh` 中的 Python 代码
  - 将第15行 `print('Transformer:', pycaffe.io.Transformer)` 改为 `print('Transformer:', pycaffe.transforms.Transformer)`
  - 将第22行 `from pycaffe.io import resize_image, oversample, Transformer as FastTransformer` 改为 `from pycaffe.transforms import resize_image, oversample, Transformer as FastTransformer`
- **Acceptance Criteria Addressed**: [AC-3]
- **Test Requirements**:
  - `programmatic` TR-6.1: 脚本中不再有 `pycaffe.io` 引用
  - `programmatic` TR-6.2: 所有引用改为 `pycaffe.transforms`
- **Notes**:

## [x] Task 7: 更新 docker/local/conda/runtest.sh
- **Priority**: medium
- **Depends On**: Task 1
- **Description**: 
  - 修改 `docker/local/conda/runtest.sh` 中的 Python 代码
  - 将第7行 `python -c "... print('Transformer', pycaffe.io.Transformer)"` 中的 `pycaffe.io.Transformer` 改为 `pycaffe.transforms.Transformer`
  - 将第11行 `from pycaffe.io import resize_image, oversample` 改为 `from pycaffe.transforms import resize_image, oversample`
- **Acceptance Criteria Addressed**: [AC-3]
- **Test Requirements**:
  - `programmatic` TR-7.1: 脚本中不再有 `pycaffe.io` 引用
  - `programmatic` TR-7.2: 所有引用改为 `pycaffe.transforms`
- **Notes**:

## [x] Task 8: 更新 docker/local/conda/test_new_features.sh
- **Priority**: medium
- **Depends On**: Task 1
- **Description**: 
  - 修改 `docker/local/conda/test_new_features.sh` 中的 Python 代码
  - 将第14行 `print('Transformer:', pycaffe.io.Transformer)` 改为 `print('Transformer:', pycaffe.transforms.Transformer)`
  - 将第21行 `from pycaffe.io import resize_image, oversample` 改为 `from pycaffe.transforms import resize_image, oversample`
- **Acceptance Criteria Addressed**: [AC-3]
- **Test Requirements**:
  - `programmatic` TR-8.1: 脚本中不再有 `pycaffe.io` 引用
  - `programmatic` TR-8.2: 所有引用改为 `pycaffe.transforms`
- **Notes**:

## [x] Task 9: 更新 docker/modules/pycaffe/scripts/verify-parity.sh
- **Priority**: medium
- **Depends On**: Task 1
- **Description**: 
  - 修改 `docker/modules/pycaffe/scripts/verify-parity.sh` 中的 Python 代码
  - 将第352行 `from pycaffe.io import array_to_blobproto, blobproto_to_array` 改为 `from pycaffe.transforms import array_to_blobproto, blobproto_to_array`
- **Acceptance Criteria Addressed**: [AC-3]
- **Test Requirements**:
  - `programmatic` TR-9.1: 脚本中不再有 `pycaffe.io` 引用
  - `programmatic` TR-9.2: 引用改为 `pycaffe.transforms`
- **Notes**:

## [x] Task 10: 全面搜索确认无残留引用
- **Priority**: high
- **Depends On**: Tasks 2-9
- **Description**: 
  - 在 `python/pycaffe/`、`python/scripts/`、`docker/` 目录下递归搜索所有 `.py` 和 `.sh` 文件
  - 确认不再有任何对 `.io` 模块或 `pycaffe.io` 的引用（caffex/ 目录除外）
  - 特别检查是否有遗漏的引用点
- **Acceptance Criteria Addressed**: [AC-2, AC-3, AC-5]
- **Test Requirements**:
  - `programmatic` TR-10.1: grep 搜索 `from . import io`、`from .io import`、`pycaffe.io` 在目标目录下无结果（caffex/除外）
  - `programmatic` TR-10.2: grep 搜索 `io.Transformer`、`io.load_image`、`io.resize_image`、`io.oversample`、`io.DataProcessor` 在目标目录下无结果（caffex/除外）
  - `programmatic` TR-10.3: caffex/ 目录下文件未被修改
- **Notes**: 注意 `skimage.io` 是合法引用，不应被替换

## [x] Task 11: Python 导入验证测试
- **Priority**: high
- **Depends On**: Tasks 2-9
- **Description**: 
  - 编写并运行一个简单的 Python 验证脚本，确认：
    1. `import pycaffe` 成功
    2. `from pycaffe import transforms` 成功
    3. `pycaffe.transforms.Transformer` 可访问
    4. `pycaffe.transforms.DataProcessor` 可访问
    5. `pycaffe.transforms.load_image` 可访问
    6. `pycaffe.transforms.resize_image` 可访问
    7. `pycaffe.transforms.oversample` 可访问
    8. `pycaffe.transforms.blobproto_to_array` 可访问
    9. 通过 `pycaffe.Transformer` 直接访问（验证 __init__.py 重新导出正常）
    10. `import io`（标准库）和 `from pycaffe import transforms` 可以共存
- **Acceptance Criteria Addressed**: [AC-4, AC-6]
- **Test Requirements**:
  - `programmatic` TR-11.1: 所有导入无 ImportError
  - `programmatic` TR-11.2: 所有公开 API 可访问
  - `programmatic` TR-11.3: 标准库 io 与 pycaffe.transforms 命名空间不冲突
  - `human-judgement` TR-11.4: 验证代码运行无异常输出
- **Notes**: 由于 C++ 扩展模块 _caffe 可能未编译，可能需要 mock 或仅验证模块结构
