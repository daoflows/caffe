from __future__ import annotations

from typing import List

from ._core import Layer, Blob


@property
def layer_type(self) -> str:
    """Get layer type string."""
    return self.type


def layer_repr(self) -> str:
    name = self.name
    if name:
        return f"Layer(name='{name}', type='{self.type}')"
    return f"Layer(type='{self.type}')"


def _patch_layer():
    """Apply monkey patches to Layer class."""
    Layer.__repr__ = layer_repr


_patch_layer()
