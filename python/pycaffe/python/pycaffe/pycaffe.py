"""
Wrap the internal caffe C++ module (_caffe.so) with a clean, Pythonic
interface.
"""

import logging
import time
from collections import OrderedDict
from itertools import zip_longest
import numpy as np

from ._caffe import Net, SGDSolver, NesterovSolver, AdaGradSolver, \
        RMSPropSolver, AdaDeltaSolver, AdamSolver, NCCL, Timer
from . import io

logger = logging.getLogger(__name__)

# We directly update methods from Net here (rather than using composition or
# inheritance) so that nets created by caffe (e.g., by SGDSolver) will
# automatically have the improved interface.


@property
def _Net_blobs(self):
    """
    An OrderedDict (bottom to top, i.e., input to output) of network
    blobs indexed by name
    """
    if not hasattr(self, '_blobs_dict'):
        self._blobs_dict = OrderedDict(zip(self._blob_names, self._blobs))
    return self._blobs_dict


@property
def _Net_blob_loss_weights(self):
    """
    An OrderedDict (bottom to top, i.e., input to output) of network
    blob loss weights indexed by name
    """
    if not hasattr(self, '_blobs_loss_weights_dict'):
        self._blob_loss_weights_dict = OrderedDict(zip(self._blob_names,
                                                       self._blob_loss_weights))
    return self._blob_loss_weights_dict

@property
def _Net_layer_dict(self):
    """
    An OrderedDict (bottom to top, i.e., input to output) of network
    layers indexed by name
    """
    if not hasattr(self, '_layer_dict'):
        self._layer_dict = OrderedDict(zip(self._layer_names, self.layers))
    return self._layer_dict


@property
def _Net_params(self):
    """
    An OrderedDict (bottom to top, i.e., input to output) of network
    parameters indexed by name; each is a list of multiple blobs (e.g.,
    weights and biases)
    """
    if not hasattr(self, '_params_dict'):
        self._params_dict = OrderedDict([(name, lr.blobs)
                                        for name, lr in zip(
                                            self._layer_names, self.layers)
                                        if len(lr.blobs) > 0])
    return self._params_dict


@property
def _Net_inputs(self):
    if not hasattr(self, '_input_list'):
        keys = list(self.blobs.keys())
        self._input_list = [keys[i] for i in self._inputs]
    return self._input_list


@property
def _Net_outputs(self):
    if not hasattr(self, '_output_list'):
        keys = list(self.blobs.keys())
        self._output_list = [keys[i] for i in self._outputs]
    return self._output_list


