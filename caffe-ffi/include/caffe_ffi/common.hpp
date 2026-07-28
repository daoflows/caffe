#ifndef CAFFE_FFI_COMMON_HPP_
#define CAFFE_FFI_COMMON_HPP_

#include <cstdint>
#include <cstring>
#include <memory>
#include <string>
#include <vector>

#include <tvm/ffi/tvm_ffi.h>

#include "caffe_ffi/log.hpp"

namespace caffe_ffi {

using namespace tvm::ffi;

class Blob;
class Layer;

using BlobVec = std::vector<ObjectPtr<Blob>>;
using LayerVec = std::vector<ObjectPtr<Layer>>;

constexpr int kMaxBlobAxes = 32;

struct CPUMemAlloc {
  void AllocData(DLTensor* tensor) {
    size_t nbytes = tvm::ffi::GetDataSize(*tensor);
    CAFFE_FFI_MEM_LOG << "AllocData: allocating " << nbytes << " bytes"
                      << " (ndim=" << tensor->ndim
                      << ", dtype=" << tensor->dtype.code << ":" << tensor->dtype.bits
                      << ", device_type=" << tensor->device.device_type << ")";
    tensor->data = std::malloc(nbytes);
    TVM_FFI_ICHECK(tensor->data != nullptr) << "Failed to allocate CPU memory of size " << nbytes;
    std::memset(tensor->data, 0, nbytes);
    CAFFE_FFI_MEM_LOG << "AllocData: allocated at " << tensor->data << " (" << nbytes << " bytes, zero-initialized)";
  }
  void FreeData(DLTensor* tensor) {
    if (tensor->data) {
      CAFFE_FFI_MEM_LOG << "FreeData: freeing memory at " << tensor->data;
      std::free(tensor->data);
      tensor->data = nullptr;
      CAFFE_FFI_MEM_LOG << "FreeData: memory freed, data pointer reset to nullptr";
    } else {
      CAFFE_FFI_MEM_LOG << "FreeData: data is already nullptr, skipping";
    }
  }
};

inline DLDevice CPU() {
  DLDevice dev;
  dev.device_type = kDLCPU;
  dev.device_id = 0;
  return dev;
}

inline DLDataType Float32() {
  DLDataType dtype;
  dtype.code = kDLFloat;
  dtype.bits = 32;
  dtype.lanes = 1;
  return dtype;
}

inline Tensor NewCPUTensor(ShapeView shape) {
  return Tensor::FromNDAlloc(CPUMemAlloc(), shape, Float32(), CPU());
}

}  // namespace caffe_ffi

#endif  // CAFFE_FFI_COMMON_HPP_
