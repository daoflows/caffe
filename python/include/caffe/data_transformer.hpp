#ifndef CAFFE_DATA_TRANSFORMER_HPP
#define CAFFE_DATA_TRANSFORMER_HPP

#include <vector>

#include "caffe/blob.hpp"
#include "caffe/common.hpp"
#include "caffe/proto/caffe.pb.h"

namespace caffe {

template <typename Dtype>
class DataTransformer {
 public:
  explicit DataTransformer(const TransformationParameter& param, Phase phase);
  virtual ~DataTransformer() {}

  void InitRand();

  void Transform(const Datum& datum, Blob<Dtype>* transformed_blob);

  void Transform(const vector<Datum> & datum_vector,
                Blob<Dtype>* transformed_blob);

#ifdef USE_OPENCV
  void Transform(const vector<cv::Mat> & mat_vector,
                Blob<Dtype>* transformed_blob);

  void Transform(const cv::Mat& cv_img, Blob<Dtype>* transformed_blob);
#endif

  void Transform(Blob<Dtype>* input_blob, Blob<Dtype>* transformed_blob);

  vector<int> InferBlobShape(const Datum& datum);
  vector<int> InferBlobShape(const vector<Datum> & datum_vector);
#ifdef USE_OPENCV
  vector<int> InferBlobShape(const vector<cv::Mat> & mat_vector);
  vector<int> InferBlobShape(const cv::Mat& cv_img);
#endif

 protected:
  virtual int Rand(int n);

  void Transform(const Datum& datum, Dtype* transformed_data);
  TransformationParameter param_;


  shared_ptr<Caffe::RNG> rng_;
  Phase phase_;
  Blob<Dtype> data_mean_;
  vector<Dtype> mean_values_;
};

}  // namespace caffe

#endif  // CAFFE_DATA_TRANSFORMER_HPP_
