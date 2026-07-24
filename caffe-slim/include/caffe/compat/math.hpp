#ifndef CAFFE_COMPAT_MATH_HPP_
#define CAFFE_COMPAT_MATH_HPP_

#include <cmath>
#include <limits>

namespace caffe {

inline float caffe_nextafter(float x) {
  return std::nextafter(x, std::numeric_limits<float>::infinity());
}

inline double caffe_nextafter(double x) {
  return std::nextafter(x, std::numeric_limits<double>::infinity());
}

}  // namespace caffe

#endif  // CAFFE_COMPAT_MATH_HPP_
