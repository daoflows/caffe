import logging
from dataclasses import dataclass
from typing import Optional
import tvm
from tvm import DataType, relax, tir
from tvm.relax.testing import nn
from tvm.script import ir as I, relax as R, tir as T
from tvm.relax import op as _op

logger = logging.getLogger(__name__)

@dataclass
class Conv2D(nn.Module):
    in_channels: int
    out_channels: int
    kernel_size: list[int] | int
    strides: int | tuple[int, int] = 1
    padding: int | tuple[int, ...] = 0
    dilation: int | tuple[int, int] = 1
    groups: int = 1
    bias: bool = True
    data_layout: str = 'NCHW'
    kernel_layout: str = 'OIHW'
    out_layout: Optional[str] = None
    out_dtype: Optional[str | DataType] = None
    name: str = "conv2d"
    define_subroutine: bool = True

    def __post_init__(self):
        # Allow dynamic input channels.
        if isinstance(self.in_channels, int):
            in_channels = int(self.in_channels / self.groups)
        else:
            in_channels = tir.floordiv(self.in_channels, self.groups)

        # Expand kernel size if provided an integer.
        if isinstance(self.kernel_size, int):
            self.kernel_size = [self.kernel_size] * 2
        else:
            self.kernel_size = self.kernel_size

        kernel_shape = [self.out_channels, in_channels] + list(self.kernel_size)

        self.weight = nn.Parameter(kernel_shape, self.out_dtype, name="weight")

        if self.bias:
            self.bias = nn.Parameter((self.out_channels,), self.out_dtype, name="bias")
        else:
            self.bias = None
    
    def forward(self, x: relax.Expr) -> relax.Var:
        conv_out = _op.nn.conv2d(
            data=x,
            weight=self.weight,
            strides=self.strides,
            padding=self.padding,
            dilation=self.dilation,
            data_layout=self.data_layout,
            groups=self.groups,
            kernel_layout=self.kernel_layout,
            out_layout=self.out_layout,
            out_dtype=self.out_dtype,
        )
        if self.bias is not None:
            if self.data_layout == "NCHW":
                conv_out = _op.add(conv_out, _op.reshape(self.bias, [1, -1, 1, 1]))
            elif self.data_layout == "NHWC":
                conv_out = _op.add(conv_out, _op.reshape(self.bias, [1, 1, 1, -1]))
            else:
                raise NotImplementedError(f"Dont know how to handle layout {self.data_layout}.")

        return nn.emit(conv_out, self.name)

@dataclass
class ConvTranspose2D(nn.Module):
    """
    Module for ConvTranspose1D layer.
    """
    in_channels: int
    out_channels: int
    kernel_size: list[int] | int
    strides: int | tuple[int, int] = 1
    padding: int | tuple[int, ...] = 0
    output_padding: int | tuple[int, int] = 0
    dilation: int | tuple[int, int] = 1
    groups: int = 1
    bias: bool = True
    data_layout: str = 'NCHW'
    kernel_layout: str = 'IOHW'
    out_layout: Optional[str] = None
    out_dtype: Optional[str | DataType] = None
    name: str = "conv2d_transpose"
    define_subroutine: bool = True

    def __post_init__(self):
        # Allow dynamic output channels.
        if isinstance(self.in_channels, int):
            out_channels = int(self.out_channels / self.groups)
        else:
            out_channels = tir.floordiv(self.out_channels, self.groups)

        # Expand kernel size if provided an integer.
        if isinstance(self.kernel_size, int):
            self.kernel_size = [self.kernel_size] * 2
        else:
            self.kernel_size = self.kernel_size

        kernel_shape = [self.in_channels, out_channels] + list(self.kernel_size)
        self.weight = nn.Parameter(kernel_shape, self.out_dtype, name="weight")

        if self.bias:
            self.bias = nn.Parameter((self.out_channels,), self.out_dtype, name="bias")
        else:
            self.bias = None

    def forward(self, x: relax.Expr) -> relax.Var:
        out = _op.nn.conv2d_transpose(
            data=x,
            weight=self.weight,
            strides=self.strides,
            padding=self.padding,
            output_padding=self.output_padding,
            dilation=self.dilation,
            data_layout=self.data_layout,
            groups=self.groups,
            kernel_layout=self.kernel_layout,
            out_layout=self.out_layout,
            out_dtype=self.out_dtype,
        )
        if self.bias is not None:
            if self.data_layout == "NCHW":
                out = _op.add(out, _op.reshape(self.bias, [1, -1, 1, 1]))
            elif self.data_layout == "NHWC":
                out = _op.add(out, _op.reshape(self.bias, [1, 1, 1, -1]))
            else:
                raise NotImplementedError(f"Dont know how to handle layout {self.data_layout}.")
        return nn.emit(out, self.name)

