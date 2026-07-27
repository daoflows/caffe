#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Caffe CPU 模式图像分类推理脚本

功能说明：
    基于 Caffe 框架实现完整的图像分类推理流程，包括：
    - 模型加载（deploy.prototxt + .caffemodel）
    - 图像预处理（缩放、裁剪、通道转换、均值减去、归一化）
    - CPU 模式前向推理
    - Softmax 概率计算与 Top-K 结果输出
    - 推理耗时统计
    - 完善的错误处理与优雅退出

使用方法：
    1. 命令行直接运行（使用默认 ResNet-50 模型和 demo 图片）：
        python inference.py

    2. 指定自定义模型和图片：
        python inference.py \\
            --prototxt resnet50/ResNet-50-deploy.prototxt \\
            --caffemodel resnet50/ResNet-50-model.caffemodel \\
            --image resnet50/data/demo.png \\
            --mean 103.939,116.779,123.68 \\
            --topk 5

    3. 作为 Python 模块导入使用：
        from inference import CaffeInference

        inferencer = CaffeInference(
            prototxt_path='resnet50/ResNet-50-deploy.prototxt',
            caffemodel_path='resnet50/ResNet-50-model.caffemodel',
            mean=[103.939, 116.779, 123.68]
        )
        results = inferencer.infer('test.jpg', topk=5)
        for class_id, prob, label in results:
            print(f"Class {class_id}: {prob:.4f} {label}")

环境要求：
    - caffe-cpu:standalone-jupyter-test Docker 镜像
    - 挂载路径: /workspace 对应宿主机 /media/pc/data/ai/notebook
    - 容器启动命令:
      docker run -it --rm \\
        -e DEBUGINFOD_URLS="" \\
        -e DEBUGINFOD_IMA_CERT_PATH="" \\
        -v /media/pc/data/ai/notebook:/workspace \\
        -w /workspace \\
        caffe-cpu:standalone-jupyter-test \\
        bash -c "cd /workspace && python workspace/models/demo/caffe/inference.py"
