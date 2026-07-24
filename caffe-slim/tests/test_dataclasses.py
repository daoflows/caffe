#!/usr/bin/env python
"""Comprehensive unit tests for pycaffe dataclass refactoring.

Tests all dataclass definitions without requiring TVM or compiled C++ _caffe extension.
Run with:
    cd python && python -m pytest tests/test_dataclasses.py -v
    cd python && python tests/test_dataclasses.py
"""

import sys
import os
import importlib.util
import types

import numpy as np


def _setup_paths():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    python_dir = os.path.dirname(test_dir)
    pycaffe_python_dir = os.path.join(python_dir, 'pycaffe', 'python')

    sys.path.insert(0, python_dir)
    sys.path.insert(0, pycaffe_python_dir)


_setup_paths()


def _load_module_from_path(module_name, file_path, package=None):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    if package:
        module.__package__ = package
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_dataclasses_module():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    python_dir = os.path.dirname(test_dir)
    dc_path = os.path.join(python_dir, 'pycaffe', 'python', 'pycaffe', 'data_types.py')
    return _load_module_from_path('pycaffe_data_types', dc_path)


def _load_netspec_module():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    python_dir = os.path.dirname(test_dir)
    ns_path = os.path.join(python_dir, 'pycaffe', 'python', 'pycaffe', 'net_spec.py')
    return _load_module_from_path('pycaffe_netspec', ns_path)


dc = _load_dataclasses_module()
ns = _load_netspec_module()

from caffeproto import caffe_fuse


def test_transformer_config_defaults():
    cfg = dc.TransformerConfig()
    assert cfg.transpose is None
    assert cfg.channel_swap is None
    assert cfg.raw_scale is None
    assert cfg.mean is None
    assert cfg.input_scale is None


def test_transformer_config_custom_values():
    mean_arr = np.array([104.0, 117.0, 123.0], dtype=np.float32)
    cfg = dc.TransformerConfig(
        transpose=(2, 0, 1),
        channel_swap=(2, 1, 0),
        raw_scale=255.0,
        mean=mean_arr,
        input_scale=1.0,
    )
    assert cfg.transpose == (2, 0, 1)
    assert cfg.channel_swap == (2, 1, 0)
    assert cfg.raw_scale == 255.0
    np.testing.assert_array_equal(cfg.mean, mean_arr)
    assert cfg.input_scale == 1.0


def test_transformer_config_slots():
    cfg = dc.TransformerConfig()
    assert not hasattr(cfg, '__dict__')
    try:
        cfg.random_attr = 42
        assert False, "Should have raised AttributeError due to __slots__"
    except AttributeError:
        pass


def test_transformer_config_repr_hides_mean():
    mean_arr = np.array([1.0, 2.0, 3.0])
    cfg = dc.TransformerConfig(
        transpose=(2, 0, 1),
        raw_scale=255.0,
        mean=mean_arr,
    )
    r = repr(cfg)
    assert 'transpose' in r
    assert 'raw_scale' in r
    assert 'mean' not in r


def test_data_processor_config_defaults():
    cfg = dc.DataProcessorConfig()
    assert cfg.input_blob == 'data'
    assert cfg.json_log is False


def test_data_processor_config_custom():
    cfg = dc.DataProcessorConfig(input_blob='images', json_log='file.log')
    assert cfg.input_blob == 'images'
    assert cfg.json_log == 'file.log'


def test_data_processor_config_slots():
    cfg = dc.DataProcessorConfig()
    assert not hasattr(cfg, '__dict__')
    try:
        cfg.xyz = 1
        assert False
    except AttributeError:
        pass


def test_timing_stats_defaults():
    ts = dc.TimingStats()
    assert ts.cast_to_float32_ms == 0.0
    assert ts.resize_ms == 0.0
    assert ts.transforms_ms == {}
    assert ts.transforms_total_ms == 0.0
    assert ts.contiguous_ms == 0.0


