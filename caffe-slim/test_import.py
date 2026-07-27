import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))

tvm_ffi_path = os.path.join(VENDOR_DIR, 'tvm-ffi', 'python')
caffe_py_path = os.path.join(SCRIPT_DIR, 'python')

print("SCRIPT_DIR:", SCRIPT_DIR)
print("VENDOR_DIR:", VENDOR_DIR)
print("tvm_ffi_path:", tvm_ffi_path)
print("tvm_ffi exists:", os.path.exists(tvm_ffi_path))
print("caffe_py_path:", caffe_py_path)
print("caffe package exists:", os.path.exists(os.path.join(caffe_py_path, 'caffe')))

sys.path.insert(0, tvm_ffi_path)
sys.path.insert(0, caffe_py_path)
sys.path.insert(0, SCRIPT_DIR)

print("\nsys.path entries with 'vendor':")
for p in sys.path:
    if 'vendor' in p:
        print(" ", p)

try:
    import tvm_ffi
    print("\ntvm_ffi imported successfully!")
    print("tvm_ffi version:", tvm_ffi.__version__)
except ImportError as e:
    print("\nFailed to import tvm_ffi:", e)

try:
    import caffe
    print("caffe imported successfully!")
    print("caffe version:", caffe.version())
except ImportError as e:
    print("Failed to import caffe:", e)
