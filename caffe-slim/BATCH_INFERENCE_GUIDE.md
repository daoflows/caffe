# Caffe-Slim 批量推理使用指南

本指南详细说明如何使用 `pycaffe` API 进行批量推理，涵盖环境准备、API 详解、脚本使用、自定义模型接入和结果导出等全流程内容。

---

## 目录

1. [前置条件](#前置条件)
2. [快速开始](#快速开始)
3. [核心 API 详解](#核心-api-详解)
4. [示例脚本逐段解析](#示例脚本逐段解析)
5. [自定义模型推理](#自定义模型推理)
6. [推理结果导出](#推理结果导出)
7. [预处理与 Transformer 使用](#预处理与-transformer-使用)
8. [常见问题](#常见问题)

---

## 前置条件

### 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | ≥ 3.14 | 项目强制要求 |
| NumPy | ≥ 2.3 | 张量数据处理 |
| SciPy | ≥ 1.14 | 可选，图像处理辅助 |
| pycaffe | 已编译 | caffe-slim Python 绑定 |
| caffeproto | 已编译 | protobuf Python 绑定 |

### 编译安装

确保已在 caffe-slim 目录下完成编译安装：

```bash
cd d:\spaces\SpecWeave\projects\xuanspace\vendor\caffe\caffe-slim\pycaffe
pip install -e .
```

---

## 快速开始

### 运行示例脚本

```bash
cd d:\spaces\SpecWeave\projects\xuanspace\vendor\caffe\caffe-slim
python batch_inference_demo.py
```

### 预期输出

```
======================================================================
Caffe-Slim 批量推理演示
======================================================================

[INFO] Caffe 版本: 1.0.0-slim
[INFO] 使用设备: CPU

[INFO] 正在加载网络: .../lenet_deploy.prototxt
[INFO] 网络结构加载完成
  - 输入 Blobs: ['data']
  - 输出 Blobs: ['prob']
  - 输入 'data' 默认形状: (64, 1, 28, 28)
  - 输出 'prob' 默认形状: (64, 10)

[INFO] 准备 100 个随机输入样本...
[INFO] 开始批量推理...
[INFO] 推理完成! 耗时: XX.XX ms
  - 吞吐量: XXX.XX samples/s
...
```

---

## 核心 API 详解

### 1. 初始化网络

```python
import pycaffe
from caffeproto.caffe_pb2 import TEST, TRAIN

# 方式1：仅加载网络结构（权重随机初始化，用于测试）
net = pycaffe.Net('deploy.prototxt', TEST)

# 方式2：加载网络结构 + 预训练权重
net = pycaffe.Net('deploy.prototxt', TEST, weights='model.caffemodel')
```

**参数说明：**
- `deploy.prototxt`: 网络部署配置文件路径（必须包含 Input 层，不能有 Data 层）
- `TEST`: 推理阶段（`TRAIN=0`, `TEST=1`），推理时必须用 `TEST`
- `weights`: 可选，`.caffemodel` 预训练权重文件路径

### 2. 设置计算设备

```python
pycaffe.set_mode_cpu()       # CPU 模式（caffe-slim 仅支持 CPU）
pycaffe.set_random_seed(42)  # 设置随机种子（可复现）
```

### 3. 网络属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `net.inputs` | `list[str]` | 输入 blob 名称列表 |
| `net.outputs` | `list[str]` | 输出 blob 名称列表 |
| `net.blobs` | `OrderedDict` | 所有 blob 的字典，key 为 blob 名称 |
| `net.blobs[name].data` | `numpy.ndarray` | blob 的数据（NCHW 格式） |
| `net.blobs[name].shape` | `tuple` | blob 的形状 |
| `net.layers` | `list` | 网络层列表 |
| `net.layer_dict` | `OrderedDict` | 按名称索引的网络层字典 |

### 4. 前向传播

#### 单次推理（单 batch）

```python
# input_data 形状必须与网络输入 blob 形状完全匹配（包含 batch_size）
input_blob = net.inputs[0]
outputs = net.forward(**{input_blob: input_data})

# 获取结果
output_blob = net.outputs[0]
predictions = outputs[output_blob]
```

#### 批量推理（自动分批）⭐

```python
# num_samples 可以是任意数量，forward_all 自动按网络 batch_size 分批
outputs = net.forward_all(**{input_blob: input_data})
predictions = outputs[output_blob]  # 形状: (num_samples, num_classes)
```

**`forward_all` 关键特性：**
- 自动分批：将输入数据按网络定义的 batch_size 拆分
- 自动 padding：最后一个不足 batch_size 的 batch 自动补零
- 自动截断：返回结果时自动去除 padding 部分
- 返回完整结果：所有样本的输出拼接为一个完整的 ndarray

### 5. Blob 数据格式

Caffe 使用 **NCHW** 格式存储张量：
- **N**: Batch 维度（样本数量）
- **C**: Channel 维度（通道数，如 RGB=3，灰度=1）
- **H**: Height（高度）
- **W**: Width（宽度）

```python
# 输入形状示例
# 灰度图 MNIST: (N, 1, 28, 28)
# RGB ImageNet: (N, 3, 224, 224)
```

---

## 示例脚本逐段解析

[batch_inference_demo.py](file:///d:/spaces/SpecWeave/projects/xuanspace/vendor/caffe/caffe-slim/batch_inference_demo.py) 的关键代码段：

### 1. 路径设置

```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'pycaffe', 'python'))
```
将 `pycaffe/python` 加入 Python 路径，确保能找到 `pycaffe` 和 `caffeproto` 模块。

### 2. 网络加载与信息打印

```python
net = pycaffe.Net(LENET_DEPLOY_PROTOTXT, TEST)
print(f"输入 Blobs: {net.inputs}")
print(f"输出 Blobs: {net.outputs}")
```

### 3. 输入数据准备

```python
num_samples = 100
C, H, W = input_shape[1], input_shape[2], input_shape[3]
input_data = np.random.rand(num_samples, C, H, W).astype(np.float32)
```
生成 100 个随机灰度图像作为测试输入，形状为 `(100, 1, 28, 28)`。

### 4. 批量推理执行

```python
outputs = net.forward_all(**{input_blob: input_data})
predictions = outputs[output_blob]
```
`forward_all` 自动将 100 个样本分为两批（64+36）执行推理，返回形状为 `(100, 10)` 的概率矩阵。

### 5. 结果解析

```python
predicted_classes = predictions.argmax(axis=1)  # 每个样本的预测类别
predicted_probs = predictions.max(axis=1)        # 每个样本的预测置信度
```

---

## 自定义模型推理

### 步骤 1: 准备 deploy.prototxt

确保您的模型有 deploy 版本的 prototxt：

1. **移除训练层**：删除所有 `Data`、`Loss`（如 `SoftmaxWithLoss`）、`Accuracy` 层
2. **添加 Input 层**：在网络开头添加 Input 层指定输入形状

```protobuf
layer {
  name: "data"
  type: "Input"
  top: "data"
  input_param { shape: { dim: 1 dim: 3 dim: 224 dim: 224 } }
}
# dim 顺序: N C H W
# 注意：这里的 N 是单 batch 大小，forward_all 会自动处理任意数量样本
```

3. **添加输出层**：确保最后有 `Softmax` 层输出概率（如果是分类模型）

```protobuf
layer {
  name: "prob"
  type: "Softmax"
  bottom: "fc8"
  top: "prob"
}
```

### 步骤 2: 加载预训练模型

```python
net = pycaffe.Net(
    'your_model_deploy.prototxt',
    TEST,
    weights='your_model.caffemodel'
)
```

### 步骤 3: 准备输入数据

```python
# 根据您的模型输入形状调整
input_blob = net.inputs[0]
N, C, H, W = net.blobs[input_blob].data.shape
print(f"模型期望输入形状: (N, {C}, {H}, {W})")

# 准备您的数据（必须是 NCHW 格式，float32 类型）
# 假设有 50 张 RGB 图片
images = load_your_images(...)  # 形状应为 (50, 3, 224, 224)
images = images.astype(np.float32)

# 执行预处理（减均值、缩放等，见下一节）
```

### 步骤 4: 执行推理

```python
outputs = net.forward_all(**{input_blob: images})
prob = outputs[net.outputs[0]]  # (50, num_classes)
```

---

## 推理结果导出

### 导出为 NumPy 文件（.npy/.npz）

```python
# 保存概率矩阵
np.save('predictions_prob.npy', predictions)

# 保存多个数组
np.savez('inference_results.npz',
         probabilities=predictions,
         predicted_classes=predicted_classes,
         predicted_probs=predicted_probs)

# 加载
results = np.load('inference_results.npz')
print(results['predicted_classes'])
```

### 导出为 CSV 文件

```python
import csv

# 方式1：使用 csv 模块
with open('predictions.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['sample_id', 'predicted_class', 'confidence'] + 
                    [f'class_{i}_prob' for i in range(predictions.shape[1])])
    for i in range(num_samples):
        row = [i, predicted_classes[i], f'{predicted_probs[i]:.6f}']
        row.extend([f'{p:.6f}' for p in predictions[i]])
        writer.writerow(row)

# 方式2：使用 pandas（如果已安装）
import pandas as pd
df = pd.DataFrame(predictions, columns=[f'class_{i}' for i in range(10)])
df['predicted_class'] = predicted_classes
df['confidence'] = predicted_probs
df.to_csv('predictions_pandas.csv', index_label='sample_id')
```

### 导出为 JSON 文件

```python
import json

results = {
    'model': 'lenet',
    'num_samples': int(num_samples),
    'input_shape': list(input_shape),
    'predictions': [
        {
            'sample_id': int(i),
            'predicted_class': int(predicted_classes[i]),
            'confidence': float(predicted_probs[i]),
            'probabilities': [float(p) for p in predictions[i]]
        }
        for i in range(num_samples)
    ]
}

with open('predictions.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
```

---

## 预处理与 Transformer 使用

对于真实图像数据，使用 `pycaffe.transforms.Transformer` 进行预处理。参考 [classifier.py](file:///d:/spaces/SpecWeave/projects/xuanspace/vendor/caffe/caffe-slim/pycaffe/python/pycaffe/classifier.py) 的用法：

### Transformer 初始化

```python
from pycaffe import transforms

in_ = net.inputs[0]
transformer = transforms.Transformer({in_: net.blobs[in_].data.shape})
```

### 常用预处理设置

```python
# 1. 通道转置：HWC (numpy/OpenCV格式) -> CHW (Caffe格式)
transformer.set_transpose(in_, (2, 0, 1))

# 2. 减去均值（可以是单个值或数组）
mean = np.array([104.00698793, 116.66876762, 122.67891434])  # BGR 均值 (ImageNet)
transformer.set_mean(in_, mean)

# 3. 输入缩放：将像素值从 [0,255] 缩放到 [0,1] 或其他范围
transformer.set_input_scale(in_, 1.0 / 255.0)

# 4. Raw scale：如果输入是 [0,1] 范围，缩放到 [0,255]
transformer.set_raw_scale(in_, 255.0)

# 5. 通道交换：RGB -> BGR (Caffe 默认使用 BGR)
transformer.set_channel_swap(in_, (2, 1, 0))
```

### 单张图像预处理

```python
# 假设 image 是通过 PIL/OpenCV 读取的 HWC 格式 BGR 图像
processed = transformer.preprocess(in_, image)
# processed 形状: (C, H, W)，已完成转置、减均值、缩放等操作
```

### 批量图像预处理

```python
caffe_in = np.zeros((num_samples, C, H, W), dtype=np.float32)
for i in range(num_samples):
    img = load_and_resize_image(images[i])  # HWC 格式
    caffe_in[i] = transformer.preprocess(in_, img)

outputs = net.forward_all(**{in_: caffe_in})
```

### 完整图像分类示例

参考 `Classifier` 类的简化用法：

```python
from pycaffe import transforms

def classify_images(net, images, oversample=False):
    """
    批量分类图像
    
    Args:
        net: 已加载的 pycaffe.Net
        images: list of HWC ndarrays (BGR格式，值域 [0,255])
        oversample: 是否使用 10-crop 测试增强
    
    Returns:
        predictions: (N, C) 概率矩阵
    """
    in_ = net.inputs[0]
    input_shape = net.blobs[in_].data.shape
    crop_dims = np.array(input_shape[2:])  # (H, W)
    
    # Resize 到统一尺寸
    resized = np.zeros((len(images), crop_dims[0], crop_dims[1], images[0].shape[2]),
                       dtype=np.float32)
    for i, img in enumerate(images):
        resized[i] = transforms.resize_image(img, crop_dims)
    
    if oversample:
        # 10-crop: 4个角 + 中心 + 镜像翻转
        crops = transforms.oversample(resized, crop_dims)
    else:
        # 中心裁剪
        center = np.array(crop_dims) / 2.0
        crop = np.tile(center, (1, 2))[0] + np.concatenate([
            -crop_dims / 2.0, crop_dims / 2.0
        ]).astype(int)
        crops = resized[:, crop[0]:crop[2], crop[1]:crop[3], :]
    
    # Preprocess
    caffe_in = np.zeros(np.array(crops.shape)[[0, 3, 1, 2]], dtype=np.float32)
    for i, crop in enumerate(crops):
        caffe_in[i] = transformer.preprocess(in_, crop)
    
    # Forward
    out = net.forward_all(**{in_: caffe_in})
    predictions = out[net.outputs[0]]
    
    if oversample:
        # 对 10 个 crop 的预测取平均
        predictions = predictions.reshape((len(predictions) // 10, 10, -1))
        predictions = predictions.mean(axis=1)
    
    return predictions
```

---

## 常见问题

### Q1: 报错 "Input blob arguments do not match net inputs"

**原因**：传入 `forward`/`forward_all` 的 kwargs 与网络输入 blob 名称不匹配。

**解决**：检查 `net.inputs` 获取正确的输入 blob 名称：
```python
print("输入 blob 名称:", net.inputs)
# 使用正确的名称:
outputs = net.forward_all(**{net.inputs[0]: data})
```

### Q2: 报错 "Input is not batch sized" 或形状不匹配

**原因**：输入数据的 batch 维度与网络期望不匹配，或数据形状不是 NCHW。

**解决**：
- 确保输入是 4 维数组：`(N, C, H, W)`
- 确保 C/H/W 与网络定义一致：
```python
expected_shape = net.blobs[net.inputs[0]].shape
print(f"期望形状: {expected_shape}")
print(f"实际形状: {data.shape}")
```
- `forward_all` 不要求 N 与 batch_size 一致，但 C/H/W 必须完全匹配

### Q3: 报错 "Could not open file"

**原因**：prototxt 或 caffemodel 文件路径错误。

**解决**：使用绝对路径，或检查相对路径是否正确：
```python
import os
prototxt_path = os.path.abspath('deploy.prototxt')
print(f"文件是否存在: {os.path.exists(prototxt_path)}")
```

### Q4: 输出概率和不为 1.0

**原因**：网络最后没有 Softmax 层，输出的是 logits 而非概率。

**解决**：
1. 在 deploy.prototxt 最后添加 Softmax 层
2. 或手动计算 softmax：
```python
def softmax(x, axis=1):
    e_x = np.exp(x - x.max(axis=axis, keepdims=True))
    return e_x / e_x.sum(axis=axis, keepdims=True)
prob = softmax(outputs[net.outputs[0]])
```

### Q5: 如何获取中间层输出？

**解决**：使用 `blobs` 参数指定要提取的中间层：
```python
outputs = net.forward_all(blobs=['conv1', 'pool1', 'fc7'], **{input_blob: data})
conv1_features = outputs['conv1']  # 第一层卷积输出
fc7_features = outputs['fc7']      # 全连接层特征
```

### Q6: `forward_all` 如何处理非整除 batch_size？

**回答**：`forward_all` 内部的 `_batch` 生成器会：
1. 先输出若干完整 batch（floor(N / batch_size) 个）
2. 如果有余数（remainder = N % batch_size > 0），则创建一个 padded batch：
   - 前 remainder 个样本是真实数据
   - 后 (batch_size - remainder) 个样本是零填充
3. 推理完成后自动截断结果，只返回前 N 个样本的输出

因此，**输入样本数量可以是任意正整数**，不需要自己对齐 batch_size。

### Q7: 如何进行单张图像推理？

**回答**：使用 `forward` 并确保 batch 维度为 1：
```python
single_image = np.random.rand(1, C, H, W).astype(np.float32)
outputs = net.forward(**{input_blob: single_image})
prob = outputs[output_blob][0]  # 取第一个样本的结果
```

或者仍然使用 `forward_all`（传入 1 个样本也可以）。

---

## API 速查表

| 操作 | 代码 |
|------|------|
| 设置 CPU 模式 | `pycaffe.set_mode_cpu()` |
| 加载网络（无权重） | `net = pycaffe.Net(prototxt, TEST)` |
| 加载网络（带权重） | `net = pycaffe.Net(prototxt, TEST, weights=caffemodel)` |
| 获取输入名称 | `net.inputs` |
| 获取输出名称 | `net.outputs` |
| 获取 blob 形状 | `net.blobs[name].shape` |
| 获取 blob 数据 | `net.blobs[name].data` (numpy array) |
| 单次前向传播 | `net.forward(**{input: data})` |
| 批量前向传播 | `net.forward_all(**{input: data})` |
| 提取中间层 | `net.forward_all(blobs=['fc7'], **{input: data})` |
| 创建 Transformer | `transforms.Transformer({input: shape})` |
| 设置转置 | `transformer.set_transpose(in_, (2,0,1))` |
| 设置均值 | `transformer.set_mean(in_, mean_array)` |
| 设置缩放 | `transformer.set_input_scale(in_, scale)` |
| 设置通道交换 | `transformer.set_channel_swap(in_, (2,1,0))` |
| 预处理图像 | `transformer.preprocess(in_, hwc_image)` |
| Resize 图像 | `transforms.resize_image(img, (H, W))` |
| 10-crop 增强 | `transforms.oversample(images, (H, W))` |
