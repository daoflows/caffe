#ifndef CAFFE_BLOB_HPP_
#define CAFFE_BLOB_HPP_

#include <algorithm>
#include <climits>
#include <cstdint>
#include <sstream>
#include <string>
#include <vector>

#include <tvm/ffi/container/shape.h>

#include "caffe/common.hpp"
#include "caffe/proto/caffe.pb.h"
#include "caffe/syncedmem.hpp"

const int kMaxBlobAxes = 32;

namespace caffe {

template <typename Dtype>
class Blob {
 public:
  Blob()
       : data_(), diff_(), count_(0), capacity_(0) {}

  explicit Blob(const int num, const int channels, const int height,
      const int width);
  explicit Blob(const vector<int>& shape);

  void Reshape(const int num, const int channels, const int height,
      const int width);
  void Reshape(const vector<int>& shape);
  void Reshape(const BlobShape& shape);
  void ReshapeLike(const Blob& other);
  inline string shape_string() const {
    ostringstream stream;
    for (int i = 0; i < static_cast<int>(shape_.size()); ++i) {
      stream << shape_[i] << " ";
    }
    stream << "(" << count_ << ")";
    return stream.str();
  }
  inline const vector<int>& shape() const { return shape_vec_; }
  inline const int* shape_data() const { return shape_vec_.data(); }
  inline tvm::ffi::ShapeView shape_view() const {
    return tvm::ffi::ShapeView(shape_.data(), shape_.size());
  }
  inline int shape(int index) const {
    return static_cast<int>(shape_[CanonicalAxisIndex(index)]);
  }
  inline int num_axes() const { return static_cast<int>(shape_.size()); }
  inline int count() const { return static_cast<int>(count_); }

  inline int count(int start_axis, int end_axis) const {
    CHECK_LE(start_axis, end_axis);
    CHECK_GE(start_axis, 0);
    CHECK_GE(end_axis, 0);
    CHECK_LE(start_axis, num_axes());
    CHECK_LE(end_axis, num_axes());
    int64_t count = 1;
    for (int i = start_axis; i < end_axis; ++i) {
      count *= shape(i);
    }
    CHECK_LE(count, INT_MAX);
    return static_cast<int>(count);
  }
  inline int count(int start_axis) const {
    return count(start_axis, num_axes());
  }

  inline int CanonicalAxisIndex(int axis_index) const {
    CHECK_GE(axis_index, -num_axes())
        << "axis " << axis_index << " out of range for " << num_axes()
        << "-D Blob with shape " << shape_string();
    CHECK_LT(axis_index, num_axes())
        << "axis " << axis_index << " out of range for " << num_axes()
        << "-D Blob with shape " << shape_string();
    if (axis_index < 0) {
      return axis_index + num_axes();
    }
    return axis_index;
  }

  inline int num() const { return LegacyShape(0); }
  inline int channels() const { return LegacyShape(1); }
  inline int height() const { return LegacyShape(2); }
  inline int width() const { return LegacyShape(3); }
  inline int LegacyShape(int index) const {
    CHECK_LE(num_axes(), 4)
        << "Cannot use legacy accessors on Blobs with > 4 axes.";
    CHECK_LT(index, 4);
    CHECK_GE(index, -4);
    if (index >= num_axes() || index < -num_axes()) {
      return 1;
    }
    return shape(index);
  }

  inline int offset(const int n, const int c = 0, const int h = 0,
      const int w = 0) const {
    CHECK_GE(n, 0);
    CHECK_LE(n, num());
    CHECK_GE(channels(), 0);
    CHECK_LE(c, channels());
    CHECK_GE(height(), 0);
    CHECK_LE(h, height());
    CHECK_GE(width(), 0);
    CHECK_LE(w, width());
    int64_t off = ((static_cast<int64_t>(n) * channels() + c) * height() + h) * width() + w;
    CHECK_LE(off, INT_MAX);
    return static_cast<int>(off);
  }

  inline int offset(const vector<int>& indices) const {
    CHECK_LE(static_cast<int>(indices.size()), num_axes());
    int64_t offset = 0;
    for (int i = 0; i < num_axes(); ++i) {
      offset *= shape(i);
      if (static_cast<int>(indices.size()) > i) {
        CHECK_GE(indices[i], 0);
        CHECK_LT(indices[i], shape(i));
        offset += indices[i];
      }
    }
    CHECK_LE(offset, INT_MAX);
    return static_cast<int>(offset);
  }

  void CopyFrom(const Blob<Dtype>& source, bool copy_diff = false,
      bool reshape = false);

  inline Dtype data_at(const int n, const int c, const int h,
      const int w) const {
    return cpu_data()[offset(n, c, h, w)];
  }

  inline Dtype diff_at(const int n, const int c, const int h,
      const int w) const {
    return cpu_diff()[offset(n, c, h, w)];
  }

  inline Dtype data_at(const vector<int>& index) const {
    return cpu_data()[offset(index)];
  }

  inline Dtype diff_at(const vector<int>& index) const {
    return cpu_diff()[offset(index)];
  }

  inline const shared_ptr<SyncedMemory>& data() const {
    CHECK(data_);
    return data_;
  }

  inline const shared_ptr<SyncedMemory>& diff() const {
    CHECK(diff_);
    return diff_;
  }

  const Dtype* cpu_data() const;
  void set_cpu_data(Dtype* data);
  const Dtype* cpu_diff() const;
  Dtype* mutable_cpu_data();
  Dtype* mutable_cpu_diff();
  void Update();
  void FromProto(const BlobProto& proto, bool reshape = true);
  void ToProto(BlobProto* proto, bool write_diff = false) const;

  Dtype asum_data() const;
  Dtype asum_diff() const;
  Dtype sumsq_data() const;
  Dtype sumsq_diff() const;

  void scale_data(Dtype scale_factor);
  void scale_diff(Dtype scale_factor);

  void ShareData(const Blob& other);
  void ShareDiff(const Blob& other);

  bool ShapeEquals(const BlobProto& other);

  Dtype* mutable_cpu_data_direct() {
    return static_cast<Dtype*>(const_cast<Blob<Dtype>*>(this)->data_->mutable_cpu_data());
  }

 protected:
  shared_ptr<SyncedMemory> data_;
  shared_ptr<SyncedMemory> diff_;
  tvm::ffi::Shape shape_;
  vector<int> shape_vec_;
  int64_t count_;
  int64_t capacity_;

  DISABLE_COPY_AND_ASSIGN(Blob);
};

}  // namespace caffe

#endif  // CAFFE_BLOB_HPP_
