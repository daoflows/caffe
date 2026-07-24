"""
步骤3产出：HardSigmoid TVM Relax 算子实现
=============================================
本文件展示如何使用 dataclass + TVM Relax nn.Module 实现新算子。

防御点（反模式规避）：
- ✅ 使用 @dataclass(slots=True) 而非普通类（内存高效+属性访问快）
- ✅ numpy.ndarray 字段使用 field(repr=False) 避免日志爆炸
- ✅ 可变默认值使用 field(default_factory=...)
- ✅ 不引入与标准库重名的模块名
- ✅ forward 方法保持纯函数式，无副作用
- ✅ define_subroutine=True 支持IR复用编译
- ✅ 通过 nn.emit() 统一变量绑定

合并到 python/operators/layers.py 时：
1. 将本类添加到文件末尾
2. 更新 __all__ 导出列表
3. 确保 import 语句已包含（dataclass, field, tvm.relax等）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import tvm
from tvm import relax
from tvm.relax import nn, op as _op


@dataclass(slots=True)
class HardSigmoid(nn.Module):
    """
    HardSigmoid 激活函数算子

    公式：y = max(0, min(1, alpha * x + beta))

    参考：
    - ONNX: https://onnx.ai/onnx/operators/onnx__HardSigmoid.html
    - PyTorch: torch.nn.Hardsigmoid (alpha=1/6, beta=0.5)
    - Caffe: 本实现，默认alpha=0.2, beta=0.5（兼容ONNX默认）

    Attributes:
        alpha: 线性项系数，默认 0.2
        beta: 偏置项，默认 0.5
        name: 算子名称，用于IR中标识
        define_subroutine: 是否生成子函数（True=复用编译，False=内联）
    """
    alpha: float = 0.2
    beta: float = 0.5
    name: str = "hardsigmoid"
    define_subroutine: bool = True

    # ❌ 反模式：不要这样写可变默认值！
    # bad_param: list = []  # 所有实例共享同一个list！
    # ✅ 正确方式：使用 default_factory
    # tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化后校验参数合法性（防御式编程）"""
        if self.alpha <= 0:
            raise ValueError(f"HardSigmoid alpha 必须为正数，当前值: {self.alpha}")
        # HardSigmoid 无可学习参数，无需创建 nn.Parameter
        # 如果是有参数的算子（如Conv、BN），在此处创建 nn.Parameter

    def forward(self, x: relax.Expr) -> relax.Var:
        """
        前向计算：HardSigmoid 激活

        Args:
            x: 输入张量，任意形状，任意浮点dtype

        Returns:
            输出张量，形状与输入相同，值范围 [0, 1]

        计算流程：
            1. linear = alpha * x + beta
            2. clipped = clip(linear, 0, 1)
            3. return clipped
        """
        dtype = x.struct_info.dtype
        alpha = relax.const(self.alpha, dtype=dtype)
        beta_const = relax.const(self.beta, dtype=dtype)

        # 线性变换: alpha * x + beta
        linear = _op.add(_op.multiply(x, alpha), beta_const)

        # 裁剪到 [0, 1]
        zero = relax.const(0.0, dtype=dtype)
        one = relax.const(1.0, dtype=dtype)
        out = _op.clip(linear, zero, one)

        # 通过 nn.emit 统一绑定变量名
        return nn.emit(out, self.name)


# ----------------------------------------------------------------------------
# 辅助函数：纯numpy参考实现（用于数值正确性测试）
# ----------------------------------------------------------------------------

def hardsigmoid_numpy(
    x: "np.ndarray",
    alpha: float = 0.2,
    beta: float = 0.5
) -> "np.ndarray":
    """
    HardSigmoid NumPy 参考实现，用于与 TVM Relax 输出对比验证。

    Args:
        x: 输入numpy数组
        alpha: 线性系数
        beta: 偏置

    Returns:
        激活后的numpy数组，范围 [0, 1]
    """
    import numpy as np  # 延迟导入，避免非测试场景强依赖numpy
    return np.clip(alpha * x + beta, 0.0, 1.0)


