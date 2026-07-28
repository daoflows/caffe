#include <tvm/ffi/tvm_ffi.h>

#include <fstream>
#include <memory>
#include <sstream>
#include <string>

#include <google/protobuf/text_format.h>

#include "caffe_ffi/blob.hpp"
#include "caffe_ffi/layer.hpp"
#include "caffe_ffi/layer_factory.hpp"
#include "caffe_ffi/net.hpp"
#include "caffe_ffi/fill.hpp"
#include "caffe_ffi/log.hpp"
#include "caffe_ffi/backtrace.hpp"

#include "caffe_ffi/layers/input_layer.hpp"
#include "caffe_ffi/layers/relu_layer.hpp"
#include "caffe_ffi/layers/inner_product_layer.hpp"
#include "caffe_ffi/layers/softmax_layer.hpp"
#include "caffe_ffi/layers/flatten_layer.hpp"
#include "caffe_ffi/layers/conv_layer.hpp"
#include "caffe_ffi/layers/pooling_layer.hpp"
#include "caffe_ffi/layers/batch_norm_layer.hpp"
#include "caffe_ffi/layers/scale_layer.hpp"
#include "caffe_ffi/layers/bias_layer.hpp"
#include "caffe_ffi/layers/softmax_loss_layer.hpp"
#include "caffe_ffi/layers/accuracy_layer.hpp"

#include "caffe_ffi/layers/sigmoid_layer.hpp"
#include "caffe_ffi/layers/tanh_layer.hpp"
#include "caffe_ffi/layers/prelu_layer.hpp"
#include "caffe_ffi/layers/elu_layer.hpp"
#include "caffe_ffi/layers/dropout_layer.hpp"
#include "caffe_ffi/layers/concat_layer.hpp"
#include "caffe_ffi/layers/eltwise_layer.hpp"
#include "caffe_ffi/layers/reshape_layer.hpp"

#include "caffe/proto/caffe.pb.h"

#ifndef CAFFE_FFI_VERSION
#define CAFFE_FFI_VERSION "0.1.0"
#endif

