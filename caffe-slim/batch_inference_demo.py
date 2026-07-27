#!/usr/bin/env python3
"""Caffe-Slim 批量推理示例脚本 — 使用 MNIST 预训练权重

演示如何使用 caffe-slim Python API (TVM FFI) 加载预训练 LeNet 模型，
在 MNIST 测试集上进行批量推理并评估分类准确率。

Usage:
    python batch_inference_demo.py
"""

import os
import sys
import time
import warnings
import numpy as np

warnings.filterwarnings("ignore", message=".*does not annotate the following reflected field.*")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAFFE_SLIM_DIR = SCRIPT_DIR

sys.path.insert(0, os.path.join(CAFFE_SLIM_DIR, 'python'))

import caffe

LENET_DEPLOY_PROTOTXT = os.path.join(CAFFE_SLIM_DIR, 'pycaffe', 'lenet_deploy.prototxt')
LENET_WEIGHTS = os.path.join(CAFFE_SLIM_DIR, 'pycaffe', 'lenet_iter_10000.caffemodel')
MNIST_TEST_NPZ = os.path.join(CAFFE_SLIM_DIR, 'data', 'mnist', 'mnist_test.npz')


def forward_all(net, input_blob, input_data):
    """批量推理：自动分批处理输入数据。

    Parameters
    ----------
    net : caffe.Net
        已加载的 Caffe 网络
    input_blob : str
        输入 blob 名称
    input_data : np.ndarray
        输入数据，形状 (N, C, H, W)，dtype float32

    Returns
    -------
    outputs : dict
        {output_blob_name: np.ndarray} 输出字典
    """
    num_samples = input_data.shape[0]
    batch_size = net.blob_shape(input_blob)[0]
    output_blob = net.outputs[0]
    output_channels = net.blob_shape(output_blob)[1]

    all_outputs = np.zeros((num_samples, output_channels), dtype=np.float32)

    num_batches = (num_samples + batch_size - 1) // batch_size

    for b in range(num_batches):
        start_idx = b * batch_size
        end_idx = min(start_idx + batch_size, num_samples)
        actual_batch = end_idx - start_idx

        batch_data = np.zeros((batch_size,) + input_data.shape[1:], dtype=np.float32)
        batch_data[:actual_batch] = input_data[start_idx:end_idx]

        net.set_input_data(input_blob, batch_data)
        net.forward()

        out = net.blob_data(output_blob)
        all_outputs[start_idx:end_idx] = np.array(out[:actual_batch], copy=True)

    return {output_blob: all_outputs}


def preprocess_mnist(images):
    """预处理 MNIST 图像为 Caffe 输入格式。

    Caffe LeNet 训练时使用 scale=0.00390625 (1/256) 将 [0,255] 映射到 [0,1)。
    输入形状: (N, 28, 28) uint8 -> (N, 1, 28, 28) float32
    """
    processed = images.astype(np.float32) * (1.0 / 256.0)
    processed = processed[:, np.newaxis, :, :]
    return processed