# ----------------------------------------------------------------------------
# 算子注册（与 LayerRegistry 对应，用于从 prototxt 创建算子实例）
# ----------------------------------------------------------------------------

def create_hardsigmoid_from_param(param) -> HardSigmoid:
    """
    从 HardSigmoidParameter protobuf 消息创建算子实例

    Args:
        param: caffe_pb2.HardSigmoidParameter 消息

    Returns:
        配置好的 HardSigmoid 算子实例

    防御点：
    - ✅ 不假设字段一定存在，使用 HasField 检查或getattr默认值
    - ✅ 参数值校验委托给 __post_init__
    """
    return HardSigmoid(
        alpha=getattr(param, "alpha", 0.2),
        beta=getattr(param, "beta", 0.5),
    )


# ----------------------------------------------------------------------------
# TVM Relax 构建辅助函数（可选）：方便快速构建带HardSigmoid的简单网络
# ----------------------------------------------------------------------------

@dataclass(slots=True)
class HardSigmoidTestNet(nn.Module):
    """
    用于测试的简单网络：Conv -> HardSigmoid
    演示如何将 HardSigmoid 组合到网络中
    """
    in_channels: int
    out_channels: int
    name: str = "hardsigmoid_test_net"

    conv: Conv2D = field(init=False)
    act: HardSigmoid = field(init=False)

    def __post_init__(self) -> None:
        self.conv = Conv2D(
            in_channels=self.in_channels,
            out_channels=self.out_channels,
            kernel_size=(3, 3),
            padding=(1, 1),
            name="conv"
        )
        self.act = HardSigmoid(alpha=0.2, beta=0.5, name="act")

    def forward(self, x: relax.Expr) -> relax.Var:
        x = self.conv(x)
        x = self.act(x)
        return nn.emit(x, self.name)


# 重导出 Conv2D（实际使用时从 layers.py 导入，这里避免依赖）
from __future__ import annotations  # noqa: E402

@dataclass(slots=True)
class Conv2D(nn.Module):  # type: ignore[no-redef]
    """简化版Conv2D占位，仅用于HardSigmoidTestNet演示"""
    in_channels: int
    out_channels: int
    kernel_size: tuple[int, int]
    padding: tuple[int, int] = (0, 0)
    stride: tuple[int, int] = (1, 1)
    name: str = "conv2d"
    define_subroutine: bool = True

    weight: nn.Parameter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        kh, kw = self.kernel_size
        self.weight = nn.Parameter(
            (self.out_channels, self.in_channels, kh, kw),
            name="weight"
        )

    def forward(self, x: relax.Expr) -> relax.Var:
        out = _op.nn.conv2d(
            x, self.weight,
            strides=self.stride,
            padding=self.padding,
            data_layout="NCHW",
            kernel_layout="OIHW",
        )
        return nn.emit(out, self.name)


if __name__ == "__main__":
    # 快速验证：打印算子信息
    print("HardSigmoid 算子示例")
    print("=" * 50)

    # 默认参数
    op = HardSigmoid()
    print(f"默认配置: alpha={op.alpha}, beta={op.beta}")

    # 自定义参数
    op2 = HardSigmoid(alpha=1.0/6.0, beta=0.5)  # PyTorch 风格
    print(f"PyTorch风格: alpha={op2.alpha:.4f}, beta={op2.beta}")

    # numpy参考实现测试
    import numpy as np
    x = np.array([-3.0, -1.0, 0.0, 1.0, 3.0], dtype=np.float32)
    y = hardsigmoid_numpy(x)
    print(f"\nNumPy参考实现测试:")
    print(f"  输入: {x}")
    print(f"  输出: {y}")
    print(f"  范围检查: min={y.min():.1f}, max={y.max():.1f}（应在[0,1]）")
