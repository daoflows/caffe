from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import numpy as np
from google.protobuf import text_format

from . import caffe_pb2 as pb2


@dataclass(slots=True)
class BatchNormParams:
    mean: np.ndarray = field(repr=False)
    var: np.ndarray = field(repr=False)
    eps: float
    inv_std: np.ndarray = field(repr=False)


@dataclass(slots=True)
class ScaleParams:
    gamma: np.ndarray = field(repr=False)
    beta: np.ndarray = field(repr=False)
    has_bias: bool


def get_bn_params(init_dict: Dict[str, Any], bn_layer: Any) -> BatchNormParams:
    blobs = init_dict[bn_layer.name].blobs
    inv_std = np.asarray(blobs[2].data, dtype=np.float32)
    if inv_std.size:
        inv_std = 1.0 / inv_std
    else:
        inv_std = np.array(1.0, dtype=np.float32)

    return BatchNormParams(
        mean=np.asarray(blobs[0].data, dtype=np.float32) * inv_std,
        var=np.asarray(blobs[1].data, dtype=np.float32) * inv_std,
        eps=bn_layer.batch_norm_param.eps,
        inv_std=inv_std,
    )


def get_scale_params(init_dict: Dict[str, Any], scale_layer: Any) -> ScaleParams:
    blobs = init_dict[scale_layer.name].blobs
    gamma = np.asarray(blobs[0].data, dtype=np.float32)
    has_bias = scale_layer.scale_param.bias_term
    beta = np.asarray(blobs[1].data, dtype=np.float32) if has_bias else np.zeros_like(gamma)

    return ScaleParams(gamma, beta, has_bias)


def fuse_layers(init_dict: Dict[str, Any], bn_layer: Any, scale_layer: Any) -> List[np.ndarray]:
    bn_params = get_bn_params(init_dict, bn_layer)
    scale_params = get_scale_params(init_dict, scale_layer)
    std_inv = 1.0 / np.sqrt(bn_params.var + bn_params.eps)

    return [bn_params.mean, bn_params.var, np.array(bn_params.eps, dtype=np.float32),
            scale_params.gamma, scale_params.beta, std_inv]


def _fuse_network(layers: List[Any], init_dict: Dict[str, Any], new_bn: Dict[str, Any]) -> Tuple[List[Any], Dict[str, str]]:
    new_layers = []
    pending_bn = None
    changed = {}

    for i, layer in enumerate(layers):
        if layer.type == "Input":
            new_layers.append(layer)
            continue

        if (layer.type == "BatchNorm"
                and i + 1 < len(layers)
                and layers[i + 1].type == "Scale"):
            pending_bn = layer
            continue

        if layer.type == "Scale" and pending_bn is not None:
            new_bn[pending_bn.name] = fuse_layers(init_dict, pending_bn, layer)
            new_layers.append(pending_bn)
            changed[layer.name] = pending_bn.name
            pending_bn = None
            continue

        if layer.type in ("BatchNorm", "Scale"):
            new_layers.append(layer)
            pending_bn = None
            continue

        layer.bottom[:] = [changed.get(bottom, bottom) for bottom in layer.bottom]
        new_layers.append(layer)

    return new_layers, changed


def fuse_network(init_net: pb2.NetParameter, predict_net: pb2.NetParameter) -> Tuple[pb2.NetParameter, pb2.NetParameter]:
    use_layer_field = bool(init_net.layer)
    init_layers = init_net.layer if use_layer_field else init_net.layers
    init_layer_dict = {il.name: il for il in init_layers}

    new_bn: Dict[str, Any] = {}
    new_layers, changed = _fuse_network(predict_net.layer, init_layer_dict, new_bn)

    predict_net.ClearField('layer')
    predict_net.layer.extend(new_layers)

    changed_names = set(changed.keys())
    remaining_layers = [l for l in init_layers if l.name not in changed_names]

    for layer in remaining_layers:
        if layer.name in new_bn:
            mean, var, eps, gamma, beta, std_inv = new_bn[layer.name]
            layer.blobs[0].data[:] = mean.ravel().tolist()
            layer.blobs[1].data[:] = var.ravel().tolist()
            layer.blobs[2].data[:] = (gamma * std_inv).ravel().tolist()

    init_net.Clear()
    init_net.name = predict_net.name
    if use_layer_field:
        init_net.layer.extend(remaining_layers)
    else:
        init_net.layers.extend(remaining_layers)

    return init_net, predict_net


if __name__ == "__main__":
    from .caffe_utils import unity_struct
    proto_file = "ResNet-50-deploy.prototxt"
    blob_file = "ResNet-50-model.caffemodel"
    init_net = pb2.NetParameter()
    predict_net = pb2.NetParameter()
    with open(proto_file, 'r') as f:
        text_format.Merge(f.read(), predict_net)
    with open(blob_file, 'rb') as fp:
        init_net.ParseFromString(fp.read())
    predict_net = unity_struct(predict_net)
    init_net, predict_net = fuse_network(init_net, predict_net)
    with open("test.prototxt", "w") as fp:
        fp.write(text_format.MessageToString(predict_net))
    with open("test.caffemodel", "wb") as fp:
        fp.write(init_net.SerializeToString())
