#ifndef CAFFE_COMPAT_RANDOM_HPP_
#define CAFFE_COMPAT_RANDOM_HPP_

#include <random>

namespace caffe {

using rng_t = std::mt19937;

template <typename Dtype>
using uniform_real_distribution = std::uniform_real_distribution<Dtype>;

template <typename Dtype>
using normal_distribution = std::normal_distribution<Dtype>;

using bernoulli_distribution = std::bernoulli_distribution;

}  // namespace caffe

#endif  // CAFFE_COMPAT_RANDOM_HPP_
