from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Optional, Union

import numpy as np


def _numpy_to_native(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, dict):
        return {k: _numpy_to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_numpy_to_native(v) for v in obj)
    return obj


@dataclass(slots=True)
class TransformerConfig:
    """数据变换器配置，存储图像预处理参数。"""
    transpose: Optional[tuple[int, ...]] = None
    channel_swap: Optional[tuple[int, ...]] = None
    raw_scale: Optional[float] = None
    mean: Optional[np.ndarray] = field(default=None, repr=False)
    input_scale: Optional[float] = None


@dataclass(slots=True)
class DataProcessorConfig:
    """数据处理器配置，控制输入blob名称和日志输出方式。"""
    input_blob: str = 'data'
    json_log: Union[bool, str] = False


@dataclass(slots=True)
class TimingStats:
    """单张图像处理各阶段的耗时统计。"""
    cast_to_float32_ms: float = 0.0
    resize_ms: float = 0.0
    transforms_ms: dict[str, float] = field(default_factory=dict)
    transforms_total_ms: float = 0.0
    contiguous_ms: float = 0.0


@dataclass(slots=True)
class PerImageTiming:
    """单张图像的完整处理耗时记录。"""
    index: int
    total_ms: float
    cast_to_float32_ms: float = 0.0
    resize_ms: float = 0.0
    transforms_total_ms: float = 0.0
    contiguous_ms: float = 0.0


@dataclass(slots=True)
class BatchTimingStats:
    """批量处理的耗时统计，包含单张图像统计和批处理汇总。"""
    per_image: list[PerImageTiming] = field(default_factory=list)
    per_image_stats_ms: dict[str, float] = field(default_factory=dict)
    stack_ms: float = 0.0
    total_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        result = dataclasses.asdict(self)
        return _numpy_to_native(result)


@dataclass(slots=True)
class ChannelStats:
    """单通道张量统计信息。"""
    channel: int
    min: float
    max: float
    mean: float
    std: float


@dataclass(slots=True)
class TensorStats:
    """张量整体统计信息，包含形状、维度和各通道统计。"""
    shape: list[int] = field(default_factory=list)
    ndim: int = 0
    per_channel: list[ChannelStats] = field(default_factory=list)
    global_min: float = 0.0
    global_max: float = 0.0
    global_mean: float = 0.0
    global_std: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        result = dataclasses.asdict(self)
        return _numpy_to_native(result)


@dataclass(slots=True)
class ValueHealthWarning:
    """张量值健康检查警告，用于记录异常值情况。"""
    warning_type: str
    message: str
    count: int = 0
    ratio: float = 0.0

    @classmethod
    def nan(cls, count: int, ratio: float) -> ValueHealthWarning:
        return cls(
            warning_type='nan',
            message=f'Detected {count} NaN values ({ratio:.2%} of elements)',
            count=count,
            ratio=ratio,
        )

    @classmethod
    def inf(cls, count: int, ratio: float) -> ValueHealthWarning:
        return cls(
            warning_type='inf',
            message=f'Detected {count} Inf values ({ratio:.2%} of elements)',
            count=count,
            ratio=ratio,
        )

    @classmethod
    def high_zero_ratio(cls, count: int, ratio: float) -> ValueHealthWarning:
        return cls(
            warning_type='high_zero_ratio',
            message=f'High zero ratio: {count} zeros ({ratio:.2%} of elements)',
            count=count,
            ratio=ratio,
        )

    @classmethod
    def all_non_positive(cls, count: int, ratio: float) -> ValueHealthWarning:
        return cls(
            warning_type='all_non_positive',
            message=f'All {count} values are non-positive ({ratio:.2%} of elements)',
            count=count,
            ratio=ratio,
        )


@dataclass(slots=True)
class ImageLoadInfo:
    """单张图像加载信息，包含索引、耗时和形状。"""
    index: int
    load_ms: float = 0.0
    shape: list[int] = field(default_factory=list)


@dataclass(slots=True)
class BatchInputInfo:
    """批量输入信息，记录文件/数组数量、加载耗时和形状信息。"""
    count: int = 0
    files: int = 0
    arrays: int = 0
    image_loads: list[ImageLoadInfo] = field(default_factory=list)
    unique_shapes: list[list[int]] = field(default_factory=list)
    mixed_shapes: bool = False

    def to_dict(self) -> dict[str, Any]:
        result = dataclasses.asdict(self)
        return _numpy_to_native(result)


@dataclass(slots=True)
class TransformInfo:
    """单个变换操作的信息，包含名称和耗时。"""
    name: str
    transform_ms: float = 0.0
