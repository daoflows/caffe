#ifndef CAFFE_COMPAT_SMART_PTR_HPP_
#define CAFFE_COMPAT_SMART_PTR_HPP_

#include <memory>

namespace caffe {

using std::shared_ptr;
using std::weak_ptr;
using std::unique_ptr;
using std::make_shared;
using std::make_unique;
using std::dynamic_pointer_cast;
using std::static_pointer_cast;
using std::const_pointer_cast;
using std::enable_shared_from_this;

}  // namespace caffe

#endif  // CAFFE_COMPAT_SMART_PTR_HPP_