def test_timing_stats_mutable_default_isolation():
    ts1 = dc.TimingStats()
    ts2 = dc.TimingStats()
    ts1.transforms_ms['resize'] = 1.5
    assert 'resize' not in ts2.transforms_ms
    assert ts2.transforms_ms == {}


def test_timing_stats_custom_values():
    ts = dc.TimingStats(
        cast_to_float32_ms=0.1,
        resize_ms=2.3,
        transforms_ms={'hflip': 0.5},
        transforms_total_ms=1.0,
        contiguous_ms=0.2,
    )
    assert ts.cast_to_float32_ms == 0.1
    assert ts.resize_ms == 2.3
    assert ts.transforms_ms == {'hflip': 0.5}
    assert ts.transforms_total_ms == 1.0
    assert ts.contiguous_ms == 0.2


def test_timing_stats_slots():
    ts = dc.TimingStats()
    assert not hasattr(ts, '__dict__')


def test_per_image_timing_required_fields():
    pit = dc.PerImageTiming(index=0, total_ms=10.5)
    assert pit.index == 0
    assert pit.total_ms == 10.5


def test_per_image_timing_optional_defaults():
    pit = dc.PerImageTiming(index=3, total_ms=5.0)
    assert pit.cast_to_float32_ms == 0.0
    assert pit.resize_ms == 0.0
    assert pit.transforms_total_ms == 0.0
    assert pit.contiguous_ms == 0.0


def test_per_image_timing_custom():
    pit = dc.PerImageTiming(
        index=7,
        total_ms=20.0,
        cast_to_float32_ms=0.3,
        resize_ms=5.0,
        transforms_total_ms=10.0,
        contiguous_ms=0.7,
    )
    assert pit.index == 7
    assert pit.total_ms == 20.0
    assert pit.cast_to_float32_ms == 0.3
    assert pit.resize_ms == 5.0


def test_per_image_timing_slots():
    pit = dc.PerImageTiming(index=0, total_ms=1.0)
    assert not hasattr(pit, '__dict__')


def test_batch_timing_stats_defaults():
    bts = dc.BatchTimingStats()
    assert bts.per_image == []
    assert bts.per_image_stats_ms == {}
    assert bts.stack_ms == 0.0
    assert bts.total_ms == 0.0


def test_batch_timing_stats_mutable_default_isolation():
    b1 = dc.BatchTimingStats()
    b2 = dc.BatchTimingStats()
    b1.per_image.append(dc.PerImageTiming(index=0, total_ms=1.0))
    assert len(b2.per_image) == 0
    b1.per_image_stats_ms['mean'] = 5.0
    assert 'mean' not in b2.per_image_stats_ms


def test_batch_timing_stats_to_dict():
    pit = dc.PerImageTiming(index=1, total_ms=3.0, cast_to_float32_ms=0.2)
    bts = dc.BatchTimingStats(
        per_image=[pit],
        per_image_stats_ms={'avg': 3.0},
        stack_ms=0.5,
        total_ms=3.5,
    )
    d = bts.to_dict()
    assert isinstance(d, dict)
    assert d['stack_ms'] == 0.5
    assert d['total_ms'] == 3.5
    assert len(d['per_image']) == 1
    assert d['per_image'][0]['index'] == 1
    assert d['per_image'][0]['total_ms'] == 3.0
    assert d['per_image_stats_ms'] == {'avg': 3.0}


def test_batch_timing_stats_to_dict_numpy_conversion():
    pit = dc.PerImageTiming(index=0, total_ms=float(np.float32(2.5)))
    bts = dc.BatchTimingStats(per_image=[pit])
    d = bts.to_dict()
    assert isinstance(d['per_image'][0]['total_ms'], float)


def test_batch_timing_stats_slots():
    bts = dc.BatchTimingStats()
    assert not hasattr(bts, '__dict__')


def test_channel_stats_required_fields():
    cs = dc.ChannelStats(channel=0, min=0.0, max=1.0, mean=0.5, std=0.1)
    assert cs.channel == 0
    assert cs.min == 0.0
    assert cs.max == 1.0
    assert cs.mean == 0.5
    assert cs.std == 0.1


