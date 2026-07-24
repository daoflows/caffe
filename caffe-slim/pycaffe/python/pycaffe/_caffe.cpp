// Caffe Slim FFI module (tvm-ffi based)
// This file replaces the old boost::python implementation with tvm-ffi C ABI exports.
// The shared library built from this file can be loaded via tvm_ffi.load_module() from Python.

#include <tvm/ffi/tvm_ffi.h>
#include <tvm/ffi/container/tensor.h>
#include <tvm/ffi/extra/stl.h>

#include <cstring>
#include <string>
#include <vector>
#include <fstream>
#include <memory>

#include "caffe/caffe.hpp"

namespace caffe {

using tvm::ffi::Tensor;
using tvm::ffi::TensorView;
using tvm::ffi::ShapeView;

typedef float Dtype;

static void CheckFile(const std::string& filename) {
    std::ifstream f(filename.c_str());
    if (!f.good()) {
        f.close();
        TVM_FFI_THROW(tvm::ffi::RuntimeError) << "Could not open file " << filename;
    }
    f.close();
}

uintptr_t Net_Init(const std::string& network_file, int phase) {
    CheckFile(network_file);
    auto* net_handle = new std::shared_ptr<Net<Dtype>>(
        new Net<Dtype>(network_file, static_cast<Phase>(phase)));
    return reinterpret_cast<uintptr_t>(net_handle);
}

uintptr_t Net_Init_Load(const std::string& param_file,
                         const std::string& pretrained_param_file,
                         int phase) {
    CheckFile(param_file);
    CheckFile(pretrained_param_file);
    auto* net_handle = new std::shared_ptr<Net<Dtype>>(
        new Net<Dtype>(param_file, static_cast<Phase>(phase)));
    (*net_handle)->CopyTrainedLayersFrom(pretrained_param_file);
    return reinterpret_cast<uintptr_t>(net_handle);
}

void Net_CopyTrainedLayersFrom(uintptr_t handle, const std::string& weights_file) {
    auto* net_handle = reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(handle);
    CheckFile(weights_file);
    (*net_handle)->CopyTrainedLayersFrom(weights_file);
}

void Net_Destroy(uintptr_t handle) {
    auto* net_handle = reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(handle);
    delete net_handle;
}

void Net_Forward(uintptr_t handle) {
    auto* net_handle = reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(handle);
    (*net_handle)->ForwardPrefilled();
}

void Net_Reshape(uintptr_t handle) {
    auto* net_handle = reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(handle);
    (*net_handle)->Reshape();
}

std::vector<std::string> Net_BlobNames(uintptr_t handle) {
    auto* net_handle = reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(handle);
    return (*net_handle)->blob_names();
}

std::vector<int> Blob_GetShape(uintptr_t net_handle, const std::string& blob_name) {
    auto& net = *reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(net_handle);
    auto blob = net->blob_by_name(blob_name);
    TVM_FFI_CHECK(blob != nullptr, tvm::ffi::ValueError)
        << "Unknown blob name: " << blob_name;
    return blob->shape();
}

struct CpuBlobDataAllocator {
    Dtype* data;
    std::shared_ptr<Net<Dtype>> net_keep_alive;