namespace caffe_ffi {

const char* Version() {
  return CAFFE_FFI_VERSION;
}

ObjectPtr<Blob> NewBlob() {
  return make_object<Blob>();
}

ObjectPtr<Blob> NewBlobFromShape(const Array<int64_t>& shape) {
  std::vector<int64_t> sv;
  for (size_t i = 0; i < shape.size(); ++i) {
    sv.push_back(shape[i]);
  }
  return make_object<Blob>(ShapeView(sv.data(), sv.size()));
}

ObjectPtr<Net> NewNetFromProtoString(const std::string& proto_text) {
  caffe::NetParameter param;
  bool success = google::protobuf::TextFormat::ParseFromString(proto_text, &param);
  TVM_FFI_ICHECK(success) << "Failed to parse NetParameter from text format";
  return make_object<Net>(param);
}

ObjectPtr<Net> NewNetFromFile(const std::string& filename) {
  std::ifstream ifs(filename);
  TVM_FFI_ICHECK(ifs.good()) << "Failed to open net file: " << filename;
  std::stringstream ss;
  ss << ifs.rdbuf();
  caffe::NetParameter param;
  bool success = google::protobuf::TextFormat::ParseFromString(ss.str(), &param);
  TVM_FFI_ICHECK(success) << "Failed to parse prototxt: " << filename;
  return make_object<Net>(param);
}

Array<String> LayerTypeList() {
  auto types = LayerRegistry::LayerTypeList();
  Array<String> result;
  for (const auto& t : types) {
    result.push_back(String(t));
  }
  return result;
}

void SetLogLevel(int level) {
  using caffe_ffi::log::Level;
  if (level < 0) level = 0;
  if (level > 4) level = 4;
  caffe_ffi::log::SetLevel(static_cast<Level>(level));
}

int GetLogLevel() {
  return static_cast<int>(caffe_ffi::log::GetLevel());
}

int64_t TotalAllocatedBytesGlobal() {
  return TotalAllocatedBytes();
}

int64_t LiveBlobCountGlobal() {
  return LiveBlobCount();
}

std::string GetBacktraceString(int skip_frames, int max_frames) {
  return backtrace::GetBacktrace(skip_frames + 1, max_frames);
}

Tensor BlobDataTensor(ObjectPtr<Blob> blob) {
  CAFFE_FFI_MEM_LOG << "FFI BlobDataTensor blob=" << blob.get()
                    << " returning data_tensor view";
  return blob->data_tensor();
}

Tensor BlobDiffTensor(ObjectPtr<Blob> blob) {
  CAFFE_FFI_MEM_LOG << "FFI BlobDiffTensor blob=" << blob.get()
                    << " returning diff_tensor view";
  return blob->diff_tensor();
}

void BlobUpdate(ObjectPtr<Blob> blob) {
  CAFFE_FFI_MEM_LOG << "FFI BlobUpdate blob=" << blob.get();
  blob->Update();
}

TVM_FFI_STATIC_INIT_BLOCK() {
  namespace refl = tvm::ffi::reflection;
  refl::GlobalDef()
      .def("caffe_ffi.Version", Version)
      .def("caffe_ffi.NewBlob", NewBlob)
      .def("caffe_ffi.NewBlobFromShape", NewBlobFromShape)
      .def("caffe_ffi.NewNetFromProtoString", NewNetFromProtoString)
      .def("caffe_ffi.NewNetFromFile", NewNetFromFile)
      .def("caffe_ffi.LayerTypeList", LayerTypeList)
      .def("caffe_ffi.SetLogLevel", SetLogLevel)
      .def("caffe_ffi.GetLogLevel", GetLogLevel)
      .def("caffe_ffi.TotalAllocatedBytes", TotalAllocatedBytesGlobal)
      .def("caffe_ffi.LiveBlobCount", LiveBlobCountGlobal)
      .def("caffe_ffi.GetBacktrace", GetBacktraceString)
      .def("caffe_ffi.BlobDataTensor", BlobDataTensor)
      .def("caffe_ffi.BlobDiffTensor", BlobDiffTensor)
      .def("caffe_ffi.BlobUpdate", BlobUpdate);

  refl::ObjectDef<Blob>()
      .def(refl::init<>())
      .def("shape", static_cast<Shape (Blob::*)() const>(&Blob::shape))
      .def("shape_at", static_cast<int64_t (Blob::*)(int) const>(&Blob::shape))
      .def("num_axes", &Blob::num_axes)
      .def("count", static_cast<int64_t (Blob::*)() const>(&Blob::count))
      .def("Reshape", static_cast<void (Blob::*)(const Array<int64_t>&)>(&Blob::Reshape))
      .def("get_data", &Blob::get_data)
      .def("set_data", &Blob::set_data)
      .def("get_diff", &Blob::get_diff)
      .def("set_diff", &Blob::set_diff)
      .def("name", &Blob::name)
      .def("set_name", &Blob::set_name)
      .def("construction_backtrace", &Blob::construction_backtrace);

  refl::ObjectDef<Layer>()
      .def("type", &Layer::type)
      .def("blobs_array", &Layer::blobs_array);

  refl::ObjectDef<Net>()
      .def("name", &Net::name)
      .def("Forward", &Net::Forward)
      .def("CopyTrainedLayersFrom", static_cast<void (Net::*)(const std::string&)>(&Net::CopyTrainedLayersFrom))
      .def("blobs_array", &Net::blobs_array)
      .def("layers_array", &Net::layers_array)
      .def("input_blobs_array", &Net::input_blobs_array)
      .def("output_blobs_array", &Net::output_blobs_array)
      .def("blob_by_name", &Net::blob_by_name)
      .def("layer_by_name", &Net::layer_by_name)
      .def("has_blob", &Net::has_blob)
      .def("has_layer", &Net::has_layer)
      .def("num_inputs", &Net::num_inputs)
      .def("num_outputs", &Net::num_outputs)
      .def("input_blob_names", &Net::input_blob_names_array)
      .def("output_blob_names", &Net::output_blob_names_array)
      .def("blob_names", &Net::blob_names_array)
      .def("layer_names", &Net::layer_names_array);
}

TVM_FFI_DLL_EXPORT_TYPED_FUNC(Version, Version)

}  // namespace caffe_ffi