def test_channel_stats_slots():
    cs = dc.ChannelStats(channel=0, min=0.0, max=1.0, mean=0.5, std=0.1)
    assert not hasattr(cs, '__dict__')


def test_tensor_stats_defaults():
    ts = dc.TensorStats()
    assert ts.shape == []
    assert ts.ndim == 0
    assert ts.per_channel == []
    assert ts.global_min == 0.0
    assert ts.global_max == 0.0
    assert ts.global_mean == 0.0
    assert ts.global_std == 0.0


def test_tensor_stats_mutable_default_isolation():
    t1 = dc.TensorStats()
    t2 = dc.TensorStats()
    t1.shape.append(1)
    t1.per_channel.append(dc.ChannelStats(channel=0, min=0.0, max=1.0, mean=0.5, std=0.1))
    assert t2.shape == []
    assert t2.per_channel == []


def test_tensor_stats_custom():
    cs = dc.ChannelStats(channel=0, min=-1.0, max=1.0, mean=0.0, std=0.5)
    ts = dc.TensorStats(
        shape=[1, 3, 224, 224],
        ndim=4,
        per_channel=[cs],
        global_min=-1.0,
        global_max=1.0,
        global_mean=0.05,
        global_std=0.45,
    )
    assert ts.shape == [1, 3, 224, 224]
    assert ts.ndim == 4
    assert len(ts.per_channel) == 1
    assert ts.global_min == -1.0
    assert ts.global_max == 1.0


def test_tensor_stats_to_dict():
    cs = dc.ChannelStats(channel=0, min=0.0, max=255.0, mean=128.0, std=50.0)
    ts = dc.TensorStats(
        shape=[2, 3],
        ndim=2,
        per_channel=[cs],
        global_min=0.0,
        global_max=255.0,
        global_mean=128.0,
        global_std=50.0,
    )
    d = ts.to_dict()
    assert isinstance(d, dict)
    assert d['shape'] == [2, 3]
    assert d['ndim'] == 2
    assert d['global_min'] == 0.0
    assert d['global_max'] == 255.0
    assert len(d['per_channel']) == 1
    assert d['per_channel'][0]['channel'] == 0


def test_tensor_stats_slots():
    ts = dc.TensorStats()
    assert not hasattr(ts, '__dict__')


def test_value_health_warning_nan():
    w = dc.ValueHealthWarning.nan(count=5, ratio=0.05)
    assert w.warning_type == 'nan'
    assert w.count == 5
    assert abs(w.ratio - 0.05) < 1e-9
    assert 'NaN' in w.message
    assert '5' in w.message
    assert '5.00%' in w.message


def test_value_health_warning_inf():
    w = dc.ValueHealthWarning.inf(count=3, ratio=0.01)
    assert w.warning_type == 'inf'
    assert w.count == 3
    assert abs(w.ratio - 0.01) < 1e-9
    assert 'Inf' in w.message
    assert '1.00%' in w.message


def test_value_health_warning_high_zero_ratio():
    w = dc.ValueHealthWarning.high_zero_ratio(count=100, ratio=0.75)
    assert w.warning_type == 'high_zero_ratio'
    assert w.count == 100
    assert abs(w.ratio - 0.75) < 1e-9
    assert 'zero' in w.message.lower()
    assert '75.00%' in w.message


def test_value_health_warning_all_non_positive():
    w = dc.ValueHealthWarning.all_non_positive(count=64, ratio=1.0)
    assert w.warning_type == 'all_non_positive'
    assert w.count == 64
    assert abs(w.ratio - 1.0) < 1e-9
    assert 'non-positive' in w.message
    assert '100.00%' in w.message


def test_value_health_warning_slots():
    w = dc.ValueHealthWarning.nan(count=1, ratio=0.1)
    assert not hasattr(w, '__dict__')


def test_image_load_info_required():
    ili = dc.ImageLoadInfo(index=0)
    assert ili.index == 0
    assert ili.load_ms == 0.0
    assert ili.shape == []