    void AllocData(DLTensor* tensor) {
        tensor->data = data;
    }
    void FreeData(DLTensor* tensor) {
        net_keep_alive.reset();
    }
};

Tensor Blob_GetData(uintptr_t net_handle, const std::string& blob_name) {
    auto& net = *reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(net_handle);
    auto blob = net->blob_by_name(blob_name);
    TVM_FFI_CHECK(blob != nullptr, tvm::ffi::ValueError)
        << "Unknown blob name: " << blob_name;

    Dtype* data_ptr = blob->mutable_cpu_data();
    const std::vector<int>& shape = blob->shape();

    std::vector<int64_t> tensor_shape(shape.begin(), shape.end());
    DLDevice cpu_device{static_cast<DLDeviceType>(kDLCPU), 0};
    DLDataType dtype{static_cast<uint8_t>(kDLFloat), 32, 1};

    return Tensor::FromNDAlloc(
        CpuBlobDataAllocator{data_ptr, net},
        ShapeView(tensor_shape.data(), tensor_shape.size()),
        dtype, cpu_device);
}

Tensor Blob_GetDiff(uintptr_t net_handle, const std::string& blob_name) {
    auto& net = *reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(net_handle);
    auto blob = net->blob_by_name(blob_name);
    TVM_FFI_CHECK(blob != nullptr, tvm::ffi::ValueError)
        << "Unknown blob name: " << blob_name;

    Dtype* diff_ptr = blob->mutable_cpu_diff();
    const std::vector<int>& shape = blob->shape();

    std::vector<int64_t> tensor_shape(shape.begin(), shape.end());
    DLDevice cpu_device{static_cast<DLDeviceType>(kDLCPU), 0};
    DLDataType dtype{static_cast<uint8_t>(kDLFloat), 32, 1};

    return Tensor::FromNDAlloc(
        CpuBlobDataAllocator{diff_ptr, net},
        ShapeView(tensor_shape.data(), tensor_shape.size()),
        dtype, cpu_device);
}

void Blob_SetData(uintptr_t net_handle, const std::string& blob_name,
                  TensorView data) {
    auto& net = *reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(net_handle);
    auto blob = net->blob_by_name(blob_name);
    TVM_FFI_CHECK(blob != nullptr, tvm::ffi::ValueError)
        << "Unknown blob name: " << blob_name;

    DLDataType f32_dtype{static_cast<uint8_t>(kDLFloat), 32, 1};
    TVM_FFI_CHECK(data.dtype() == f32_dtype, tvm::ffi::TypeError)
        << "Input data must be float32 tensor";
    TVM_FFI_CHECK(data.IsContiguous(), tvm::ffi::ValueError)
        << "Input data must be contiguous";

    const std::vector<int>& expected_shape = blob->shape();
    ShapeView data_shape = data.shape();
    TVM_FFI_CHECK(data_shape.size() == static_cast<int64_t>(expected_shape.size()),
                   tvm::ffi::ValueError)
        << "Shape dimension mismatch: expected " << expected_shape.size()
        << ", got " << data_shape.size();

    int64_t numel = 1;
    for (size_t i = 0; i < expected_shape.size(); ++i) {
        TVM_FFI_CHECK(data_shape[i] == static_cast<int64_t>(expected_shape[i]),
                       tvm::ffi::ValueError)
            << "Shape mismatch at dim " << i << ": expected " << expected_shape[i]
            << ", got " << data_shape[i];
        numel *= expected_shape[i];
    }

    Dtype* dst = blob->mutable_cpu_data();
    const Dtype* src = static_cast<const Dtype*>(data.data_ptr());
    std::memcpy(dst, src, static_cast<size_t>(numel) * sizeof(Dtype));
}

std::vector<std::string> Net_InputBlobNames(uintptr_t handle) {
    auto& net = *reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(handle);
    const std::vector<int>& input_indices = net->input_blob_indices();
    const std::vector<std::string>& blob_names = net->blob_names();
    std::vector<std::string> names;
    names.reserve(input_indices.size());
    for (int idx : input_indices) {
        names.push_back(blob_names[idx]);
    }
    return names;
}

std::vector<std::string> Net_OutputBlobNames(uintptr_t handle) {
    auto& net = *reinterpret_cast<std::shared_ptr<Net<Dtype>>*>(handle);
    const std::vector<int>& output_indices = net->output_blob_indices();
    const std::vector<std::string>& blob_names = net->blob_names();
    std::vector<std::string> names;
    names.reserve(output_indices.size());
    for (int idx : output_indices) {
        names.push_back(blob_names[idx]);
    }
    return names;
}

std::vector<std::string> LayerTypeList() {
    return LayerRegistry<Dtype>::LayerTypeList();
}

void SetModeCPU() {
    Caffe::set_mode(Caffe::CPU);
}

void SetRandomSeed(unsigned int seed) {
    Caffe::set_random_seed(seed);
}

const char* Version() {
    return CAFFE_VERSION;
}

TVM_FFI_DLL_EXPORT_TYPED_FUNC(SetModeCPU, SetModeCPU)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(SetRandomSeed, SetRandomSeed)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Version, Version)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(LayerTypeList, LayerTypeList)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Net_Init, Net_Init)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Net_Init_Load, Net_Init_Load)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Net_CopyTrainedLayersFrom, Net_CopyTrainedLayersFrom)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Net_Destroy, Net_Destroy)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Net_Forward, Net_Forward)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Net_Reshape, Net_Reshape)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Net_BlobNames, Net_BlobNames)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Net_InputBlobNames, Net_InputBlobNames)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Net_OutputBlobNames, Net_OutputBlobNames)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Blob_GetShape, Blob_GetShape)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Blob_GetData, Blob_GetData)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Blob_GetDiff, Blob_GetDiff)
TVM_FFI_DLL_EXPORT_TYPED_FUNC(Blob_SetData, Blob_SetData)

}  // namespace caffe
