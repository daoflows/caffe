#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Caffe CPU 模式图像分类推理脚本（tvm-ffi pycaffe 适配版）

适配 tvm-ffi 后端的 pycaffe（caffe-slim），不依赖经典 BVLC caffe 的内部API。
使用 pycaffe 顶层 Transformer、Net 等接口。

功能说明：
    - 模型加载（deploy.prototxt + .caffemodel）
    - 图像预处理（缩放、裁剪、通道转换、均值减去、归一化）
    - CPU 模式前向推理
    - Softmax 概率计算与 Top-K 结果输出
    - 推理耗时统计

使用方法：
    python infer.py
    python infer.py --image /path/to/image.jpg
    python infer.py --prototxt model.prototxt --caffemodel model.caffemodel --image test.jpg
"""

import sys
import os
import argparse
import logging
import time
from typing import List, Tuple, Optional, Dict, Any

import numpy as np

try:
    import pycaffe as caffe
except ImportError:
    import caffe

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
DEFAULT_RAW_SCALE = 255.0

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=level, format=log_format, datefmt=date_format, stream=sys.stdout)


def parse_mean(mean_str: str) -> List[float]:
    mean_str = mean_str.strip()
    if os.path.isfile(mean_str):
        logger.warning("binaryproto 均值文件暂不支持，将忽略均值文件: %s", mean_str)
        return [0.0, 0.0, 0.0]
    parts = [p.strip() for p in mean_str.split(",")]
    try:
        values = [float(p) for p in parts]
    except ValueError:
        raise ValueError(f"无效的均值格式: {mean_str}")
    if len(values) == 1:
        return values * 3
    elif len(values) == 3:
        return values
    else:
        raise ValueError(f"均值必须为1个或3个数值，当前为 {len(values)} 个")


def load_labels(labels_path: str) -> Dict[int, str]:
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
                labels[idx] = parts[1] if len(parts) >= 2 else line
        logger.info(f"成功加载 {len(labels)} 个类别标签")
    except Exception as e:
        logger.warning(f"加载标签文件失败: {e}")
    return labels


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x_max = np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


class CaffeInference:
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
            self.mean = [0.0, 0.0, 0.0]
            logger.warning("均值文件路径暂不直接支持，将不使用均值")
        else:
            self.mean = [float(mean)] * 3

        self.net = None
        self.transformer = None
        self.input_blob = None
        self.output_blob = None

        self.load_model()

    def load_model(self) -> None:
        logger.info("=" * 60)
        logger.info("开始加载 Caffe 模型...")

        if not os.path.isfile(self.prototxt_path):
            raise FileNotFoundError(f"找不到 prototxt 文件: {self.prototxt_path}")
        if not os.path.isfile(self.caffemodel_path):
            raise FileNotFoundError(f"找不到 caffemodel 文件: {self.caffemodel_path}")

        logger.info(f"  prototxt: {self.prototxt_path}")
        logger.info(f"  caffemodel: {self.caffemodel_path}")

        caffe.set_mode_cpu()
        logger.info("  运行模式: CPU（强制 CPU_ONLY）")

        try:
            self.net = caffe.Net(self.prototxt_path, caffe.TEST, self.caffemodel_path)
        except Exception as e:
            raise RuntimeError(f"加载 Caffe 模型失败: {e}")

        self.input_blob = self.net.inputs[0] if self.net.inputs else self.net.blob_names[0]
        self.output_blob = self.net.outputs[0] if self.net.outputs else self.net.blob_names[-1]
        logger.info(f"  输入 blob: {self.input_blob}")
        logger.info(f"  输出 blob: {self.output_blob}")

        input_shape = self.net.blob_shape(self.input_blob)
        logger.info(f"  输入 shape: {input_shape}")

        if len(input_shape) == 4:
            _, c, h, w = input_shape
            self.input_size = (h, w)
            logger.info(f"  自动检测输入尺寸: {h}x{w}, 通道数: {c}")

        self._configure_transformer()
        logger.info("模型加载完成")
        logger.info("=" * 60)

    def _configure_transformer(self) -> None:
        input_shape = self.net.blob_shape(self.input_blob)
        self.transformer = caffe.Transformer({self.input_blob: input_shape})

        self.transformer.set_transpose(self.input_blob, (2, 0, 1))

        if self.channel_swap is not None:
            self.transformer.set_channel_swap(self.input_blob, self.channel_swap)
            logger.debug(f"  通道转换: RGB -> BGR (channel_swap={self.channel_swap})")

        if self.mean is not None:
            mean_array = np.array(self.mean, dtype=np.float64)
            if mean_array.ndim == 1 and len(mean_array) == 3:
                h, w = self.input_size
                mean_image = np.zeros((3, h, w), dtype=np.float64)
                mean_image[0] = mean_array[0]
                mean_image[1] = mean_array[1]
                mean_image[2] = mean_array[2]
                self.transformer.set_mean(self.input_blob, mean_image)
                logger.debug(f"  均值 (BGR): [{mean_array[0]}, {mean_array[1]}, {mean_array[2]}]")

        if self.raw_scale != 1.0:
            self.transformer.set_raw_scale(self.input_blob, self.raw_scale)
            logger.debug(f"  raw_scale: {self.raw_scale}")

        if self.input_scale != 1.0:
            self.transformer.set_input_scale(self.input_blob, self.input_scale)
            logger.debug(f"  input_scale: {self.input_scale}")

    def _load_image(self, image_path: str) -> np.ndarray:
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
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                img = np.array(pil_img)
                use_pil = True
                logger.debug(f"使用 PIL 读取图像: {image_path}")
            except ImportError:
                raise ValueError("无法读取图像：需要 OpenCV (cv2) 或 Pillow (PIL)")

        if img is None:
            raise ValueError(f"无法读取图像文件: {image_path}")

        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        elif img.shape[2] == 4:
            img = img[:, :, :3]

        logger.debug(f"图像形状: {img.shape}, 数据类型: {img.dtype}")
        return img

    def _resize_and_crop(self, img: np.ndarray) -> np.ndarray:
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
        t_start = time.perf_counter()
        img = self._load_image(image_path)
        img = self._resize_and_crop(img)
        processed = self.transformer.preprocess(self.input_blob, img)
        processed_blob = processed[np.newaxis, ...]
        t_end = time.perf_counter()
        return processed_blob, t_end - t_start

    def forward(self, input_blob: np.ndarray) -> Tuple[np.ndarray, float]:
        t_start = time.perf_counter()
        self.net.set_input_data(self.input_blob, input_blob)
        self.net.forward()
        output_data = self.net.blob_data(self.output_blob)[0]
        prob_sum = np.sum(output_data)
        if prob_sum < 0.99 or prob_sum > 1.01:
            logger.debug(f"输出未经 softmax（sum={prob_sum:.4f}），执行 softmax 转换")
            output_prob = softmax(output_data)
        else:
            output_prob = output_data
        t_end = time.perf_counter()
        return output_prob, t_end - t_start

    def postprocess(
        self, output_prob: np.ndarray, topk: int = 5, labels: Optional[Dict[int, str]] = None
    ) -> Tuple[List[Tuple[int, float, str]], float]:
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
        return results, t_end - t_start

    def infer(
        self, image_path: str, topk: int = DEFAULT_TOPK, labels: Optional[Dict[int, str]] = None
    ) -> List[Tuple[int, float, str]]:
        input_blob, t_prep = self.preprocess(image_path)
        output_prob, t_inf = self.forward(input_blob)
        results, t_post = self.postprocess(output_prob, topk, labels)

        total = t_prep + t_inf + t_post
        logger.info("-" * 60)
        logger.info("推理耗时统计:")
        logger.info(f"  预处理: {t_prep*1000:.2f} ms")
        logger.info(f"  推  理: {t_inf*1000:.2f} ms")
        logger.info(f"  后处理: {t_post*1000:.2f} ms")
        logger.info(f"  总  计: {total*1000:.2f} ms")
        logger.info("-" * 60)
        return results


def print_results(results: List[Tuple[int, float, str]], topk: int) -> None:
    print("\n" + "=" * 60)
    print(f" Top-{topk} 分类结果")
    print("=" * 60)
    for rank, (class_id, prob, label) in enumerate(results, 1):
        label_str = f" ({label})" if label else ""
        print(f"  Top-{rank}: class_id={class_id:<4d}  prob={prob:.6f}{label_str}")
    print("=" * 60 + "\n")


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Caffe CPU 模式图像分类推理脚本（tvm-ffi 版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--prototxt", type=str, default=DEFAULT_PROTOTXT)
    parser.add_argument("--caffemodel", type=str, default=DEFAULT_CAFFEMODEL)
    parser.add_argument("--image", "-i", type=str, default=DEFAULT_IMAGE)
    parser.add_argument("--mean", type=str, default=",".join(str(m) for m in DEFAULT_MEAN))
    parser.add_argument("--input-scale", type=float, default=DEFAULT_INPUT_SCALE)
    parser.add_argument("--raw-scale", type=float, default=DEFAULT_RAW_SCALE)
    parser.add_argument("--topk", "-k", type=int, default=DEFAULT_TOPK)
    parser.add_argument("--labels", type=str, default=None)
    parser.add_argument("--no-center-crop", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


def resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(SCRIPT_DIR, path))


def main() -> int:
    parser = build_argparser()
    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    try:
        mean = parse_mean(args.mean)
    except ValueError as e:
        logger.error(str(e))
        return EXIT_ARG_ERROR

    prototxt_path = resolve_path(args.prototxt)
    caffemodel_path = resolve_path(args.caffemodel)
    image_path = resolve_path(args.image)
    labels_path = resolve_path(args.labels) if args.labels else None

    logger.info("Caffe CPU 推理脚本启动（tvm-ffi 版）")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"脚本目录: {SCRIPT_DIR}")

    labels = load_labels(labels_path) if labels_path else {}

    try:
        inferencer = CaffeInference(
            prototxt_path=prototxt_path,
            caffemodel_path=caffemodel_path,
            mean=mean,
            input_scale=args.input_scale,
            raw_scale=args.raw_scale,
            center_crop=not args.no_center_crop,
        )
    except Exception as e:
        logger.error(str(e))
        if args.debug:
            import traceback
            traceback.print_exc()
        return EXIT_INFERENCE_ERROR

    try:
        results = inferencer.infer(image_path, topk=args.topk, labels=labels)
    except Exception as e:
        logger.error(f"推理失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return EXIT_INFERENCE_ERROR

    print_results(results, args.topk)
    logger.info("推理完成")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