def test_image_load_info_custom():
    ili = dc.ImageLoadInfo(index=5, load_ms=12.3, shape=[224, 224, 3])
    assert ili.index == 5
    assert ili.load_ms == 12.3
    assert ili.shape == [224, 224, 3]


def test_image_load_info_mutable_default_isolation():
    i1 = dc.ImageLoadInfo(index=0)
    i2 = dc.ImageLoadInfo(index=1)
    i1.shape.append(224)
    assert i2.shape == []


def test_image_load_info_slots():
    ili = dc.ImageLoadInfo(index=0)
    assert not hasattr(ili, '__dict__')


def test_batch_input_info_defaults():
    bii = dc.BatchInputInfo()
    assert bii.count == 0
    assert bii.files == 0
    assert bii.arrays == 0
    assert bii.image_loads == []
    assert bii.unique_shapes == []
    assert bii.mixed_shapes is False


def test_batch_input_info_mutable_default_isolation():
    b1 = dc.BatchInputInfo()
    b2 = dc.BatchInputInfo()
    b1.image_loads.append(dc.ImageLoadInfo(index=0))
    b1.unique_shapes.append([224, 224])
    assert len(b2.image_loads) == 0
    assert len(b2.unique_shapes) == 0


def test_batch_input_info_custom():
    ili = dc.ImageLoadInfo(index=0, load_ms=1.0, shape=[100, 100, 3])
    bii = dc.BatchInputInfo(
        count=2,
        files=2,
        arrays=0,
        image_loads=[ili],
        unique_shapes=[[100, 100, 3]],
        mixed_shapes=False,
    )
    assert bii.count == 2
    assert bii.files == 2
    assert len(bii.image_loads) == 1


def test_batch_input_info_to_dict():
    ili = dc.ImageLoadInfo(index=0, load_ms=2.0, shape=[32, 32, 3])
    bii = dc.BatchInputInfo(
        count=1,
        files=1,
        arrays=0,
        image_loads=[ili],
        unique_shapes=[[32, 32, 3]],
        mixed_shapes=False,
    )
    d = bii.to_dict()
    assert isinstance(d, dict)
    assert d['count'] == 1
    assert d['files'] == 1
    assert d['mixed_shapes'] is False
    assert len(d['image_loads']) == 1
    assert d['image_loads'][0]['index'] == 0


def test_batch_input_info_slots():
    bii = dc.BatchInputInfo()
    assert not hasattr(bii, '__dict__')


def test_transform_info_required():
    ti = dc.TransformInfo(name='hflip')
    assert ti.name == 'hflip'
    assert ti.transform_ms == 0.0


def test_transform_info_custom():
    ti = dc.TransformInfo(name='resize', transform_ms=3.5)
    assert ti.name == 'resize'
    assert ti.transform_ms == 3.5


def test_transform_info_slots():
    ti = dc.TransformInfo(name='crop')
    assert not hasattr(ti, '__dict__')


def test_top_dataclass_creation():
    mock_fn = types.SimpleNamespace()
    mock_fn._to_proto = lambda layers, names, autonames: None
    top = ns.Top(fn=mock_fn, n=0)
    assert top.fn is mock_fn
    assert top.n == 0


def test_top_dataclass_slots():
    mock_fn = types.SimpleNamespace()
    mock_fn._to_proto = lambda layers, names, autonames: None
    top = ns.Top(fn=mock_fn, n=1)
    assert not hasattr(top, '__dict__')
    try:
        top.extra = True
        assert False
    except AttributeError:
        pass


def test_top_to_proto_method_exists():
    mock_fn = types.SimpleNamespace()
    mock_fn._to_proto = lambda layers, names, autonames: None
    top = ns.Top(fn=mock_fn, n=0)
    assert callable(top.to_proto)
    assert callable(top._to_proto)