"""

import sys
import os
import argparse
import logging
import time
from typing import List, Tuple, Optional, Dict, Any

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

EXIT_SUCCESS = 0
EXIT_ARG_ERROR = 1
EXIT_FILE_ERROR = 2
EXIT_INFERENCE_ERROR = 3

DEFAULT_PROTOTXT = os.path.join(SCRIPT_DIR, "resnet50", "ResNet-50-deploy.prototxt")
DEFAULT_CAFFEMODEL = os.path.join(SCRIPT_DIR, "resnet50", "ResNet-50-model.caffemodel")
DEFAULT_IMAGE = os.path.join(SCRIPT_DIR, "resnet50", "data", "demo.png")
DEFAULT_MEAN = [103.939, 116.779, 123.68]
DEFAULT_INPUT_SIZE = (224, 224)
DEFAULT_TOPK = 5
DEFAULT_INPUT_SCALE = 1.0
DEFAULT_RAW_SCALE = 1.0

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """配置日志系统

    Args:
        verbose: 是否启用 DEBUG 级别详细日志
    """
    level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=level, format=log_format, datefmt=date_format, stream=sys.stdout)


def parse_mean(mean_str: str) -> List[float]:
    """解析均值参数字符串

    支持格式：
        - 单值: "128" (所有通道使用相同均值)
        - 三值: "103.939,116.779,123.68" (BGR 顺序)
        - .binaryproto 文件路径

    Args:
        mean_str: 均值字符串或文件路径

    Returns:
        长度为3的均值列表 [B_mean, G_mean, R_mean]

    Raises:
        ValueError: 均值格式无效
    """
    mean_str = mean_str.strip()

    if os.path.isfile(mean_str):
        logger.info(f"检测到均值文件: {mean_str}，将尝试加载 binaryproto 格式")
        return mean_str

    parts = [p.strip() for p in mean_str.split(",")]
    try:
        values = [float(p) for p in parts]
    except ValueError:
        raise ValueError(f"无效的均值格式: {mean_str}，应为数值或逗号分隔的数值列表")

    if len(values) == 1:
        return values * 3
    elif len(values) == 3:
        return values
    else:
        raise ValueError(f"均值必须为1个或3个数值，当前为 {len(values)} 个: {mean_str}")


def load_labels(labels_path: str) -> Dict[int, str]:
    """加载 ImageNet 标签文件 (synset_words.txt 格式)

    标签文件格式：每行 "n01234567 class name"，按类别 ID 顺序排列。

    Args:
        labels_path: 标签文件路径

    Returns:
        字典 {class_id: class_name}
    """
    labels = {}
    if not os.path.isfile(labels_path):
        logger.warning(f"标签文件不存在: {labels_path}，将只显示类别 ID")
        return labels

    try:
        with open(labels_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" ", 1)
                if len(parts) >= 2:
                    labels[idx] = parts[1]
                else:
                    labels[idx] = line
        logger.info(f"成功加载 {len(labels)} 个类别标签")
    except Exception as e:
        logger.warning(f"加载标签文件失败: {e}，将只显示类别 ID")

    return labels


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """计算 Softmax 概率分布

    为数值稳定性，先减去最大值再计算指数。

    Args:
        x: 输入 logits 数组
        axis: 沿哪个轴计算 softmax

    Returns:
        概率分布数组，与输入形状相同
    """
    x_max = np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


class CaffeInference:
    """Caffe CPU 图像分类推理器

    封装 Caffe 模型的加载、预处理、推理和后处理完整流程。
    使用前确保 caffe 模块可正常导入（在 caffe-cpu Docker 容器内运行）。

    Attributes:
        prototxt_path: deploy.prototxt 文件路径
        caffemodel_path: .caffemodel 权重文件路径
        mean: 图像均值 (BGR 顺序)，长度3列表或 .binaryproto 路径
        input_scale: 输入缩放系数
        raw_scale: 原始像素缩放系数（[0,1]→[0,255]）
        channel_swap: 通道顺序转换，默认 (2,1,0) 即 RGB→BGR
        input_size: 模型输入尺寸 (height, width)
        center_crop: 是否使用中心裁剪（ImageNet 标准：短边256→中心裁剪224）
        net: Caffe Net 对象
        transformer: Caffe Transformer 对象
        input_blob: 输入 blob 名称
        output_blob: 输出 blob 名称
    """

    def __init__(
        self,
        prototxt_path: str,
        caffemodel_path: str,
        mean: Any = None,
        input_scale: float = DEFAULT_INPUT_SCALE,
        raw_scale: float = DEFAULT_RAW_SCALE,
        channel_swap: Tuple[int, int, int] = (2, 1, 0),
        input_size: Tuple[int, int] = DEFAULT_INPUT_SIZE,
        center_crop: bool = True,
    ):
        """初始化推理器并加载模型

        Args:
            prototxt_path: deploy.prototxt 网络结构文件路径
            caffemodel_path: .caffemodel 模型权重文件路径
            mean: 图像均值，支持:
                - 长度3列表 (B, G, R)，如 [103.939, 116.779, 123.68]
                - 单数值（所有通道使用相同均值）
                - .binaryproto 均值文件路径
                - None（不减均值）
            input_scale: 特征缩放系数，默认 1.0
            raw_scale: 像素值缩放系数，若输入为 [0,1] 范围设为 255
            channel_swap: 通道交换顺序，(2,1,0) 表示 RGB→BGR
            input_size: 模型输入尺寸 (height, width)，默认 (224, 224)
            center_crop: 是否使用中心裁剪，True 时先缩放短边至256再裁剪至input_size

        Raises:
            FileNotFoundError: 模型文件不存在
            RuntimeError: 模型加载失败
        """
        self.prototxt_path = prototxt_path
        self.caffemodel_path = caffemodel_path
        self.input_scale = input_scale
        self.raw_scale = raw_scale
        self.channel_swap = channel_swap
        self.input_size = input_size
        self.center_crop = center_crop

        if mean is None:
            self.mean = None
        elif isinstance(mean, (list, tuple)):
            self.mean = list(mean)
        elif isinstance(mean, str):
            self.mean = mean
        else:
            self.mean = [float(mean)] * 3

        self.net = None
        self.transformer = None
        self.input_blob = None
        self.output_blob = None

        self._import_caffe()
        self.load_model()

    def _import_caffe(self) -> None:
        """导入 caffe 模块并设置 CPU 模式

        Raises:
            ImportError: 无法导入 caffe 模块
        """
        try:
            import caffe
            self.caffe = caffe
        except ImportError as e:
            raise ImportError(
                "无法导入 Caffe 模块 (import caffe 失败)。\n"
                "请确保在 caffe-cpu:standalone-jupyter-test Docker 容器内运行，\n"
                "且已正确配置 PyCaffe 环境。\n"
                f"原始错误: {e}"
            )

    def load_model(self) -> None:
        """加载 Caffe 模型并配置 Transformer

        设置 CPU 模式，创建 Net 对象，自动检测输入输出 blob，
        并配置图像预处理器 Transformer。

        Raises:
            FileNotFoundError: prototxt 或 caffemodel 文件不存在
            RuntimeError: 模型加载失败
        """
        logger.info("=" * 60)
        logger.info("开始加载 Caffe 模型...")

        if not os.path.isfile(self.prototxt_path):
            raise FileNotFoundError(f"找不到 prototxt 文件: {self.prototxt_path}")
        if not os.path.isfile(self.caffemodel_path):
            raise FileNotFoundError(f"找不到 caffemodel 文件: {self.caffemodel_path}")

        logger.info(f"  prototxt: {self.prototxt_path}")
        logger.info(f"  caffemodel: {self.caffemodel_path}")

        self.caffe.set_mode_cpu()
        logger.info("  运行模式: CPU（强制 CPU_ONLY）")

        try:
            self.net = self.caffe.Net(self.prototxt_path, self.caffemodel_path, self.caffe.TEST)
        except Exception as e:
            raise RuntimeError(f"加载 Caffe 模型失败，请检查文件格式是否正确: {e}")

        blob_names = list(self.net.blobs.keys())
        self.input_blob = blob_names[0]
        self.output_blob = blob_names[-1]
        logger.info(f"  输入 blob: {self.input_blob}")
        logger.info(f"  输出 blob: {self.output_blob}")

        input_shape = self.net.blobs[self.input_blob].data.shape
        logger.info(f"  输入 shape: {input_shape}")

        if len(input_shape) == 4:
            _, c, h, w = input_shape
            self.input_size = (h, w)
            logger.info(f"  自动检测输入尺寸: {h}x{w}, 通道数: {c}")

        self._configure_transformer()
        logger.info("模型加载完成 ✓")
        logger.info("=" * 60)

    def _configure_transformer(self) -> None:
        """配置 Caffe Transformer 预处理器

        设置以下预处理步骤：
        1. transpose: (H, W, C) → (C, H, W)
        2. channel_swap: RGB → BGR (Caffe 惯例)
        3. mean: 减去图像均值
        4. raw_scale: 像素值范围缩放
        5. input_scale: 特征值缩放
        """
        self.transformer = self.caffe.io.Transformer({self.input_blob: self.net.blobs[self.input_blob].data.shape})

        self.transformer.set_transpose(self.input_blob, (2, 0, 1))

        if self.channel_swap is not None:
            self.transformer.set_channel_swap(self.input_blob, self.channel_swap)
            logger.debug(f"  通道转换: RGB -> BGR (channel_swap={self.channel_swap})")

        if self.mean is not None:
            if isinstance(self.mean, str) and self.mean.endswith(".binaryproto"):
                logger.info(f"  从 binaryproto 加载均值: {self.mean}")
                blob = self.caffe.proto.caffe_pb2.BlobProto()
                with open(self.mean, "rb") as f:
                    blob.ParseFromString(f.read())
                mean_array = np.array(self.caffe.io.blobproto_to_array(blob))[0]
                self.transformer.set_mean(self.input_blob, mean_array)
            else:
                mean_array = np.array(self.mean, dtype=np.float64)
                if mean_array.ndim == 1 and len(mean_array) == 3:
                    h, w = self.input_size
                    mean_image = np.zeros((h, w, 3), dtype=np.float64)
                    mean_image[:, :, 0] = mean_array[0]
                    mean_image[:, :, 1] = mean_array[1]
                    mean_image[:, :, 2] = mean_array[2]
                    self.transformer.set_mean(self.input_blob, mean_image)
                    logger.debug(f"  均值 (BGR): [{mean_array[0]}, {mean_array[1]}, {mean_array[2]}]")

        if self.raw_scale != 1.0:
            self.transformer.set_raw_scale(self.input_blob, self.raw_scale)
            logger.debug(f"  raw_scale: {self.raw_scale}")

        if self.input_scale != 1.0:
            self.transformer.set_input_scale(self.input_blob, self.input_scale)
            logger.debug(f"  input_scale: {self.input_scale}")

    def _load_image(self, image_path: str) -> np.ndarray:
        """读取图像文件

        优先使用 OpenCV (cv2) 读取，若 cv2 不可用则回退到 PIL。
        自动处理 RGBA→RGB 和灰度→RGB 转换。

        Args:
            image_path: 图像文件路径

        Returns:
            numpy 数组，形状 (H, W, 3)，RGB 格式，uint8 或 float32

        Raises:
            FileNotFoundError: 图像文件不存在
            ValueError: 图像无法读取或格式不支持
        """
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"找不到输入图片: {image_path}")

        img = None
        use_cv2 = False
        use_pil = False

        try:
            import cv2
            img = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                use_cv2 = True
                logger.debug(f"使用 OpenCV 读取图像: {image_path}")
        except ImportError:
            logger.debug("OpenCV (cv2) 不可用，尝试使用 PIL")

        if img is None:
            try:
                from PIL import Image
                pil_img = Image.open(image_path)
                if pil_img.mode == "RGBA":
                    pil_img = pil_img.convert("RGB")
                elif pil_img.mode == "L":
                    pil_img = pil_img.convert("RGB")
                elif pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                img = np.array(pil_img)
                use_pil = True
                logger.debug(f"使用 PIL 读取图像: {image_path}")
            except ImportError:
                raise ValueError(
                    "无法读取图像：需要 OpenCV (cv2) 或 Pillow (PIL)，"
                    "请确保容器内已安装其中一个库。"
                )

        if img is None:
            raise ValueError(f"无法读取图像文件: {image_path}，文件可能损坏或格式不支持")

        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        elif img.shape[2] == 4:
            img = img[:, :, :3]
        elif img.shape[2] == 1:
            img = np.concatenate([img, img, img], axis=-1)

        logger.debug(f"图像形状: {img.shape}, 数据类型: {img.dtype}, 读取库: {'cv2' if use_cv2 else 'PIL'}")
        return img

    def _resize_and_crop(self, img: np.ndarray) -> np.ndarray:
        """图像缩放和中心裁剪

        若 center_crop=True，执行 ImageNet 标准预处理：
        1. 将短边缩放至 256 像素
        2. 从中心裁剪 input_size 大小区域

        若 center_crop=False，直接缩放至 input_size。

        Args:
            img: 输入图像 (H, W, 3)，RGB 格式

        Returns:
            处理后的图像 (input_h, input_w, 3)
        """
        h, w = img.shape[:2]
        target_h, target_w = self.input_size

        if self.center_crop:
            scale_size = 256
            if h < w:
                new_h = scale_size
                new_w = int(w * scale_size / h)
            else:
                new_w = scale_size
                new_h = int(h * scale_size / w)
        else:
            new_h, new_w = target_h, target_w

        try:
            import cv2
            img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        except ImportError:
            from PIL import Image
            pil_img = Image.fromarray(img)
            pil_img = pil_img.resize((new_w, new_h), Image.BILINEAR)
            img_resized = np.array(pil_img)

        if self.center_crop:
            h_off = (new_h - target_h) // 2
            w_off = (new_w - target_w) // 2
            img_cropped = img_resized[h_off:h_off + target_h, w_off:w_off + target_w]
            logger.debug(f"中心裁剪: ({h_off},{w_off}) 裁剪 {target_h}x{target_w}")
        else:
            img_cropped = img_resized

        logger.debug(f"预处理后形状: {img_cropped.shape}")
        return img_cropped

    def preprocess(self, image_path: str) -> Tuple[np.ndarray, float]:
        """执行图像预处理全流程

        Args:
            image_path: 输入图像路径

        Returns:
            (processed_blob, preprocess_time): 预处理后的 blob 和预处理耗时（秒）
            processed_blob 形状: (1, C, H, W)

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 图像读取或预处理失败
        """
        t_start = time.perf_counter()

        img = self._load_image(image_path)
        img = self._resize_and_crop(img)

        processed = self.transformer.preprocess(self.input_blob, img)
        processed_blob = processed[np.newaxis, ...]

        t_end = time.perf_counter()
        preprocess_time = t_end - t_start
        logger.debug(f"预处理完成，耗时: {preprocess_time*1000:.2f} ms")

        return processed_blob, preprocess_time

    def forward(self, input_blob: np.ndarray) -> Tuple[np.ndarray, float]:
        """执行前向推理

        Args:
            input_blob: 预处理后的输入数据，形状 (1, C, H, W)

        Returns:
            (output_prob, inference_time): 输出概率和推理耗时（秒）

        Raises:
            RuntimeError: 推理执行失败
        """
        t_start = time.perf_counter()

        self.net.blobs[self.input_blob].data[...] = input_blob

        try:
            output = self.net.forward()
        except Exception as e:
            raise RuntimeError(f"前向推理执行失败: {e}")

        if self.output_blob in output:
            output_data = output[self.output_blob][0]
        else:
            output_data = self.net.blobs[self.output_blob].data[0]

        prob_sum = np.sum(output_data)
        if prob_sum < 0.99 or prob_sum > 1.01:
            logger.debug(f"输出未经 softmax（sum={prob_sum:.4f}），执行 softmax 转换")
            output_prob = softmax(output_data)
        else:
            output_prob = output_data

        t_end = time.perf_counter()
        inference_time = t_end - t_start
        logger.debug(f"推理完成，耗时: {inference_time*1000:.2f} ms")

        return output_prob, inference_time

    def postprocess(
        self, output_prob: np.ndarray, topk: int = 5, labels: Optional[Dict[int, str]] = None
    ) -> Tuple[List[Tuple[int, float, str]], float]:
        """后处理：获取 Top-K 分类结果

        Args:
            output_prob: softmax 概率分布
            topk: 返回前 K 个结果
            labels: 标签字典 {class_id: class_name}，可选

        Returns:
            (results, postprocess_time): 结果列表和后处理耗时（秒）
            results: [(class_id, probability, label_str), ...] 按概率降序排列
        """
        t_start = time.perf_counter()

        topk = min(topk, len(output_prob))
        top_indices = np.argsort(output_prob)[::-1][:topk]

        results = []
        for idx in top_indices:
            class_id = int(idx)
            prob = float(output_prob[idx])
            label = labels.get(class_id, "") if labels else ""
            results.append((class_id, prob, label))

        t_end = time.perf_counter()
        postprocess_time = t_end - t_start
        logger.debug(f"后处理完成，耗时: {postprocess_time*1000:.2f} ms")

        return results, postprocess_time

    def infer(
        self, image_path: str, topk: int = DEFAULT_TOPK, labels: Optional[Dict[int, str]] = None
    ) -> List[Tuple[int, float, str]]:
        """执行完整推理流程

        Args:
            image_path: 输入图像路径
            topk: 返回 Top-K 结果数量，默认 5
            labels: 标签字典，可选

        Returns:
            结果列表 [(class_id, probability, label_str), ...]，按概率降序排列

        Raises:
            各种异常：见 preprocess/forward/postprocess
        """
        input_blob, t_preprocess = self.preprocess(image_path)
        output_prob, t_inference = self.forward(input_blob)
        results, t_postprocess = self.postprocess(output_prob, topk, labels)

        total_time = t_preprocess + t_inference + t_postprocess
        logger.info("-" * 60)
        logger.info(f"推理耗时统计:")
        logger.info(f"  预处理: {t_preprocess*1000:.2f} ms")
        logger.info(f"  推  理: {t_inference*1000:.2f} ms")
        logger.info(f"  后处理: {t_postprocess*1000:.2f} ms")
        logger.info(f"  总  计: {total_time*1000:.2f} ms")
        logger.info("-" * 60)

        return results


def print_results(results: List[Tuple[int, float, str]], topk: int) -> None:
    """格式化打印 Top-K 分类结果

    Args:
        results: 结果列表 [(class_id, prob, label), ...]
        topk: K 值
    """
    print("\n" + "=" * 60)
    print(f" Top-{topk} 分类结果")
    print("=" * 60)
    for rank, (class_id, prob, label) in enumerate(results, 1):
        label_str = f" ({label})" if label else ""
        print(f"  Top-{rank}: class_id={class_id:<4d}  prob={prob:.6f}{label_str}")
    print("=" * 60 + "\n")


def build_argparser() -> argparse.ArgumentParser:
    """构建命令行参数解析器

    Returns:
        argparse.ArgumentParser 对象
    """
    parser = argparse.ArgumentParser(
        description="Caffe CPU 模式图像分类推理脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认参数运行（ResNet-50 + demo.png）
  python inference.py

  # 指定自定义模型和图片
  python inference.py --prototxt model.prototxt --caffemodel model.caffemodel --image test.jpg

  # 指定均值和 Top-K
  python inference.py --mean 103.939,116.779,123.68 --topk 10

  # 使用标签文件显示类别名称
  python inference.py --labels synset_words.txt

  # 启用详细日志
  python inference.py -v
        """,
    )

    parser.add_argument(
        "--prototxt",
        type=str,
        default=DEFAULT_PROTOTXT,
        help=f"deploy.prototxt 网络结构文件路径 (默认: {DEFAULT_PROTOTXT})",
    )
    parser.add_argument(
        "--caffemodel",
        type=str,
        default=DEFAULT_CAFFEMODEL,
        help=f".caffemodel 模型权重文件路径 (默认: {DEFAULT_CAFFEMODEL})",
    )
    parser.add_argument(
        "--image",
        "-i",
        type=str,
        default=DEFAULT_IMAGE,
        help=f"输入图片路径 (默认: {DEFAULT_IMAGE})",
    )
    parser.add_argument(
        "--mean",
        type=str,
        default=",".join(str(m) for m in DEFAULT_MEAN),
        help=f"图像均值 (BGR顺序)，格式: 'B,G,R' 或单值 或 .binaryproto 文件路径 (默认: {DEFAULT_MEAN})",
    )
    parser.add_argument(
        "--input-scale",
        type=float,
        default=DEFAULT_INPUT_SCALE,
        help=f"输入特征缩放系数 (默认: {DEFAULT_INPUT_SCALE})",
    )
    parser.add_argument(
        "--raw-scale",
        type=float,
        default=DEFAULT_RAW_SCALE,
        help=f"像素值原始缩放系数 (默认: {DEFAULT_RAW_SCALE}，输入为[0,1]范围时设为255)",
    )
    parser.add_argument(
        "--topk",
        "-k",
        type=int,
        default=DEFAULT_TOPK,
        help=f"输出 Top-K 分类结果数量 (默认: {DEFAULT_TOPK})",
    )
    parser.add_argument(
        "--labels",
        type=str,
        default=None,
        help="ImageNet 标签文件路径 (synset_words.txt 格式)，可选",
    )
    parser.add_argument(
        "--no-center-crop",
        action="store_true",
        help="禁用中心裁剪（默认启用：短边缩放至256后中心裁剪224x224）",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="⚠️  此参数将被忽略，脚本强制使用 CPU 模式",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="调试模式：发生错误时显示完整 Python traceback",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="启用 DEBUG 级别详细日志输出",
    )

    return parser


