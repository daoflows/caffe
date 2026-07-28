#ifndef CAFFE_FFI_LAYER_FACTORY_HPP_
#define CAFFE_FFI_LAYER_FACTORY_HPP_

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include <tvm/ffi/error.h>
#include <tvm/ffi/tvm_ffi.h>
#include <tvm/ffi/memory.h>
#include "caffe/proto/caffe.pb.h"

namespace caffe_ffi {

class Layer;

class LayerRegistry {
 public:
  using Creator = ObjectPtr<Layer> (*)(const caffe::LayerParameter&);
  using CreatorRegistry = std::unordered_map<std::string, Creator>;

  static CreatorRegistry& Registry() {
    static CreatorRegistry* g_registry_ = new CreatorRegistry();
    return *g_registry_;
  }

  static void AddCreator(const std::string& type, Creator creator) {
    CreatorRegistry& registry = Registry();
    TVM_FFI_ICHECK_EQ(registry.count(type), 0)
        << "Layer type " << type << " already registered.";
    registry[type] = creator;
  }

  static ObjectPtr<Layer> CreateLayer(const caffe::LayerParameter& param) {
    const std::string& type = param.type();
    CreatorRegistry& registry = Registry();
    TVM_FFI_ICHECK_EQ(registry.count(type), 1)
        << "Unknown layer type: " << type << " (known types: " << LayerTypeListString() << ")";
    return registry[type](param);
  }

  static std::vector<std::string> LayerTypeList() {
    CreatorRegistry& registry = Registry();
    std::vector<std::string> layer_types;
    for (const auto& kv : registry) {
      layer_types.push_back(kv.first);
    }
    return layer_types;
  }

 private:
  LayerRegistry() = default;

  static std::string LayerTypeListString() {
    std::vector<std::string> layer_types = LayerTypeList();
    std::string result;
    for (size_t i = 0; i < layer_types.size(); ++i) {
      if (i > 0) result += ", ";
      result += layer_types[i];
    }
    return result;
  }
};

#define REGISTER_LAYER_CLASS(type)                                                         \
  namespace {                                                                              \
  ObjectPtr<Layer> Creator_##type##Layer(const caffe::LayerParameter& param) {             \
    return make_object<type##Layer>(param);                                                \
  }                                                                                        \
  TVM_FFI_STATIC_INIT_BLOCK() {                                                            \
    ::caffe_ffi::LayerRegistry::AddCreator(#type, Creator_##type##Layer);                  \
  }                                                                                        \
  }  // namespace

}  // namespace caffe_ffi

#endif  // CAFFE_FFI_LAYER_FACTORY_HPP_