def test_batchnorm_params_creation():
    mean = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    var = np.array([0.01, 0.02, 0.03], dtype=np.float32)
    inv_std = np.array([10.0, 7.07, 5.77], dtype=np.float32)
    bn = caffe_fuse.BatchNormParams(mean=mean, var=var, eps=1e-5, inv_std=inv_std)
    np.testing.assert_array_equal(bn.mean, mean)
    np.testing.assert_array_equal(bn.var, var)
    assert abs(bn.eps - 1e-5) < 1e-12
    np.testing.assert_array_equal(bn.inv_std, inv_std)


def test_batchnorm_params_slots():
    mean = np.zeros(3, dtype=np.float32)
    var = np.ones(3, dtype=np.float32)
    inv_std = np.ones(3, dtype=np.float32)
    bn = caffe_fuse.BatchNormParams(mean=mean, var=var, eps=1e-5, inv_std=inv_std)
    assert not hasattr(bn, '__dict__')


def test_batchnorm_params_repr_hides_arrays():
    mean = np.array([1.0, 2.0], dtype=np.float32)
    var = np.array([0.5, 0.5], dtype=np.float32)
    inv_std = np.array([1.4, 1.4], dtype=np.float32)
    bn = caffe_fuse.BatchNormParams(mean=mean, var=var, eps=0.001, inv_std=inv_std)
    r = repr(bn)
    assert 'eps' in r
    assert '0.001' in r
    assert 'mean=' not in r
    assert 'var=' not in r
    assert 'inv_std=' not in r


def test_scale_params_creation():
    gamma = np.array([1.0, 1.5, 2.0], dtype=np.float32)
    beta = np.array([0.0, 0.1, 0.2], dtype=np.float32)
    sp = caffe_fuse.ScaleParams(gamma=gamma, beta=beta, has_bias=True)
    np.testing.assert_array_equal(sp.gamma, gamma)
    np.testing.assert_array_equal(sp.beta, beta)
    assert sp.has_bias is True


def test_scale_params_no_bias():
    gamma = np.array([0.5, 0.5], dtype=np.float32)
    beta = np.zeros(2, dtype=np.float32)
    sp = caffe_fuse.ScaleParams(gamma=gamma, beta=beta, has_bias=False)
    assert sp.has_bias is False
    np.testing.assert_array_equal(sp.gamma, gamma)


def test_scale_params_slots():
    gamma = np.ones(3, dtype=np.float32)
    beta = np.zeros(3, dtype=np.float32)
    sp = caffe_fuse.ScaleParams(gamma=gamma, beta=beta, has_bias=True)
    assert not hasattr(sp, '__dict__')


def test_scale_params_repr_hides_arrays():
    gamma = np.array([1.0], dtype=np.float32)
    beta = np.array([0.0], dtype=np.float32)
    sp = caffe_fuse.ScaleParams(gamma=gamma, beta=beta, has_bias=True)
    r = repr(sp)
    assert 'has_bias' in r
    assert 'True' in r
    assert 'gamma=' not in r
    assert 'beta=' not in r


def _collect_tensor_stats_as_dataclass(arr):
    arr = np.asarray(arr, dtype=np.float32)
    per_channel = []
    if arr.ndim >= 1:
        num_channels = arr.shape[0] if arr.ndim >= 1 else 1
        for c in range(num_channels):
            ch_data = arr[c] if arr.ndim > 1 else arr
            per_channel.append(dc.ChannelStats(
                channel=c,
                min=float(np.min(ch_data)),
                max=float(np.max(ch_data)),
                mean=float(np.mean(ch_data)),
                std=float(np.std(ch_data)),
            ))
    return dc.TensorStats(
        shape=list(arr.shape),
        ndim=arr.ndim,
        per_channel=per_channel,
        global_min=float(np.min(arr)),
        global_max=float(np.max(arr)),
        global_mean=float(np.mean(arr)),
        global_std=float(np.std(arr)),
    )


