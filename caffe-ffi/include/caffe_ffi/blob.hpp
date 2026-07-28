#ifndef CAFFE_FFI_BLOB_HPP_
#define CAFFE_FFI_BLOB_HPP_

#include <memory>
#include <string>
#include <vector>

#include "caffe_ffi/common.hpp"
#include "caffe_ffi/math_utils.hpp"

namespace caffe {
class BlobProto;
class BlobShape;
}

namespace caffe_ffi {

class Blob : public Object {
 public:
  static constexpr bool _type_mutable = true;

  Blob();
  explicit Blob(ShapeView shape);
  explicit Blob(const std::vector<int64_t>& shape);
  ~Blob();

  void Reshape(ShapeView shape);
  void Reshape(const std::vector<int64_t>& shape);
  void Reshape(const Array<int64_t>& shape);
  void Reshape(const caffe::BlobShape& shape);
  void ReshapeLike(const Blob& other);

  Shape shape() const { return Shape(data_tensor_.shape()); }
  int num_axes() const { return data_tensor_.ndim(); }
  int64_t count() const { return data_tensor_.numel(); }
  int64_t count(int start_axis) const { return Count(data_tensor_.shape(), start_axis); }
  int64_t count(int start_axis, int end_axis) const {
    return Count(data_tensor_.shape(), start_axis, end_axis);
  }

  int CanonicalAxisIndex(int axis_index) const {
    return caffe_ffi::CanonicalAxisIndex(axis_index, num_axes());
  }

  int64_t shape(int index) const {
    return data_tensor_.size(this->CanonicalAxisIndex(index));
  }

  int64_t LegacyShape(int index) const;
  int num() const { return LegacyShape(0); }
  int channels() const { return LegacyShape(1); }
  int height() const { return LegacyShape(2); }
  int width() const { return LegacyShape(3); }

  float* cpu_data() { return static_cast<float*>(data_tensor_.data_ptr()); }
  const float* cpu_data() const { return static_cast<const float*>(data_tensor_.data_ptr()); }
  float* cpu_diff() { return static_cast<float*>(diff_tensor_.data_ptr()); }
  const float* cpu_diff() const { return static_cast<const float*>(diff_tensor_.data_ptr()); }

  Tensor data_tensor() const;
  Tensor diff_tensor() const;

  void FromProto(const caffe::BlobProto& proto, bool reshape = true);
  void ToProto(caffe::BlobProto* proto) const;
  void Update();

  Array<float> get_data() const;
  void set_data(Array<float> data);
  Array<float> get_diff() const;
  void set_diff(Array<float> diff);

  void set_name(const std::string& name) { name_ = name; }
  std::string name() const { return name_; }

  TVM_FFI_DECLARE_OBJECT_INFO_FINAL(
      "caffe_ffi.Blob", Blob, Object);

 private:
  std::string name_;
  Tensor data_tensor_;
  Tensor diff_tensor_;
};

}  // namespace caffe_ffi

#endif  // CAFFE_FFI_BLOB_HPP_