def main():
    print("=" * 70)
    print("Caffe-Slim LeNet-MNIST 预训练模型推理演示")
    print("=" * 70)

    print(f"\n[INFO] Python 版本: {sys.version}")
    print(f"[INFO] NumPy 版本: {np.__version__}")

    # 检查权重文件
    if not os.path.exists(LENET_WEIGHTS):
        print(f"\n[ERROR] 未找到预训练权重文件: {LENET_WEIGHTS}")
        print("  请先运行 download_mnist.py 下载模型权重")
        return 1

    print(f"\n[INFO] 预训练权重: {LENET_WEIGHTS} ({os.path.getsize(LENET_WEIGHTS)} bytes)")

    # 检查 MNIST 数据
    if not os.path.exists(MNIST_TEST_NPZ):
        print(f"\n[ERROR] 未找到 MNIST 测试数据: {MNIST_TEST_NPZ}")
        print("  请先运行 download_mnist.py 下载测试数据")
        return 1

    caffe.set_mode_cpu()
    print(f"[INFO] Caffe 版本: {caffe.version()}")
    print(f"[INFO] 使用设备: CPU")

    # 加载预训练模型
    print(f"\n[INFO] 正在加载网络和预训练权重...")
    print(f"  - prototxt: {LENET_DEPLOY_PROTOTXT}")
    print(f"  - weights:  {LENET_WEIGHTS}")
    net = caffe.Net(LENET_DEPLOY_PROTOTXT, caffe.TEST, weights=LENET_WEIGHTS)

    input_blob = net.inputs[0]
    output_blob = net.outputs[0]
    input_shape = net.blob_shape(input_blob)
    output_shape = net.blob_shape(output_blob)
    batch_size = input_shape[0]

    print(f"\n[INFO] 网络加载完成")
    print(f"  - 输入 Blobs: {net.inputs}")
    print(f"  - 输出 Blobs: {net.outputs}")
    print(f"  - 输入 '{input_blob}' 形状: {input_shape}")
    print(f"  - 输出 '{output_blob}' 形状: {output_shape}")

    # 加载 MNIST 测试数据
    print(f"\n[INFO] 加载 MNIST 测试数据: {MNIST_TEST_NPZ}")
    mnist_data = np.load(MNIST_TEST_NPZ)
    test_images = mnist_data['images']
    test_labels = mnist_data['labels']
    print(f"  - 测试图像: {test_images.shape}, dtype={test_images.dtype}, range=[{test_images.min()}, {test_images.max()}]")
    print(f"  - 测试标签: {test_labels.shape}, dtype={test_labels.dtype}, classes={np.unique(test_labels)}")

    # 预处理
    num_samples = len(test_images)
    input_data = preprocess_mnist(test_images)
    print(f"  - 预处理后: {input_data.shape}, dtype={input_data.dtype}, range=[{input_data.min():.6f}, {input_data.max():.6f}]")

    # 批量推理
    print(f"\n[INFO] 开始批量推理 (网络 batch_size={batch_size}, 总样本数={num_samples})...")
    start_time = time.perf_counter()

    outputs = forward_all(net, input_blob, input_data)

    elapsed = time.perf_counter() - start_time
    predictions = outputs[output_blob]

    print(f"[INFO] 推理完成! 耗时: {elapsed*1000:.2f} ms")
    print(f"  - 吞吐量: {num_samples / elapsed:.2f} samples/s")

    # 分析结果
    print("\n" + "=" * 70)
    print("推理结果分析")
    print("=" * 70)
    print(f"\n输出 Blob '{output_blob}' 形状: {predictions.shape}")

    print("\n--- 概率统计 ---")
    print(f"  全局最小值: {predictions.min():.6f}")
    print(f"  全局最大值: {predictions.max():.6f}")
    prob_sums = predictions.sum(axis=1)
    print(f"  概率和范围: [{prob_sums.min():.6f}, {prob_sums.max():.6f}]")
    print(f"  是否全部 ≈1.0: {np.allclose(prob_sums, 1.0)}")

    # 计算准确率
    predicted_classes = predictions.argmax(axis=1)
    predicted_probs = predictions.max(axis=1)
    correct = (predicted_classes == test_labels).sum()
    accuracy = correct / num_samples * 100

    print(f"\n--- 分类准确率 ---")
    print(f"  正确分类: {correct}/{num_samples}")
    print(f"  总体准确率: {accuracy:.2f}%")

    # 逐类别准确率
    print(f"\n--- 逐类别准确率 ---")
    print(f"  {'数字':<6} {'样本数':<8} {'正确数':<8} {'准确率':<10} {'平均置信度':<12}")
    print("  " + "-" * 50)
    for digit in range(10):
        mask = test_labels == digit
        total_d = mask.sum()
        correct_d = ((predicted_classes == digit) & mask).sum()
        avg_conf = predictions[mask, digit].mean()
        acc_d = correct_d / total_d * 100 if total_d > 0 else 0
        print(f"  {digit:<6} {total_d:<8} {correct_d:<8} {acc_d:<10.2f}% {avg_conf:<12.6f}")

    # 混淆矩阵信息
    print(f"\n--- 错误分析 (前 20 个错误样本) ---")
    errors = np.where(predicted_classes != test_labels)[0]
    print(f"  总错误数: {len(errors)}/{num_samples}")
    print(f"  {'样本ID':<8} {'真实标签':<10} {'预测标签':<10} {'预测置信度':<12} {'真实类概率':<12}")
    print("  " + "-" * 55)
    for i, idx in enumerate(errors[:20]):
        true_label = test_labels[idx]
        pred_label = predicted_classes[idx]
        pred_prob = predicted_probs[idx]
        true_prob = predictions[idx, true_label]
        print(f"  {idx:<8} {true_label:<10} {pred_label:<10} {pred_prob:<12.6f} {true_prob:<12.6f}")

    # 前 20 个样本详情
    print(f"\n--- 前 30 个测试样本预测结果 ---")
    print(f"  {'ID':<5} {'真实':<6} {'预测':<6} {'置信度':<10} {'正确?':<8}")
    print("  " + "-" * 35)
    for i in range(min(30, num_samples)):
        true_l = test_labels[i]
        pred_l = predicted_classes[i]
        conf = predicted_probs[i]
        ok = "✓" if pred_l == true_l else "✗"
        print(f"  {i:<5} {true_l:<6} {pred_l:<6} {conf:<10.6f} {ok:<8}")

    # 高置信度错误检测
    high_conf_errors = errors[predicted_probs[errors] > 0.9]
    print(f"\n--- 高置信度错误 (>0.9) ---")
    print(f"  数量: {len(high_conf_errors)}")
    if len(high_conf_errors) > 0:
        for idx in high_conf_errors[:10]:
            print(f"  样本 {idx}: 真实={test_labels[idx]}, 预测={predicted_classes[idx]}, 置信度={predicted_probs[idx]:.6f}")

    print("\n" + "=" * 70)
    print(f"LeNet-MNIST 推理演示完成! 准确率: {accuracy:.2f}%")
    print("=" * 70)

    return 0


if __name__ == '__main__':
    sys.exit(main())