def _collect_value_health_as_dataclass(arr):
    arr = np.asarray(arr)
    warnings = []
    total = arr.size
    nan_count = int(np.sum(np.isnan(arr)))
    if nan_count > 0:
        warnings.append(dc.ValueHealthWarning.nan(nan_count, nan_count / total))
    inf_count = int(np.sum(np.isinf(arr)))
    if inf_count > 0:
        warnings.append(dc.ValueHealthWarning.inf(inf_count, inf_count / total))
    finite_arr = arr[np.isfinite(arr)]
    if finite_arr.size == 0:
        return warnings
    zero_count = int(np.sum(finite_arr == 0))
    if zero_count / finite_arr.size > 0.99:
        warnings.append(dc.ValueHealthWarning.high_zero_ratio(zero_count, zero_count / finite_arr.size))
    non_pos_count = int(np.sum(finite_arr <= 0))
    if non_pos_count == finite_arr.size:
        warnings.append(dc.ValueHealthWarning.all_non_positive(non_pos_count, non_pos_count / finite_arr.size))
    return warnings


def test_collect_tensor_stats_simple_array():
    arr = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    stats = _collect_tensor_stats_as_dataclass(arr)
    assert stats.shape == [2, 2]
    assert stats.ndim == 2
    assert abs(stats.global_min - 1.0) < 1e-6
    assert abs(stats.global_max - 4.0) < 1e-6
    assert abs(stats.global_mean - 2.5) < 1e-6
    assert len(stats.per_channel) == 2
    assert stats.per_channel[0].channel == 0
    assert abs(stats.per_channel[0].min - 1.0) < 1e-6
    assert abs(stats.per_channel[0].max - 2.0) < 1e-6


def test_collect_value_health_nan():
    arr = np.array([1.0, np.nan, 2.0, np.nan, np.nan], dtype=np.float32)
    warnings = _collect_value_health_as_dataclass(arr)
    nan_warnings = [w for w in warnings if w.warning_type == 'nan']
    assert len(nan_warnings) == 1
    assert nan_warnings[0].count == 3
    assert abs(nan_warnings[0].ratio - 0.6) < 1e-6


def test_collect_value_health_inf():
    arr = np.array([1.0, np.inf, -np.inf, 2.0], dtype=np.float32)
    warnings = _collect_value_health_as_dataclass(arr)
    inf_warnings = [w for w in warnings if w.warning_type == 'inf']
    assert len(inf_warnings) == 1
    assert inf_warnings[0].count == 2
    assert abs(inf_warnings[0].ratio - 0.5) < 1e-6


def test_collect_value_health_clean_array():
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32)
    warnings = _collect_value_health_as_dataclass(arr)
    assert len(warnings) == 0


def test_collect_value_health_all_zeros():
    arr = np.zeros(100, dtype=np.float32)
    warnings = _collect_value_health_as_dataclass(arr)
    zero_warnings = [w for w in warnings if w.warning_type == 'high_zero_ratio']
    assert len(zero_warnings) == 1
    assert zero_warnings[0].count == 100


def test_collect_value_health_all_non_positive():
    arr = np.array([-1.0, -2.0, 0.0, -3.0], dtype=np.float32)
    warnings = _collect_value_health_as_dataclass(arr)
    nonpos_warnings = [w for w in warnings if w.warning_type == 'all_non_positive']
    assert len(nonpos_warnings) == 1
    assert nonpos_warnings[0].count == 4


def test_numpy_to_native_helper_converts_ndarray():
    arr = np.array([1, 2, 3], dtype=np.int32)
    result = dc._numpy_to_native(arr)
    assert isinstance(result, list)
    assert result == [1, 2, 3]


def test_numpy_to_native_helper_converts_scalars():
    assert dc._numpy_to_native(np.int32(42)) == 42
    assert isinstance(dc._numpy_to_native(np.int32(42)), int)
    assert isinstance(dc._numpy_to_native(np.float32(3.14)), float)
    assert dc._numpy_to_native(np.bool_(True)) is True


def test_numpy_to_native_helper_nested():
    data = {
        'arr': np.array([1.0, 2.0], dtype=np.float32),
        'val': np.float64(3.14),
        'list': [np.int32(1), np.int32(2)],
    }
    result = dc._numpy_to_native(data)
    assert isinstance(result['arr'], list)
    assert result['arr'] == [1.0, 2.0]
    assert isinstance(result['val'], float)
    assert isinstance(result['list'][0], int)


