#include <string>

#include "caffe/layer.hpp"
#include "caffe/layer_factory.hpp"
#include "caffe/layers/conv_layer.hpp"
#include "caffe/layers/deconv_layer.hpp"
#include "caffe/layers/lrn_layer.hpp"
#include "caffe/layers/pooling_layer.hpp"
#include "caffe/layers/relu_layer.hpp"
#include "caffe/layers/sigmoid_layer.hpp"
#include "caffe/layers/softmax_layer.hpp"
#include "caffe/layers/tanh_layer.hpp"
#include "caffe/proto/caffe.pb.h"

namespace caffe {

template <typename Dtype>
shared_ptr<Layer<Dtype> > GetConvolutionLayer(
    const LayerParameter& param) {
  return shared_ptr<Layer<Dtype> >(new ConvolutionLayer<Dtype>(param));
}

REGISTER_LAYER_CREATOR(Convolution, GetConvolutionLayer);

template <typename Dtype>
shared_ptr<Layer<Dtype> > GetDeconvolutionLayer(const LayerParameter& param) {
  return shared_ptr<Layer<Dtype> >(new DeconvolutionLayer<Dtype>(param));
}

REGISTER_LAYER_CREATOR(Deconvolution, GetDeconvolutionLayer);

template <typename Dtype>
shared_ptr<Layer<Dtype> > GetPoolingLayer(const LayerParameter& param) {
  return shared_ptr<Layer<Dtype> >(new PoolingLayer<Dtype>(param));
}

REGISTER_LAYER_CREATOR(Pooling, GetPoolingLayer);

template <typename Dtype>
shared_ptr<Layer<Dtype> > GetLRNLayer(const LayerParameter& param) {
  return shared_ptr<Layer<Dtype> >(new LRNLayer<Dtype>(param));
}

REGISTER_LAYER_CREATOR(LRN, GetLRNLayer);

template <typename Dtype>
shared_ptr<Layer<Dtype> > GetReLULayer(const LayerParameter& param) {
  return shared_ptr<Layer<Dtype> >(new ReLULayer<Dtype>(param));
}

REGISTER_LAYER_CREATOR(ReLU, GetReLULayer);

template <typename Dtype>
shared_ptr<Layer<Dtype> > GetSigmoidLayer(const LayerParameter& param) {
  return shared_ptr<Layer<Dtype> >(new SigmoidLayer<Dtype>(param));
}

REGISTER_LAYER_CREATOR(Sigmoid, GetSigmoidLayer);

template <typename Dtype>
shared_ptr<Layer<Dtype> > GetSoftmaxLayer(const LayerParameter& param) {
  return shared_ptr<Layer<Dtype> >(new SoftmaxLayer<Dtype>(param));
}

REGISTER_LAYER_CREATOR(Softmax, GetSoftmaxLayer);

template <typename Dtype>
shared_ptr<Layer<Dtype> > GetTanHLayer(const LayerParameter& param) {
  return shared_ptr<Layer<Dtype> >(new TanHLayer<Dtype>(param));
}

REGISTER_LAYER_CREATOR(TanH, GetTanHLayer);

}  // namespace caffe
