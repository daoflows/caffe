#ifndef CAFFE_FFI_NET_HPP_
#define CAFFE_FFI_NET_HPP_

#include <map>
#include <memory>
#include <set>
#include <string>
#include <utility>
#include <vector>

#include "caffe_ffi/blob.hpp"
#include "caffe_ffi/layer.hpp"
#include "caffe_ffi/layer_factory.hpp"
#include "caffe/proto/caffe.pb.h"

namespace caffe_ffi {

class Net : public Object {
 public:
  static constexpr bool _type_mutable = true;

  explicit Net(const caffe::NetParameter& param);
  explicit Net(const std::string& param_file);
  virtual ~Net() = default;

  void Init(const caffe::NetParameter& param);

  void CopyTrainedLayersFrom(const std::string& trained_filename);
  void CopyTrainedLayersFrom(const caffe::NetParameter& trained_net_param);

  Map<String, ObjectPtr<Blob>> Forward(
      const Map<String, Array<float>>& inputs = {});

  float ForwardFromTo(int start, int end);

  const std::string& name() const { return name_; }
  const std::vector<std::string>& layer_names() const { return layer_names_; }
  const std::vector<std::string>& blob_names() const { return blob_names_; }

  Array<String> layer_names_array() const;
  Array<String> blob_names_array() const;
  Array<String> input_blob_names_array() const;
  Array<String> output_blob_names_array() const;

  Array<ObjectPtr<Blob>> blobs_array() const;
  Array<ObjectPtr<Layer>> layers_array() const;
  Array<ObjectPtr<Blob>> input_blobs_array() const;
  Array<ObjectPtr<Blob>> output_blobs_array() const;

  ObjectPtr<Blob> blob_by_name(const std::string& blob_name) const;
  ObjectPtr<Layer> layer_by_name(const std::string& layer_name) const;

  bool has_blob(const std::string& blob_name) const;
  bool has_layer(const std::string& layer_name) const;

  int num_inputs() const { return static_cast<int>(net_input_blobs_.size()); }
  int num_outputs() const { return static_cast<int>(net_output_blobs_.size()); }
  const std::vector<Blob*>& input_blobs() const { return net_input_blobs_; }
  const std::vector<Blob*>& output_blobs() const { return net_output_blobs_; }
  const std::vector<std::string>& input_blob_names() const { return net_input_blob_names_; }
  const std::vector<std::string>& output_blob_names() const { return net_output_blob_names_; }

  TVM_FFI_DECLARE_OBJECT_INFO_FINAL(
      "caffe_ffi.Net", Net, Object);

 protected:
  void AppendTop(const caffe::NetParameter& param, int layer_id,
                 int top_id, std::set<std::string>* available_blobs,
                 std::map<std::string, int>* blob_name_to_idx);
  int AppendBottom(const caffe::NetParameter& param, int layer_id,
                   int bottom_id, std::set<std::string>* available_blobs,
                   std::map<std::string, int>* blob_name_to_idx);

  std::string name_;
  std::vector<ObjectPtr<Layer>> layers_;
  std::vector<std::string> layer_names_;
  std::map<std::string, int> layer_names_index_;
  std::vector<ObjectPtr<Blob>> blobs_;
  std::vector<std::string> blob_names_;
  std::map<std::string, int> blob_names_index_;
  std::vector<std::vector<Blob*>> bottom_vecs_;
  std::vector<std::vector<Blob*>> top_vecs_;
  std::vector<int> net_input_blob_indices_;
  std::vector<int> net_output_blob_indices_;
  std::vector<Blob*> net_input_blobs_;
  std::vector<Blob*> net_output_blobs_;
  std::vector<std::string> net_input_blob_names_;
  std::vector<std::string> net_output_blob_names_;

 private:
  Net(const Net&) = delete;
  Net& operator=(const Net&) = delete;
};

caffe::NetParameter ReadNetParamsFromTextFile(const std::string& filename);
caffe::NetParameter ReadNetParamsFromBinaryFile(const std::string& filename);

}  // namespace caffe_ffi

#endif  // CAFFE_FFI_NET_HPP_