def test_all_dataclasses_use_slots():
    classes = [
        dc.TransformerConfig,
        dc.DataProcessorConfig,
        dc.TimingStats,
        dc.PerImageTiming,
        dc.BatchTimingStats,
        dc.ChannelStats,
        dc.TensorStats,
        dc.ValueHealthWarning,
        dc.ImageLoadInfo,
        dc.BatchInputInfo,
        dc.TransformInfo,
        ns.Top,
        caffe_fuse.BatchNormParams,
        caffe_fuse.ScaleParams,
    ]
    for cls in classes:
        assert hasattr(cls, '__slots__'), f'{cls.__name__} missing __slots__'


if __name__ == '__main__':
    tests = [
        test_transformer_config_defaults,
        test_transformer_config_custom_values,
        test_transformer_config_slots,
        test_transformer_config_repr_hides_mean,
        test_data_processor_config_defaults,
        test_data_processor_config_custom,
        test_data_processor_config_slots,
        test_timing_stats_defaults,
        test_timing_stats_mutable_default_isolation,
        test_timing_stats_custom_values,
        test_timing_stats_slots,
        test_per_image_timing_required_fields,
        test_per_image_timing_optional_defaults,
        test_per_image_timing_custom,
        test_per_image_timing_slots,
        test_batch_timing_stats_defaults,
        test_batch_timing_stats_mutable_default_isolation,
        test_batch_timing_stats_to_dict,
        test_batch_timing_stats_to_dict_numpy_conversion,
        test_batch_timing_stats_slots,
        test_channel_stats_required_fields,
        test_channel_stats_slots,
        test_tensor_stats_defaults,
        test_tensor_stats_mutable_default_isolation,
        test_tensor_stats_custom,
        test_tensor_stats_to_dict,
        test_tensor_stats_slots,
        test_value_health_warning_nan,
        test_value_health_warning_inf,
        test_value_health_warning_high_zero_ratio,
        test_value_health_warning_all_non_positive,
        test_value_health_warning_slots,
        test_image_load_info_required,
        test_image_load_info_custom,
        test_image_load_info_mutable_default_isolation,
        test_image_load_info_slots,
        test_batch_input_info_defaults,
        test_batch_input_info_mutable_default_isolation,
        test_batch_input_info_custom,
        test_batch_input_info_to_dict,
        test_batch_input_info_slots,
        test_transform_info_required,
        test_transform_info_custom,
        test_transform_info_slots,
        test_top_dataclass_creation,
        test_top_dataclass_slots,
        test_top_to_proto_method_exists,
        test_batchnorm_params_creation,
        test_batchnorm_params_slots,
        test_batchnorm_params_repr_hides_arrays,
        test_scale_params_creation,
        test_scale_params_no_bias,
        test_scale_params_slots,
        test_scale_params_repr_hides_arrays,
        test_collect_tensor_stats_simple_array,
        test_collect_value_health_nan,
        test_collect_value_health_inf,
        test_collect_value_health_clean_array,
        test_collect_value_health_all_zeros,
        test_collect_value_health_all_non_positive,
        test_numpy_to_native_helper_converts_ndarray,
        test_numpy_to_native_helper_converts_scalars,
        test_numpy_to_native_helper_nested,
        test_all_dataclasses_use_slots,
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test_fn in tests:
        name = test_fn.__name__
        try:
            result = test_fn()
            if result == 'SKIP':
                print(f'SKIP: {name}')
                skipped += 1
            else:
                print(f'PASS: {name}')
                passed += 1
        except Exception as e:
            print(f'FAIL: {name}')
            import traceback
            traceback.print_exc()
            failed += 1

    print(f'\n{"="*60}')
    print(f'Results: {passed} passed, {failed} failed, {skipped} skipped, {len(tests)} total')
    print(f'{"="*60}')
    sys.exit(0 if failed == 0 else 1)
