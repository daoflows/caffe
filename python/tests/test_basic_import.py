#!/usr/bin/env python3
"""Test script for Caffe slim FFI module."""
import sys
import os
import ctypes

CAFFE_PY = "/mnt/d/spaces/SpecWeave/external/chaos/caffe/python"
TVM_FFI_PY = "/mnt/d/spaces/SpecWeave/external/ffi/tvm-ffi/python"
BUILD_DIR = os.path.join(CAFFE_PY, "build")

sys.path.insert(0, TVM_FFI_PY)
sys.path.insert(0, os.path.join(CAFFE_PY, "python"))
sys.path.insert(0, CAFFE_PY)

os.environ["LD_LIBRARY_PATH"] = os.path.join(BUILD_DIR, "lib") + ":" + os.path.join(BUILD_DIR, "python", "caffe") + ":" + os.environ.get("LD_LIBRARY_PATH", "")

print("Python:", sys.version)
print()
print("Testing tvm_ffi import...")
import tvm_ffi
print("tvm_ffi version:", tvm_ffi.__version__)
print()
print("Testing _caffe.so loading via ctypes...")
lib_path = os.path.join(BUILD_DIR, "python", "caffe", "_caffe.so")
print("Loading:", lib_path)
lib = ctypes.CDLL(lib_path)
print("_caffe.so loaded successfully!")
print()
print("Exported functions (sample):")
for func in ["Net_Init", "Net_Init_Load", "Net_Destroy", "Net_Forward", "Net_Reshape",
             "Net_BlobNames", "Net_InputBlobNames", "Net_OutputBlobNames",
             "Blob_GetShape", "Blob_GetData", "Blob_GetDiff", "Blob_SetData",
             "Net_CopyTrainedLayersFrom",
             "Version", "SetModeCPU", "SetRandomSeed", "LayerTypeList"]:
    try:
        addr = getattr(lib, func, None)
        print(f"  {func}: {'found' if addr else 'NOT FOUND'}")
    except Exception as e:
        print(f"  {func}: error - {e}")

print()
print("Testing Version() function call...")
lib.Version.restype = ctypes.c_char_p
version_str = lib.Version()
print(f"Caffe version: {version_str.decode()}")

print()
print("Testing SetModeCPU()...")
lib.SetModeCPU()
print("SetModeCPU() succeeded!")

print()
print("Testing LayerTypeList...")
print("(Skipping FFI complex type call via ctypes, will test via tvm_ffi)")

print()
print("=" * 60)
print("All basic _caffe.so tests passed!")
print("=" * 60)