def _Net_forward(self, blobs=None, start=None, end=None, **kwargs):
    """
    Forward pass: prepare inputs and run the net forward.

    Parameters
    ----------
    blobs : list of blobs to return in addition to output blobs.
    kwargs : Keys are input blob names and values are blob ndarrays.
             For formatting inputs for Caffe, see Net.preprocess().
             If None, input is taken from data layers.
    start : optional name of layer at which to begin the forward pass
    end : optional name of layer at which to finish the forward pass
          (inclusive)

    Returns
    -------
    outs : {blob name: blob ndarray} dict.
    """
    t_start = time.perf_counter()

    if blobs is None:
        blobs = []

    if start is not None:
        start_ind = list(self._layer_names).index(start)
    else:
        start_ind = 0

    if end is not None:
        end_ind = list(self._layer_names).index(end)
        outputs = set(self.top_names[end] + blobs)
    else:
        end_ind = len(self.layers) - 1
        outputs = set(self.outputs + blobs)

    logger.info(f"[forward] start_layer='{self._layer_names[start_ind]}'({start_ind}), "
                f"end_layer='{self._layer_names[end_ind]}'({end_ind}), "
                f"output_blobs={sorted(outputs)}, num_extra_blobs={len(blobs)}")

    if kwargs:
        if set(kwargs.keys()) != set(self.inputs):
            raise Exception('Input blob arguments do not match net inputs.')
        logger.info(f"[forward] feeding {len(kwargs)} input(s):")
        for in_, blob in kwargs.items():
            expected_shape = tuple(self.blobs[in_].shape)
            logger.info(f"[forward]   input '{in_}': provided shape={tuple(blob.shape)}, "
                        f"expected shape={expected_shape}, dtype={blob.dtype}")
            if blob.shape[0] != self.blobs[in_].shape[0]:
                logger.error(f"[forward]   batch size mismatch! Input batch={blob.shape[0]}, "
                             f"expected={self.blobs[in_].shape[0]}")
                raise Exception('Input is not batch sized')
            self.blobs[in_].data[...] = blob
    else:
        logger.info("[forward] no external inputs provided; using data from network layers")

    t_cpp = time.perf_counter()
    self._forward(start_ind, end_ind)
    t_cpp_end = time.perf_counter()

    # Unpack blobs to extract
    outs = {out: self.blobs[out].data for out in outputs}

    logger.info(f"[forward] output blobs:")
    for name, data in outs.items():
        arr = np.asarray(data)
        logger.info(f"[forward]   '{name}': shape={arr.shape}, dtype={arr.dtype}, "
                    f"min={arr.min():.6f}, max={arr.max():.6f}, mean={arr.mean():.6f}")

    elapsed = time.perf_counter() - t_start
    cpp_elapsed = t_cpp_end - t_cpp
    logger.info(f"[forward] completed in {elapsed*1000:.2f}ms (C++ forward: {cpp_elapsed*1000:.2f}ms)")
    return outs


def _Net_backward(self, diffs=None, start=None, end=None, **kwargs):
    """
    Backward pass: prepare diffs and run the net backward.

    Parameters
    ----------
    diffs : list of diffs to return in addition to bottom diffs.
    kwargs : Keys are output blob names and values are diff ndarrays.
            If None, top diffs are taken from forward loss.
    start : optional name of layer at which to begin the backward pass
    end : optional name of layer at which to finish the backward pass
        (inclusive)

    Returns
    -------
    outs: {blob name: diff ndarray} dict.
    """
    t_start = time.perf_counter()

    if diffs is None:
        diffs = []

    if start is not None:
        start_ind = list(self._layer_names).index(start)
    else:
        start_ind = len(self.layers) - 1

    if end is not None:
        end_ind = list(self._layer_names).index(end)
        outputs = set(self.bottom_names[end] + diffs)
    else:
        end_ind = 0
        outputs = set(self.inputs + diffs)

    logger.info(f"[backward] start_layer='{self._layer_names[start_ind]}'({start_ind}), "
                f"end_layer='{self._layer_names[end_ind]}'({end_ind}), "
                f"output_diffs={sorted(outputs)}, num_extra_diffs={len(diffs)}")

    if kwargs:
        if set(kwargs.keys()) != set(self.outputs):
            raise Exception('Top diff arguments do not match net outputs.')
        logger.info(f"[backward] setting {len(kwargs)} output diff(s):")
        for top, diff in kwargs.items():
            expected_shape = tuple(self.blobs[top].shape)
            logger.info(f"[backward]   top '{top}': diff shape={tuple(diff.shape)}, "
                        f"expected shape={expected_shape}, dtype={diff.dtype}")
            if diff.shape[0] != self.blobs[top].shape[0]:
                logger.error(f"[backward]   batch size mismatch! Diff batch={diff.shape[0]}, "
                             f"expected={self.blobs[top].shape[0]}")
                raise Exception('Diff is not batch sized')
            self.blobs[top].diff[...] = diff
    else:
        logger.info("[backward] no external diffs provided; using diffs from forward pass (loss layers)")

    t_cpp = time.perf_counter()
    self._backward(start_ind, end_ind)
    t_cpp_end = time.perf_counter()

    # Unpack diffs to extract
    outs = {out: self.blobs[out].diff for out in outputs}

    logger.info(f"[backward] output diffs:")
    for name, diff_arr in outs.items():
        arr = np.asarray(diff_arr)
        has_grad = np.any(arr != 0)
        logger.info(f"[backward]   '{name}': shape={arr.shape}, dtype={arr.dtype}, "
                    f"min={arr.min():.6f}, max={arr.max():.6f}, mean={arr.mean():.6f}, "
                    f"nonzero={has_grad}")

    elapsed = time.perf_counter() - t_start
    cpp_elapsed = t_cpp_end - t_cpp
    logger.info(f"[backward] completed in {elapsed*1000:.2f}ms (C++ backward: {cpp_elapsed*1000:.2f}ms)")
    return outs


