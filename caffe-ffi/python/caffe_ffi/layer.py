from __future__ import annotations

from typing import List

from ._core import Layer, Blob


@property
def layer_type(self) -> str:
    """Get layer type string."""
    return self.type


@property
def layer_name(self) -> str:
    """Get layer name."""
    if hasattr(self, '_handle') and self._handle is not None:
        if hasattr(self._handle, 'layer_param'):
            return self._handle.layer_param().name()
    return getattr(self, '_name', '')


def layer_repr(self) -> str:
    name = self.name
    if name:
        return f"Layer(name='{name}', type='{self.type}')"
    return f"Layer(type='{self.type}')"


def _patch_layer():
    """Apply monkey patches to Layer class."""
    Layer.name = layer_name
    Layer.__repr__ = layer_repr


_patch_layer()
