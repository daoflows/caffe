#ifndef CAFFE_COMPAT_FUNCTION_HPP_
#define CAFFE_COMPAT_FUNCTION_HPP_

#include <functional>
#include <utility>

namespace caffe {

using std::function;
using std::bind;
using std::ref;
using std::cref;
using std::forward;
using std::move;

namespace placeholders {
using namespace std::placeholders;
}  // namespace placeholders

}  // namespace caffe

#endif  // CAFFE_COMPAT_FUNCTION_HPP_
