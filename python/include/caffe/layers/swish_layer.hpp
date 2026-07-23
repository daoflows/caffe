#ifndef CAFFE_SWISH_LAYER_HPP_
#define CAFFE_SWISH_LAYER_HPP_

#include <memory>
#include <vector>

#include "caffe/blob.hpp"
#include "caffe/layer.hpp"
#include "caffe/proto/caffe.pb.h"

#include "caffe/layers/neuron_layer.hpp"
#include "caffe/layers/sigmoid_layer.hpp"

namespace caffe {

template <typename Dtype>
class SwishLayer : public NeuronLayer<Dtype> {
 public:
  explicit SwishLayer(const LayerParameter& param)
      : NeuronLayer<Dtype>(param),
        sigmoid_layer_(new SigmoidLayer<Dtype>(param)),
        sigmoid_input_(new Blob<Dtype>()),
        sigmoid_output_(new Blob<Dtype>()) {}
  virtual void LayerSetUp(const vector<Blob<Dtype>*>& bottom,
      const vector<Blob<Dtype>*>& top);
  virtual void Reshape(const vector<Blob<Dtype>*>& bottom,
      const vector<Blob<Dtype>*>& top);

  virtual inline const char* type() const { return "Swish"; }

 protected:
  virtual void Forward_cpu(const vector<Blob<Dtype>*>& bottom,
      const vector<Blob<Dtype>*>& top);
  virtual void Backward_cpu(const vector<Blob<Dtype>*>& top,
      const vector<bool>& propagate_down, const vector<Blob<Dtype>*>& bottom);

  std::shared_ptr<SigmoidLayer<Dtype> > sigmoid_layer_;
  std::shared_ptr<Blob<Dtype> > sigmoid_input_;
  std::shared_ptr<Blob<Dtype> > sigmoid_output_;
  vector<Blob<Dtype>*> sigmoid_bottom_vec_;
  vector<Blob<Dtype>*> sigmoid_top_vec_;
};

}  // namespace caffe

#endif  // CAFFE_SWISH_LAYER_HPP_
