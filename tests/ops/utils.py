# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os
import time
import logging
import tracemalloc
import numpy as np
from google.protobuf import text_format
import caffe
from caffe import layers as L, params as P
from caffe.proto import caffe_pb2 as pb

np.random.seed(42)

os.environ["GLOG_minloglevel"] = "2"

_log_level = os.environ.get("CAFFE_LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.WARNING),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _create_dir(d_path):
    """If the directory is not existed, create it"""
    logger.debug(f"Creating directory: {d_path}")
    if not (os.path.exists(d_path) and os.path.isdir(d_path)):
        os.makedirs(d_path)


def _list_to_str(ll):
    """Convert list or tuple to str, separated by underline."""
    if isinstance(ll, (tuple, list)):
        tmp = [str(i) for i in ll]
        res = "_".join(tmp)
    else:
        res = str(ll)
    return res


def _dict_to_str(d):
    """Convert a dict to a filename-safe string."""
    items = []
    for k in sorted(d.keys()):
        v = d[k]
        if isinstance(v, dict):
            items.append(f"{k}-{_dict_to_str(v)}")
        elif isinstance(v, (list, tuple)):
            items.append(f"{k}-{_list_to_str(v)}")
        elif isinstance(v, bool):
            items.append(f"{k}-{1 if v else 0}")
        else:
            items.append(f"{k}-{v}")
    return "_".join(items)


def _gen_filename_str(op_name, data_shape, base_dir, *args, **kwargs):
    """Combining the filename according to the op_name, shape and other args."""
    file_dir = os.path.join(base_dir, op_name)
    _create_dir(file_dir)
    res = op_name + "_"
    shape_str = _list_to_str(list(data_shape))
    res += shape_str
    for arg in args:
        if isinstance(arg, (tuple, list)):
            res += "_" + _list_to_str(arg)
        elif isinstance(arg, (int, float, str)):
            res += "_" + str(arg)
        elif isinstance(arg, dict):
            res += "_" + _dict_to_str(arg)
    for k, v in kwargs.items():
        if isinstance(v, (tuple, list)):
            res += "_" + k + "-" + _list_to_str(v)
        elif isinstance(v, (int, float, str)):
            res += "_" + k + "-" + str(v)
        elif isinstance(v, bool):
            res += "_" + k + "-" + ("1" if v else "0")
        elif isinstance(v, dict):
            res += "_" + k + "-" + _dict_to_str(v)
    res = res.replace(".", "_")
    res = res.replace("-", "_")
    proto_file = os.path.join(file_dir, res + ".prototxt")
    blob_file = os.path.join(file_dir, res + ".caffemodel")
    solver_file = os.path.join(file_dir, res + "_solver.prototxt")
    logger.debug(f"Generated files - proto: {proto_file}, blob: {blob_file}, solver: {solver_file}")

    return (proto_file, blob_file, solver_file)


def _save_prototxt(n_netspec, f_path):
    """Generate .prototxt file according to caffe.NetSpec"""
    logger.debug(f"Saving prototxt to: {f_path}")
    s = n_netspec.to_proto()
    with open(f_path, "w") as f:
        f.write(str(s))


def _save_solver(solver_file, proto_file, blob_file):
    """Define a solver proto, you can change the configs."""
    logger.debug(f"Saving solver to: {solver_file}, proto: {proto_file}, blob: {blob_file}")
    blob_file_prefix = blob_file.split(".caffemodel")[0]
    s = pb.SolverParameter()
    s.train_net = proto_file
    s.base_lr = 0.01
    s.momentum = 0.9
    s.weight_decay = 0.0005
    s.lr_policy = "inv"
    s.gamma = 0.0001
    s.power = 0.75
    s.display = 1
    s.max_iter = 100000
    s.snapshot = 100000
    s.snapshot_prefix = blob_file_prefix

    with open(solver_file, "w") as f:
        f.write(str(s))


def _save_caffemodel(solver_file, blob_file):
    """Generate .caffemodel file."""
    logger.info(f"Saving caffemodel to: {blob_file}")
    solver = caffe.SGDSolver(solver_file)
    solver.net.save(blob_file)


def _gen_model_files(n_netspec, proto_file, blob_file, solver_file):
    logger.info("Starting model files generation")
    _save_prototxt(n_netspec, proto_file)
    _save_solver(solver_file, proto_file, blob_file)
    _save_caffemodel(solver_file, blob_file)


def _siso_op(data, func, *args, **kwargs):
    """Create single input and single output Caffe op"""
    logger.debug(f"Creating SISO op, input shape: {data.shape}")
    n = caffe.NetSpec()
    n.data = L.Input(input_param={"shape": {"dim": list(data.shape)}})
    n.output = func(n.data, *args, **kwargs)
    return n


def _miso_op(data_list, func, *args, **kwargs):
    """Create multi input and single output Caffe op"""
    input_shapes = [d.shape for d in data_list]
    logger.debug(f"Creating MISO op, num inputs: {len(data_list)}, shapes: {input_shapes}")
    n = caffe.NetSpec()
    if not isinstance(data_list, (tuple, list)):
        raise TypeError(f"Need tuple or list but get {type(data_list)}")
    input_list = []
    for idx, data in enumerate(data_list):
        n["data" + str(idx)] = L.Input(input_param={"shape": {"dim": list(data.shape)}})
        input_list.append(n["data" + str(idx)])
    n.output = func(*input_list, *args, **kwargs)
    return n


def _simo_op(data, func, *args, **kwargs):
    """Create single input and multi output Caffe op"""
    logger.debug(f"Creating SIMO op, input shape: {data.shape}")
    n = caffe.NetSpec()
    n.data = L.Input(input_param={"shape": {"dim": list(data.shape)}})
    output_list = func(n.data, *args, **kwargs)
    logger.debug(f"SIMO op num outputs: {len(output_list)}")
    for idx, out in enumerate(output_list):
        n["output" + str(idx)] = out
    return n


def _run_caffe(data, proto_file, blob_file):
    """Run caffe model by Caffe according to .caffemodel and .prototxt"""
    logger.info(f"Starting Caffe inference, proto: {proto_file}, blob: {blob_file}")
    try:
        if isinstance(data, (list, tuple)):
            input_shapes = [d.shape for d in data]
            logger.debug(f"Input data is list, num inputs: {len(data)}, shapes: {input_shapes}")
        else:
            logger.debug(f"Input data shape: {data.shape}")
        net = caffe.Net(proto_file, blob_file, caffe.TEST)
        if isinstance(data, (list, tuple)):
            for idx, d in enumerate(data):
                net.blobs["data" + str(idx)].data[...] = d
        else:
            net.blobs["data"].data[...] = data
        out = net.forward()

        caffe_output = []
        for i in range(len(out.keys())):
            if "output" + str(i) not in out.keys():
                caffe_output.clear()
                result = list(out.values())
                out_shapes = [v.shape for v in result]
                logger.info(f"Caffe inference completed, output shapes: {out_shapes}")
                return result
            caffe_output.append(out["output" + str(i)])
        out_shapes = [o.shape for o in caffe_output]
        logger.info(f"Caffe inference completed, output shapes: {out_shapes}")
        return caffe_output
    except Exception as e:
        logger.error(f"Error running Caffe inference: {e}", exc_info=True)
        raise


def _validate_reshape_params(data, reshape_param):
    """
    Pre-validate Reshape parameters in Python before calling C++ layer.
    Converts C++ CHECK failures (SIGABRT) into Python ValueError with clear messages.
    
    Corresponds to reshape_layer.cpp CHECK_EQ(top[0]->count(), bottom[0]->count()).
    
    Caffe Reshape logic:
    - Output shape = input[:axis] + resolved_dims + input[axis+num_axes:]
    - 0 in dim[i] = copy input axis size from position axis+i (requires i < num_axes)
    - -1 in dim[i] = infer this dimension (exactly one -1 allowed)
    - dim can have different length than num_axes (this is how rank changes in reshape)
    - Product of resolved dims must equal product of affected input axes
    """
    import numpy as _np
    if isinstance(data, (list, tuple)):
        input_shape = list(data[0].shape)
    else:
        input_shape = list(data.shape)
    
    shape_spec = reshape_param.get("shape", {})
    dim = list(shape_spec.get("dim", []))
    axis = reshape_param.get("axis", 0)
    num_axes = reshape_param.get("num_axes", -1)
    
    if not dim:
        return
    
    ndim = len(input_shape)
    if axis < 0:
        axis = ndim + axis
    if axis < 0 or axis >= ndim:
        raise ValueError(
            f"Reshape parameter error: axis={axis} out of range for input_shape={input_shape}"
        )
    
    if num_axes < 0:
        num_axes = ndim - axis
    if axis + num_axes > ndim:
        raise ValueError(
            f"Reshape parameter error: axis+num_axes={axis+num_axes} exceeds ndim={ndim}"
        )
    
    # Affected input axes (those being reshaped)
    affected_axes = input_shape[axis:axis + num_axes]
    affected_count = int(_np.prod(affected_axes)) if affected_axes else 1
    
    # Count -1 occurrences
    num_minus_one = dim.count(-1)
    if num_minus_one > 1:
        raise ValueError(
            f"Reshape parameter error: multiple -1 in dim={dim} (at most one allowed)"
        )
    
    # Compute product of resolved dims:
    # - d > 0: multiply by d
    # - d == 0: multiply by affected_axes[i] (copy from input); requires i < num_axes
    # - d == -1: skip (infer later)
    constant_count = 1
    for i, d in enumerate(dim):
        if d == -1:
            continue
        elif d == 0:
            if i >= num_axes:
                raise ValueError(
                    f"Reshape parameter error: dim[0] at position {i} is outside "
                    f"the affected axis range (num_axes={num_axes}). "
                    f"dim={dim}, axis={axis}, num_axes={num_axes}"
                )
            constant_count *= affected_axes[i]
        elif d > 0:
            constant_count *= d
        else:
            raise ValueError(
                f"Reshape parameter error: invalid dim value {d} at position {i} in {dim}"
            )
    
    if num_minus_one == 1:
        if affected_count % constant_count != 0:
            raise ValueError(
                f"Reshape parameter error: cannot infer -1 dimension. "
                f"Affected axes {affected_axes} have {affected_count} elements, "
                f"explicit product is {constant_count} (not a divisor). "
                f"dim={dim}, axis={axis}, num_axes={num_axes}, input_shape={input_shape}. "
                f"This would trigger SIGABRT in C++ reshape_layer CHECK_EQ."
            )
    else:
        if constant_count != affected_count:
            raise ValueError(
                f"Reshape parameter error: element count mismatch. "
                f"Affected axes {affected_axes} have {affected_count} elements, "
                f"but resolved dim product is {constant_count}. "
                f"dim={dim}, axis={axis}, num_axes={num_axes}, input_shape={input_shape}. "
                f"This would trigger SIGABRT in C++ reshape_layer CHECK_EQ."
            )

def _test_op(data, func_op, op_name, test_dir, **kwargs):
    """Single op testing pipeline (Caffe-only, no TVM comparison)."""
    logger.info(f"Testing operator: {op_name}")
    logger.debug(f"Test parameters - test_dir: {test_dir}, kwargs: {kwargs}")

    # --- Reshape parameter pre-validation (prevents SIGABRT from C++ CHECK failure) ---
    if op_name == "Reshape" and "reshape_param" in kwargs:
        _validate_reshape_params(data, kwargs["reshape_param"])

    try:
        shape_list = []
        if isinstance(data, (list, tuple)):
            n = _miso_op(data, func_op, **kwargs)
            for d in data:
                shape_list.extend(list(d.shape))
        else:
            output_num = 1
            if "ntop" in kwargs:
                output_num = kwargs["ntop"]
            if output_num == 1:
                n = _siso_op(data, func_op, **kwargs)
            else:
                n = _simo_op(data, func_op, **kwargs)
            shape_list = list(data.shape)

        (proto_file, blob_file, solver_file) = _gen_filename_str(op_name, shape_list, test_dir, **kwargs)
        _gen_model_files(n, proto_file, blob_file, solver_file)
        caffe_out = _run_caffe(data, proto_file, blob_file)
        logger.info(f"Testing operator {op_name} completed")
        return caffe_out
    except Exception as e:
        logger.error(f"Error testing operator {op_name}: {e}", exc_info=True)
        raise


def assert_op_correct(caffe_out, ref_out, atol=1e-5, rtol=1e-4, op_name=""):
    """
    Compare Caffe output with numpy reference implementation using np.allclose.
    
    Args:
        caffe_out: Caffe operator output (numpy array or list of arrays)
        ref_out: Numpy reference output (numpy array or list of arrays)
        atol: Absolute tolerance for np.allclose
        rtol: Relative tolerance for np.allclose
        op_name: Operator name for error messages
    
    Raises:
        AssertionError: If outputs don't match within tolerance, showing max error
    """
    logger.debug(f"Verifying correctness for op: {op_name or 'unknown'}, atol={atol}, rtol={rtol}")
    
    def _compare_single(a, b):
        a_np = np.asarray(a)
        b_np = np.asarray(b)
        if a_np.shape != b_np.shape:
            raise AssertionError(
                f"Shape mismatch for {op_name or 'op'}: "
                f"caffe_out shape {a_np.shape} vs ref_out shape {b_np.shape}"
            )
        close_mask = np.isclose(a_np, b_np, atol=atol, rtol=rtol)
        if not np.all(close_mask):
            max_abs_err = np.max(np.abs(a_np - b_np))
            max_rel_err = np.max(np.abs(a_np - b_np) / (np.abs(b_np) + 1e-10))
            err_idx = np.unravel_index(np.argmax(np.abs(a_np - b_np)), a_np.shape)
            raise AssertionError(
                f"Output mismatch for {op_name or 'op'}: "
                f"max absolute error = {max_abs_err:.2e}, "
                f"max relative error = {max_rel_err:.2e}, "
                f"atol={atol}, rtol={rtol}, "
                f"error location (flattened index argmax): {err_idx}, "
                f"caffe value = {a_np[err_idx]}, ref value = {b_np[err_idx]}"
            )
        return True
    
    if isinstance(caffe_out, (list, tuple)) and isinstance(ref_out, (list, tuple)):
        if len(caffe_out) != len(ref_out):
            raise AssertionError(
                f"Output count mismatch for {op_name or 'op'}: "
                f"{len(caffe_out)} vs {len(ref_out)}"
            )
        for i, (c, r) in enumerate(zip(caffe_out, ref_out)):
            _compare_single(c, r)
    elif isinstance(caffe_out, (list, tuple)) and len(caffe_out) == 1 and not isinstance(ref_out, (list, tuple)):
        _compare_single(caffe_out[0], ref_out)
    else:
        _compare_single(caffe_out, ref_out)
    
    logger.info(f"Correctness check passed for {op_name or 'op'}")


class Timer:
    """
    Context manager for performance timing.
    
    Usage:
        with Timer() as t:
            # code to time
        print(f"Elapsed: {t.elapsed} seconds")
    """
    
    def __init__(self, name=""):
        self.name = name
        self.elapsed = 0.0
        self._start = None
    
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self._start
        if self.name:
            logger.debug(f"Timer [{self.name}] elapsed: {self.elapsed:.6f}s")


def get_memory_usage():
    """
    Get current memory usage in bytes using tracemalloc.
    
    Returns:
        tuple: (current_memory, peak_memory) in bytes
    """
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    current, peak = tracemalloc.get_traced_memory()
    return current, peak


def check_memory_leak(func, runs=5, *args, **kwargs):
    """
    Check for memory leaks by running a function multiple times and tracking memory growth.
    
    Args:
        func: Callable to test
        runs: Number of consecutive runs
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
    
    Returns:
        dict: Memory usage statistics with keys:
            - 'memory_per_run': List of memory usage (bytes) after each run
            - 'has_leak': Boolean indicating if continuous growth detected
            - 'growth_rate': Average bytes increase per run
            - 'peak_memory': Peak memory usage across all runs
    
    Raises:
        RuntimeError: If significant memory leak is detected
    """
    logger.debug(f"Checking memory leak for {func.__name__} with {runs} runs")
    
    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()
    
    tracemalloc.reset_peak()
    memory_per_run = []
    
    for i in range(runs):
        func(*args, **kwargs)
        current, _ = tracemalloc.get_traced_memory()
        memory_per_run.append(current)
    
    _, peak = tracemalloc.get_traced_memory()
    
    if len(memory_per_run) >= 3:
        first_half = memory_per_run[:runs//2]
        second_half = memory_per_run[runs//2:]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        growth = avg_second - avg_first
        growth_rate = growth / (runs // 2)
        has_leak = growth_rate > 1024 * 100
    else:
        growth = memory_per_run[-1] - memory_per_run[0]
        growth_rate = growth / max(runs - 1, 1)
        has_leak = growth_rate > 1024 * 100
    
    if not was_tracing:
        tracemalloc.stop()
    
    result = {
        'memory_per_run': memory_per_run,
        'has_leak': has_leak,
        'growth_rate': growth_rate,
        'peak_memory': peak,
    }
    
    if has_leak:
        logger.warning(
            f"Potential memory leak detected in {func.__name__}: "
            f"avg growth = {growth_rate:.2f} bytes/run over {runs} runs"
        )
    else:
        logger.debug(
            f"No memory leak detected in {func.__name__}: "
            f"avg growth = {growth_rate:.2f} bytes/run"
        )
    
    return result


class TestResultCollector:
    """
    Collector for test results including correctness, performance, and memory tests.
    """
    
    def __init__(self):
        self.results = {
            'correctness': [],
            'performance': [],
            'memory': [],
        }
    
    def add_result(self, category, name, passed, details=None):
        """
        Add a test result.
        
        Args:
            category: One of 'correctness', 'performance', 'memory'
            name: Test/operator name
            passed: Boolean indicating if test passed
            details: Optional dict with additional details (e.g., elapsed time, error)
        """
        if category not in self.results:
            raise ValueError(f"Unknown category: {category}. Must be one of {list(self.results.keys())}")
        
        result = {
            'name': name,
            'passed': passed,
            'details': details or {},
        }
        self.results[category].append(result)
        logger.debug(f"Added {category} result for {name}: passed={passed}")
    
    def get_summary(self):
        """
        Get a summary of all test results.
        
        Returns:
            dict: Summary with counts per category and overall pass/fail status
        """
        summary = {}
        total_passed = 0
        total_tests = 0
        
        for category, results in self.results.items():
            passed = sum(1 for r in results if r['passed'])
            total = len(results)
            summary[category] = {
                'total': total,
                'passed': passed,
                'failed': total - passed,
                'pass_rate': passed / total if total > 0 else 0.0,
                'results': results,
            }
            total_passed += passed
            total_tests += total
        
        summary['overall'] = {
            'total': total_tests,
            'passed': total_passed,
            'failed': total_tests - total_passed,
            'pass_rate': total_passed / total_tests if total_tests > 0 else 0.0,
            'all_passed': total_passed == total_tests,
        }
        
        logger.info(
            f"Test summary - total: {total_tests}, passed: {total_passed}, "
            f"failed: {total_tests - total_passed}, "
            f"pass rate: {summary['overall']['pass_rate']:.1%}"
        )
        
        return summary