def _Net_forward_all(self, blobs=None, **kwargs):
    """
    Run net forward in batches.

    Parameters
    ----------
    blobs : list of blobs to extract as in forward()
    kwargs : Keys are input blob names and values are blob ndarrays.
             Refer to forward().

    Returns
    -------
    all_outs : {blob name: list of blobs} dict.
    """
    t_start = time.perf_counter()
    num_samples = len(next(iter(kwargs.values())))
    batch_size = next(iter(self.blobs.values())).shape[0]
    logger.info(f"[forward_all] processing {num_samples} samples with batch_size={batch_size}")

    # Collect outputs from batches
    all_outs = {out: [] for out in set(self.outputs + (blobs or []))}
    batch_idx = 0
    for batch in self._batch(kwargs):
        actual_batch = next(iter(batch.values())).shape[0]
        logger.info(f"[forward_all] batch {batch_idx}: size={actual_batch}")
        outs = self.forward(blobs=blobs, **batch)
        for out, out_blob in outs.items():
            all_outs[out].extend(out_blob.copy())
        batch_idx += 1
    # Package in ndarray.
    for out in all_outs:
        all_outs[out] = np.asarray(all_outs[out])
    # Discard padding.
    pad = len(next(iter(all_outs.values()))) - len(next(iter(kwargs.values())))
    if pad:
        logger.info(f"[forward_all] discarding {pad} padding samples")
        for out in all_outs:
            all_outs[out] = all_outs[out][:-pad]

    elapsed = time.perf_counter() - t_start
    logger.info(f"[forward_all] completed in {elapsed*1000:.2f}ms, "
                f"{batch_idx} batches, outputs={list(all_outs.keys())}")
    return all_outs


def _Net_forward_backward_all(self, blobs=None, diffs=None, **kwargs):
    """
    Run net forward + backward in batches.

    Parameters
    ----------
    blobs: list of blobs to extract as in forward()
    diffs: list of diffs to extract as in backward()
    kwargs: Keys are input (for forward) and output (for backward) blob names
            and values are ndarrays. Refer to forward() and backward().
            Prefilled variants are called for lack of input or output blobs.

    Returns
    -------
    all_blobs: {blob name: blob ndarray} dict.
    all_diffs: {blob name: diff ndarray} dict.
    """
    t_start = time.perf_counter()
    num_samples = len(next(iter(kwargs.values())))
    batch_size = next(iter(self.blobs.values())).shape[0]
    logger.info(f"[forward_backward_all] {num_samples} samples, batch_size={batch_size}")

    # Batch blobs and diffs.
    all_outs = {out: [] for out in set(self.outputs + (blobs or []))}
    all_diffs = {diff: [] for diff in set(self.inputs + (diffs or []))}
    forward_batches = self._batch({in_: kwargs[in_]
                                   for in_ in self.inputs if in_ in kwargs})
    backward_batches = self._batch({out: kwargs[out]
                                    for out in self.outputs if out in kwargs})
    # Collect outputs from batches (and heed lack of forward/backward batches).
    batch_idx = 0
    for fb, bb in zip_longest(forward_batches, backward_batches, fillvalue={}):
        fb_info = {k: tuple(v.shape) for k, v in fb.items()} if fb else "(empty)"
        bb_info = {k: tuple(v.shape) for k, v in bb.items()} if bb else "(empty)"
        logger.info(f"[forward_backward_all] batch {batch_idx}: forward={fb_info}, backward={bb_info}")
        batch_blobs = self.forward(blobs=blobs, **fb)
        batch_diffs = self.backward(diffs=diffs, **bb)
        for out, out_blobs in batch_blobs.items():
            all_outs[out].extend(out_blobs.copy())
        for diff, out_diffs in batch_diffs.items():
            all_diffs[diff].extend(out_diffs.copy())
        batch_idx += 1
    # Package in ndarray.
    for out, diff in zip(all_outs, all_diffs):
        all_outs[out] = np.asarray(all_outs[out])
        all_diffs[diff] = np.asarray(all_diffs[diff])
    # Discard padding at the end and package in ndarray.
    pad = len(next(iter(all_outs.values()))) - len(next(iter(kwargs.values())))
    if pad:
        logger.info(f"[forward_backward_all] discarding {pad} padding samples")
        for out, diff in zip(all_outs, all_diffs):
            all_outs[out] = all_outs[out][:-pad]
            all_diffs[diff] = all_diffs[diff][:-pad]

    elapsed = time.perf_counter() - t_start
    logger.info(f"[forward_backward_all] completed in {elapsed*1000:.2f}ms, "
                f"{batch_idx} batches, outs={list(all_outs.keys())}, diffs={list(all_diffs.keys())}")
    return all_outs, all_diffs


