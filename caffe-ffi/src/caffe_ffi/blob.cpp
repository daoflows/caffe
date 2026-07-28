#include "caffe_ffi/blob.hpp"

#include <algorithm>
#include <cmath>
#include <sstream>

#include "caffe_ffi/fill.hpp"
#include "caffe_ffi/log.hpp"
#include "caffe/proto/caffe.pb.h"

namespace caffe_ffi {

namespace {
std::string ShapeToString(ShapeView shape) {
  std::ostringstream oss;
  oss << "(";
  for (size_t i = 0; i < shape.size(); ++i) {
    if (i > 0) oss << ",";
    oss << shape[i];
  }
  oss << ")";
  return oss.str();
}
}  // namespace

Blob::Blob() {
  CAFFE_FFI_BLOB_LOG << "Blob() default constructor";
  Reshape(std::vector<int64_t>{0});
}

Blob::Blob(ShapeView shape) {
  CAFFE_FFI_BLOB_LOG << "Blob(ShapeView) shape=" << ShapeToString(shape);
  Reshape(shape);
}

Blob::Blob(const std::vector<int64_t>& shape) {
  CAFFE_FFI_BLOB_LOG << "Blob(vector) shape=" << ShapeToString(ShapeView(shape.data(), shape.size()));
  Reshape(ShapeView(shape.data(), shape.size()));
}

void Blob::Reshape(ShapeView shape) {
  bool shape_changed = (shape.size() != data_tensor_.ndim());
  if (!shape_changed) {
    for (size_t i = 0; i < shape.size(); ++i) {
      if (shape[i] != data_tensor_.size(static_cast<int>(i))) {
        shape_changed = true;
        break;
      }
    }
  }
  int64_t new_count = 1;
  for (size_t i = 0; i < shape.size(); ++i) {
    new_count *= shape[i];
  }
  int64_t old_count = data_tensor_.defined() ? data_tensor_.numel() : 0;
  if (shape_changed || !data_tensor_.defined()) {
    CAFFE_FFI_TENSOR_LOG << "Reshape: allocating new tensors, shape=" << ShapeToString(shape)
                         << " (old_count=" << old_count << ", new_count=" << new_count << ")";
    data_tensor_ = NewCPUTensor(shape);
    diff_tensor_ = NewCPUTensor(shape);
    CAFFE_FFI_TENSOR_LOG << "Reshape: data_tensor=" << data_tensor_.data_ptr()
                         << ", diff_tensor=" << diff_tensor_.data_ptr();
  } else {
    CAFFE_FFI_TENSOR_LOG << "Reshape: shape unchanged " << ShapeToString(shape)
                         << " (count=" << new_count << "), skipping reallocation";
  }
}

void Blob::Reshape(const std::vector<int64_t>& shape) {
  Reshape(ShapeView(shape.data(), shape.size()));
}

void Blob::Reshape(const Array<int64_t>& shape) {
  std::vector<int64_t> dims(shape.begin(), shape.end());
  Reshape(ShapeView(dims.data(), dims.size()));
}

void Blob::Reshape(const caffe::BlobShape& shape) {
  std::vector<int64_t> dims;
  for (int i = 0; i < shape.dim_size(); ++i) {
    dims.push_back(shape.dim(i));
  }
  Reshape(dims);
}

void Blob::ReshapeLike(const Blob& other) {
  std::vector<int64_t> dims;
  for (int i = 0; i < other.num_axes(); ++i) {
    dims.push_back(other.shape(i));
  }
  Reshape(dims);
}

int64_t Blob::LegacyShape(int index) const {
  if (index >= num_axes()) {
    return 1;
  }
  return shape(index);
}

void Blob::FromProto(const caffe::BlobProto& proto, bool reshape) {
  CAFFE_FFI_CONTAINER_LOG << "FromProto: reshape=" << reshape
                           << " proto.data_size=" << proto.data_size()
                           << " proto.double_data_size=" << proto.double_data_size()
                           << " proto.diff_size=" << proto.diff_size();
  if (reshape) {
    std::vector<int64_t> shape;
    if (proto.has_shape()) {
      for (int i = 0; i < proto.shape().dim_size(); ++i) {
        shape.push_back(proto.shape().dim(i));
      }
    } else {
      if (proto.num() > 0) shape.push_back(proto.num());
      if (proto.channels() > 0) shape.push_back(proto.channels());
      if (proto.height() > 0) shape.push_back(proto.height());
      if (proto.width() > 0) shape.push_back(proto.width());
      if (shape.empty()) shape.push_back(0);
    }
    CAFFE_FFI_TENSOR_LOG << "FromProto: reshaping to " << ShapeToString(ShapeView(shape.data(), shape.size()));
    Reshape(shape);
  }
  float* data_ptr = cpu_data();
  const int data_count = proto.data_size();
  const int double_data_count = proto.double_data_size();
  if (data_count > 0) {
    TVM_FFI_ICHECK_EQ(data_count, count())
        << "Incorrect data size for Blob: expected " << count() << ", got " << data_count;
    CAFFE_FFI_CONTAINER_LOG << "FromProto: copying " << data_count << " float data elements to " << data_ptr;
    std::copy(proto.data().begin(), proto.data().end(), data_ptr);
  } else if (double_data_count > 0) {
    TVM_FFI_ICHECK_EQ(double_data_count, count())
        << "Incorrect double_data size for Blob: expected " << count() << ", got " << double_data_count;
    CAFFE_FFI_CONTAINER_LOG << "FromProto: converting " << double_data_count << " double→float data elements";
    for (int i = 0; i < double_data_count; ++i) {
      data_ptr[i] = static_cast<float>(proto.double_data(i));
    }
  }
  float* diff_ptr = cpu_diff();
  const int diff_count = proto.diff_size();
  const int double_diff_count = proto.double_diff_size();
  if (diff_count > 0) {
    TVM_FFI_ICHECK_EQ(diff_count, count())
        << "Incorrect diff size for Blob: expected " << count() << ", got " << diff_count;
    CAFFE_FFI_CONTAINER_LOG << "FromProto: copying " << diff_count << " float diff elements to " << diff_ptr;
    std::copy(proto.diff().begin(), proto.diff().end(), diff_ptr);
  } else if (double_diff_count > 0) {
    TVM_FFI_ICHECK_EQ(double_diff_count, count())
        << "Incorrect double_diff size for Blob: expected " << count() << ", got " << double_diff_count;
    CAFFE_FFI_CONTAINER_LOG << "FromProto: converting " << double_diff_count << " double→float diff elements";
    for (int i = 0; i < double_diff_count; ++i) {
      diff_ptr[i] = static_cast<float>(proto.double_diff(i));
    }
  } else {
    CAFFE_FFI_CONTAINER_LOG << "FromProto: zeroing diff tensor (" << count() << " elements at " << diff_ptr << ")";
    caffe_set_fp32(static_cast<size_t>(count()), 0.0f, diff_ptr);
  }
  CAFFE_FFI_BLOB_LOG << "FromProto: completed, data_ptr=" << data_ptr << " diff_ptr=" << diff_ptr;
}

void Blob::ToProto(caffe::BlobProto* proto) const {
  proto->Clear();
  auto* shape_proto = proto->mutable_shape();
  shape_proto->clear_dim();
  for (int i = 0; i < num_axes(); ++i) {
    shape_proto->add_dim(shape(i));
  }
  proto->clear_data();
  const float* data_ptr = cpu_data();
  for (int64_t i = 0; i < count(); ++i) {
    proto->add_data(data_ptr[i]);
  }
  proto->clear_diff();
  const float* diff_ptr = cpu_diff();
  for (int64_t i = 0; i < count(); ++i) {
    proto->add_diff(diff_ptr[i]);
  }
}

void Blob::Update() {
  caffe_cpu_axpby_fp32(static_cast<size_t>(count()), -1.0f, cpu_diff(), 1.0f, cpu_data());
}

Array<float> Blob::get_data() const {
  Array<float> result;
  result.reserve(count());
  const float* ptr = cpu_data();
  CAFFE_FFI_CONTAINER_LOG << "get_data: copying " << count() << " elements from " << ptr << " to Array<float>";
  for (int64_t i = 0; i < count(); ++i) {
    result.push_back(ptr[i]);
  }
  CAFFE_FFI_CONTAINER_LOG << "get_data: Array<float> size=" << result.size() << " created";
  return result;
}

void Blob::set_data(Array<float> data) {
  TVM_FFI_ICHECK_EQ(static_cast<int64_t>(data.size()), count())
      << "Data size mismatch: expected " << count() << ", got " << data.size();
  float* ptr = cpu_data();
  CAFFE_FFI_CONTAINER_LOG << "set_data: writing " << count() << " elements from Array<float> to " << ptr;
  for (int64_t i = 0; i < count(); ++i) {
    ptr[i] = data[i];
  }
}

Array<float> Blob::get_diff() const {
  Array<float> result;
  result.reserve(count());
  const float* ptr = cpu_diff();
  CAFFE_FFI_CONTAINER_LOG << "get_diff: copying " << count() << " elements from " << ptr << " to Array<float>";
  for (int64_t i = 0; i < count(); ++i) {
    result.push_back(ptr[i]);
  }
  return result;
}

void Blob::set_diff(Array<float> diff) {
  TVM_FFI_ICHECK_EQ(static_cast<int64_t>(diff.size()), count())
      << "Diff size mismatch: expected " << count() << ", got " << diff.size();
  float* ptr = cpu_diff();
  CAFFE_FFI_CONTAINER_LOG << "set_diff: writing " << count() << " elements from Array<float> to " << ptr;
  for (int64_t i = 0; i < count(); ++i) {
    ptr[i] = diff[i];
  }
}

}  // namespace caffe_ffi