@dataclass
class L2Norm(nn.Module):
    num_channels: int
    eps: float = 1e-10
    channel_shared: bool = False
    across_spatial: bool = False
    scale_init: float = 1.0
    name: str = "l2_norm"
    define_subroutine: bool = True

    def __post_init__(self):
        if self.channel_shared:
            scale_shape = (1,)
        else:
            scale_shape = (self.num_channels,)
        self.scale = nn.Parameter(scale_shape, name="scale", init=relax.const(self.scale_init, dtype=None))

    def forward(self, x: relax.Expr) -> relax.Var:
        x_shape = _op.shape_of(x)
        x_dtype = x.struct_info.dtype
        logger.info(
            "[L2Norm] forward entry | name=%s | shape=%s | dtype=%s | "
            "num_channels=%d | eps=%.2e | channel_shared=%s | across_spatial=%s | scale_init=%.4f",
            self.name, x_shape, x_dtype, self.num_channels, self.eps,
            self.channel_shared, self.across_spatial, self.scale_init,
        )

        x_sq = _op.multiply(x, x)
        logger.debug(
            "[L2Norm] x_sq computed | name=%s | across_spatial=%s",
            self.name, self.across_spatial,
        )

        if self.across_spatial:
            logger.debug(
                "[L2Norm] sum axis: spatial (1,2,3) | name=%s | mode=ParseNet-style",
                self.name,
            )
            sum_val = _op.sum(x_sq, axis=[1, 2, 3], keepdims=True)
        else:
            logger.debug(
                "[L2Norm] sum axis: channel (1) | name=%s | mode=SSD-style (cross-channel)",
                self.name,
            )
            sum_val = _op.sum(x_sq, axis=1, keepdims=True)

        eps_val = relax.const(self.eps, dtype=x_dtype)
        sum_plus_eps = _op.add(sum_val, eps_val)
        norm = _op.sqrt(sum_plus_eps)
        logger.debug(
            "[L2Norm] norm computed | name=%s | eps=%.2e",
            self.name, self.eps,
        )

        x_norm = _op.divide(x, norm)
        logger.debug(
            "[L2Norm] x_norm computed (x / norm) | name=%s",
            self.name,
        )

        if self.channel_shared:
            scale_reshaped = _op.reshape(self.scale, [1, 1, 1, 1])
            logger.debug(
                "[L2Norm] scale reshaped: channel_shared mode | name=%s | shape=[1,1,1,1]",
                self.name,
            )
        else:
            scale_reshaped = _op.reshape(self.scale, [1, -1, 1, 1])
            logger.debug(
                "[L2Norm] scale reshaped: per-channel mode | name=%s | shape=[1,%d,1,1]",
                self.name, self.num_channels,
            )

        out = _op.multiply(x_norm, scale_reshaped)
        logger.info(
            "[L2Norm] forward exit | name=%s | channel_shared=%s | across_spatial=%s",
            self.name, self.channel_shared, self.across_spatial,
        )
        return nn.emit(out, self.name)