def _Net_set_input_arrays(self, data, labels):
    """
    Set input arrays of the in-memory MemoryDataLayer.
    (Note: this is only for networks declared with the memory data layer.)
    """
    if labels.ndim == 1:
        labels = np.ascontiguousarray(labels[:, np.newaxis, np.newaxis,
                                             np.newaxis])
    return self._set_input_arrays(data, labels)


def _Net_batch(self, blobs):
    """
    Batch blob lists according to net's batch size.

    Parameters
    ----------
    blobs: Keys blob names and values are lists of blobs (of any length).
           Naturally, all the lists should have the same length.

    Yields
    ------
    batch: {blob name: list of blobs} dict for a single batch.
    """
    num = len(next(iter(blobs.values())))
    batch_size = next(iter(self.blobs.values())).shape[0]
    remainder = num % batch_size
    num_batches = num // batch_size

    # Yield full batches.
    for b in range(num_batches):
        i = b * batch_size
        yield {name: blobs[name][i:i + batch_size] for name in blobs}

    # Yield last padded batch, if any.
    if remainder > 0:
        padded_batch = {}
        for name in blobs:
            padding = np.zeros((batch_size - remainder,)
                               + blobs[name].shape[1:])
            padded_batch[name] = np.concatenate([blobs[name][-remainder:],
                                                 padding])
        yield padded_batch

def _Net_get_id_name(func, field):
    """
    Generic property that maps func to the layer names into an OrderedDict.

    Used for top_names and bottom_names.

    Parameters
    ----------
    func: function id -> [id]
    field: implementation field name (cache)

    Returns
    ------
    A one-parameter function that can be set as a property.
    """
    @property
    def get_id_name(self):
        if not hasattr(self, field):
            id_to_name = list(self.blobs)
            res = OrderedDict([(self._layer_names[i],
                                [id_to_name[j] for j in func(self, i)])
                                for i in range(len(self.layers))])
            setattr(self, field, res)
        return getattr(self, field)
    return get_id_name

# Attach methods to Net.
Net.blobs = _Net_blobs
Net.blob_loss_weights = _Net_blob_loss_weights
Net.layer_dict = _Net_layer_dict
Net.params = _Net_params
Net.forward = _Net_forward
Net.backward = _Net_backward
Net.forward_all = _Net_forward_all
Net.forward_backward_all = _Net_forward_backward_all
Net.set_input_arrays = _Net_set_input_arrays
Net._batch = _Net_batch
Net.inputs = _Net_inputs
Net.outputs = _Net_outputs
Net.top_names = _Net_get_id_name(Net._top_ids, "_top_names")
Net.bottom_names = _Net_get_id_name(Net._bottom_ids, "_bottom_names")