def resolve_path(path: str) -> str:
    """解析路径，支持相对路径和绝对路径

    相对路径基于脚本所在目录解析。

    Args:
        path: 输入路径

    Returns:
        解析后的绝对路径
    """
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(SCRIPT_DIR, path))


def main() -> int:
    """主函数：解析参数、执行推理、输出结果

    Returns:
        退出码：0=成功, 1=参数错误, 2=文件错误, 3=推理错误
    """
    parser = build_argparser()
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    if args.gpu:
        logger.warning("⚠️  此脚本仅支持 CPU 模式，--gpu 参数将被忽略")

    try:
        mean = parse_mean(args.mean)
    except ValueError as e:
        logger.error(f"参数错误: {e}")
        return EXIT_ARG_ERROR

    prototxt_path = resolve_path(args.prototxt)
    caffemodel_path = resolve_path(args.caffemodel)
    image_path = resolve_path(args.image)
    labels_path = resolve_path(args.labels) if args.labels else None

    logger.info(f"Caffe CPU 推理脚本启动")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"脚本目录: {SCRIPT_DIR}")

    labels = {}
    if labels_path:
        labels = load_labels(labels_path)

    try:
        inferencer = CaffeInference(
            prototxt_path=prototxt_path,
            caffemodel_path=caffemodel_path,
            mean=mean,
            input_scale=args.input_scale,
            raw_scale=args.raw_scale,
            center_crop=not args.no_center_crop,
        )
    except FileNotFoundError as e:
        logger.error(str(e))
        return EXIT_FILE_ERROR
    except ImportError as e:
        logger.error(str(e))
        return EXIT_FILE_ERROR
    except RuntimeError as e:
        logger.error(str(e))
        if args.debug:
            import traceback
            traceback.print_exc()
        return EXIT_INFERENCE_ERROR
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return EXIT_INFERENCE_ERROR

    try:
        results = inferencer.infer(image_path, topk=args.topk, labels=labels)
    except FileNotFoundError as e:
        logger.error(str(e))
        return EXIT_FILE_ERROR
    except ValueError as e:
        logger.error(str(e))
        if args.debug:
            import traceback
            traceback.print_exc()
        return EXIT_FILE_ERROR
    except RuntimeError as e:
        logger.error(str(e))
        if args.debug:
            import traceback
            traceback.print_exc()
        return EXIT_INFERENCE_ERROR
    except Exception as e:
        logger.error(f"推理过程发生错误: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return EXIT_INFERENCE_ERROR

    print_results(results, args.topk)

    logger.info("推理完成 ✓")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
