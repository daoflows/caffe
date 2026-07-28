#ifndef CAFFE_FFI_LAYER_HPP_
#define CAFFE_FFI_LAYER_HPP_

#include <algorithm>
#include <memory>
#include <string>
#include <vector>

#include "caffe_ffi/blob.hpp"
#include "caffe/proto/caffe.pb.h"

namespace caffe_ffi {

class Layer : public Object {
 public:
  static constexpr bool _type_mutable = true;
  static constexpr int _type_child_slots = 32;
  static constexpr bool _type_child_slots_can_overflow = true;

  explicit Layer(const caffe::LayerParameter& param);
  virtual ~Layer() = default;

  void SetUp(const std::vector<Blob*>& bottom, const std::vector<Blob*>& top);

  float Forward(const std::vector<Blob*>& bottom, const std::vector<Blob*>& top);

  virtual void LayerSetUp(const std::vector<Blob*>& bottom,
                          const std::vector<Blob*>& top) {}

  virtual void Reshape(const std::vector<Blob*>& bottom,
                       const std::vector<Blob*>& top) = 0;

  std::vector<ObjectPtr<Blob>>& blobs() { return blobs_; }
  const std::vector<ObjectPtr<Blob>>& blobs() const { return blobs_; }

  Array<ObjectPtr<Blob>> blobs_array() const;

  const caffe::LayerParameter& layer_param() const { return layer_param_; }

  void ToProto(caffe::LayerParameter* param, bool write_diff = false);

  float loss(int top_index) const {
    return (loss_.size() > static_cast<size_t>(top_index)) ? loss_[top_index] : 0.0f;
  }

  void set_loss(int top_index, float value) {
    if (loss_.size() <= static_cast<size_t>(top_index)) {
      loss_.resize(top_index + 1, 0.0f);
    }
    loss_[top_index] = value;
  }

  virtual const char* type() const { return ""; }

  virtual int ExactNumBottomBlobs() const { return -1; }
  virtual int MinBottomBlobs() const { return -1; }
  virtual int MaxBottomBlobs() const { return -1; }
  virtual int ExactNumTopBlobs() const { return -1; }
  virtual int MinTopBlobs() const { return -1; }
  virtual int MaxTopBlobs() const { return -1; }
  virtual bool EqualNumBottomTopBlobs() const { return false; }
  virtual bool AutoTopBlobs() const { return false; }

  bool param_propagate_down(int param_id) const {
    return (param_propagate_down_.size() > static_cast<size_t>(param_id))
               ? param_propagate_down_[param_id]
               : false;
  }
  void set_param_propagate_down(int param_id, bool value) {
    if (param_propagate_down_.size() <= static_cast<size_t>(param_id)) {
      param_propagate_down_.resize(param_id + 1, true);
    }
    param_propagate_down_[param_id] = value;
  }

  TVM_FFI_DECLARE_OBJECT_INFO("caffe_ffi.Layer", Layer, Object);

 protected:
  caffe::LayerParameter layer_param_;
  std::vector<ObjectPtr<Blob>> blobs_;
  std::vector<bool> param_propagate_down_;
  std::vector<float> loss_;

  virtual void Forward_cpu(const std::vector<Blob*>& bottom,
                           const std::vector<Blob*>& top) = 0;

  void CheckBlobCounts(const std::vector<Blob*>& bottom,
                       const std::vector<Blob*>& top);

  void SetLossWeights(const std::vector<Blob*>& top);

 private:
  Layer(const Layer&) = delete;
  Layer& operator=(const Layer&) = delete;
};

}  // namespace caffe_ffi

#endif  // CAFFE_FFI_LAYER_HPP_
