#include <caffe/caffe.hpp>
#include <tvm/ffi/error.h>

#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

using namespace caffe;

typedef float Dtype;

static int g_tests_passed = 0;
static int g_tests_failed = 0;

#define TEST_CHECK(cond, msg)                                                  \
  do {                                                                         \
    if (!(cond)) {                                                             \
      std::cerr << "FAIL: " << msg << " (at " << __FILE__ << ":" << __LINE__   \
                << ")" << std::endl;                                           \
      g_tests_failed++;                                                        \
    } else {                                                                   \
      std::cout << "PASS: " << msg << std::endl;                               \
      g_tests_passed++;                                                        \
    }                                                                          \
  } while (0)

#define TEST_SECTION(name) std::cout << "\n=== " << name << " ===" << std::endl;

static bool FileExists(const std::string& path) {
  std::ifstream f(path);
  return f.good();
}

static bool RunLeNetForward(const std::string& proto_path,
                             std::vector<Dtype>& out_probs,
                             std::vector<int>& out_shape) {
  Caffe::set_random_seed(42);
  Net<Dtype>* net = nullptr;
  try {
    net = new Net<Dtype>(proto_path, caffe::TEST);
  } catch (const std::exception& e) {
    std::cerr << "  Net constructor exception: " << e.what() << std::endl;
    return false;
  }
  if (!net) return false;

  Blob<Dtype>* data_blob = net->blob_by_name("data").get();
  Blob<Dtype>* prob_blob = net->blob_by_name("prob").get();
  if (!data_blob || !prob_blob) {
    delete net;
    return false;
  }

  Dtype* data_ptr = data_blob->mutable_cpu_data();
  int data_count = data_blob->count();
  for (int i = 0; i < data_count; ++i) {
    data_ptr[i] = static_cast<Dtype>(i % 100) / Dtype(100.0) - Dtype(0.5);
  }

  net->ForwardPrefilled();

  const Dtype* prob_ptr = prob_blob->cpu_data();
  int prob_count = prob_blob->count();
  out_probs.assign(prob_ptr, prob_ptr + prob_count);
  out_shape.clear();
  for (int i = 0; i < prob_blob->num_axes(); ++i) {
    out_shape.push_back(prob_blob->shape(i));
  }

  delete net;
  return true;
}

int main(int argc, char** argv) {
  std::string proto_dir = ".";
  if (argc > 1) {
    proto_dir = argv[1];
  }
  std::string proto_path = proto_dir + "/lenet_deploy.prototxt";

  std::cout << "Caffe Slim C++ Unit Tests" << std::endl;
  std::cout << "Caffe version: " << CAFFE_VERSION << std::endl;
  std::cout << "Proto path: " << proto_path << std::endl;

  TEST_SECTION("1. Environment Setup");
  TEST_CHECK(FileExists(proto_path), "lenet_deploy.prototxt exists");
  Caffe::set_mode(Caffe::CPU);
  TEST_CHECK(Caffe::mode() == Caffe::CPU, "Set mode to CPU");
  Caffe::set_random_seed(42);
  TEST_CHECK(true, "Set random seed to 42");

  TEST_SECTION("2. Layer Registry");
  std::vector<std::string> layer_types = LayerRegistry<Dtype>::LayerTypeList();
  std::cout << "  Registered layers (" << layer_types.size() << "):";
  for (const auto& t : layer_types) std::cout << " " << t;
  std::cout << std::endl;

  TEST_CHECK(layer_types.size() >= 35, "At least 35 layers registered");
  auto has_layer = [&](const std::string& name) {
    return std::find(layer_types.begin(), layer_types.end(), name) !=
           layer_types.end();
  };
  const std::vector<std::string> expected_layers = {
    "Input", "Convolution", "Pooling", "InnerProduct", "ReLU", "Softmax",
    "SoftmaxWithLoss", "Dropout", "BatchNorm", "Scale", "Bias", "Concat",
    "Split", "Reshape", "Flatten", "Sigmoid", "TanH", "AbsVal", "Power",
    "PReLU", "ELU", "Exp", "Log", "Threshold", "Bias", "LRN", "Eltwise",
    "Deconvolution", "Slice", "ArgMax", "Accuracy", "MVN", "Reduction",
    "Tile", "Clip", "BNLL", "Swish"
  };
  int found_count = 0;
  for (const auto& name : expected_layers) {
    if (has_layer(name)) found_count++;
  }
  std::cout << "  Expected layers found: " << found_count << "/"
            << expected_layers.size() << std::endl;
  TEST_CHECK(found_count >= 30, "At least 30 expected inference layers registered");

  TEST_SECTION("3. Net Construction from prototxt");
  Net<Dtype>* net = nullptr;
  try {
    net = new Net<Dtype>(proto_path, caffe::TEST);
    TEST_CHECK(net != nullptr, "Net created successfully");
  } catch (const std::exception& e) {
    std::cerr << "  Exception: " << e.what() << std::endl;
    TEST_CHECK(false, "Net constructor did not throw");
    return 1;
  }

  TEST_SECTION("4. Blob Names and Shapes");
  const std::vector<std::string>& blob_names = net->blob_names();
  std::cout << "  Blobs (" << blob_names.size() << "):";
  for (const auto& n : blob_names) std::cout << " " << n;
  std::cout << std::endl;

  TEST_CHECK(blob_names.size() >= 8, "Expected >=8 blobs");

  auto blob_by_name = [&](const std::string& name) -> Blob<Dtype>* {
    return net->blob_by_name(name).get();
  };

  Blob<Dtype>* data_blob = blob_by_name("data");
  TEST_CHECK(data_blob != nullptr, "data blob exists");
  if (data_blob) {
    std::cout << "  data shape:";
    for (int i = 0; i < data_blob->num_axes(); ++i) std::cout << " " << data_blob->shape(i);
    std::cout << " count=" << data_blob->count() << std::endl;
    TEST_CHECK(data_blob->num_axes() == 4, "data blob is 4D (NCHW)");
    TEST_CHECK(data_blob->shape(0) == 64, "data batch size = 64");
    TEST_CHECK(data_blob->shape(1) == 1, "data channels = 1");
    TEST_CHECK(data_blob->shape(2) == 28, "data height = 28");
    TEST_CHECK(data_blob->shape(3) == 28, "data width = 28");
  }

  Blob<Dtype>* prob_blob = blob_by_name("prob");
  TEST_CHECK(prob_blob != nullptr, "prob blob exists");
  if (prob_blob) {
    std::cout << "  prob shape:";
    for (int i = 0; i < prob_blob->num_axes(); ++i) std::cout << " " << prob_blob->shape(i);
    std::cout << " count=" << prob_blob->count() << std::endl;
    TEST_CHECK(prob_blob->num_axes() == 2, "prob blob is 2D");
    TEST_CHECK(prob_blob->shape(0) == 64, "prob batch size = 64");
    TEST_CHECK(prob_blob->shape(1) == 10, "prob num_classes = 10");
  }

  Blob<Dtype>* conv1_blob = blob_by_name("conv1");
  TEST_CHECK(conv1_blob != nullptr, "conv1 blob exists");
  if (conv1_blob) {
    std::cout << "  conv1 shape:";
    for (int i = 0; i < conv1_blob->num_axes(); ++i) std::cout << " " << conv1_blob->shape(i);
    std::cout << std::endl;
    TEST_CHECK(conv1_blob->shape(0) == 64, "conv1 batch = 64");
    TEST_CHECK(conv1_blob->shape(1) == 20, "conv1 output channels = 20");
    TEST_CHECK(conv1_blob->shape(2) == 24, "conv1 height = 24");
    TEST_CHECK(conv1_blob->shape(3) == 24, "conv1 width = 24");
  }

  Blob<Dtype>* ip1_blob = blob_by_name("ip1");
  TEST_CHECK(ip1_blob != nullptr, "ip1 blob exists");
  if (ip1_blob) {
    std::cout << "  ip1 shape:";
    for (int i = 0; i < ip1_blob->num_axes(); ++i) std::cout << " " << ip1_blob->shape(i);
    std::cout << std::endl;
    TEST_CHECK(ip1_blob->shape(1) == 500, "ip1 output dim = 500");
  }

  Blob<Dtype>* ip2_blob = blob_by_name("ip2");
  TEST_CHECK(ip2_blob != nullptr, "ip2 blob exists");
  if (ip2_blob) {
    std::cout << "  ip2 shape:";
    for (int i = 0; i < ip2_blob->num_axes(); ++i) std::cout << " " << ip2_blob->shape(i);
    std::cout << std::endl;
    TEST_CHECK(ip2_blob->shape(1) == 10, "ip2 output dim = 10");
  }

  TEST_SECTION("5. Input/Output Blob Indices");
  const std::vector<int>& input_indices = net->input_blob_indices();
  const std::vector<int>& output_indices = net->output_blob_indices();
  std::cout << "  Input blobs:";
  for (int i : input_indices) std::cout << " " << blob_names[i];
  std::cout << std::endl;
  std::cout << "  Output blobs:";
  for (int i : output_indices) std::cout << " " << blob_names[i];
  std::cout << std::endl;
  TEST_CHECK(input_indices.size() == 1, "Number of input blobs = 1");
  TEST_CHECK(output_indices.size() == 1, "Number of output blobs = 1");

  const std::vector<std::string>& input_names = net->input_blob_names();
  const std::vector<std::string>& output_names = net->output_blob_names();
  TEST_CHECK(input_names.size() == 1 && input_names[0] == "data",
             "Input blob names API works");
  TEST_CHECK(output_names.size() == 1 && output_names[0] == "prob",
             "Output blob names API works");

  TEST_SECTION("6. Forward Pass");
  Dtype* data_ptr = data_blob->mutable_cpu_data();
  int data_count = data_blob->count();
  std::srand(12345);
  for (int i = 0; i < data_count; ++i) {
    data_ptr[i] = static_cast<Dtype>(std::rand()) / RAND_MAX - Dtype(0.5);
  }
  std::cout << "  Filling input with random values in [-0.5, 0.5)..." << std::endl;

  const vector<Blob<Dtype>*>& output_blobs = net->ForwardPrefilled();
  TEST_CHECK(!output_blobs.empty(), "ForwardPrefilled returned output blobs");
  TEST_CHECK(output_blobs[0] == prob_blob, "Output blob[0] is prob");

  TEST_SECTION("7. Softmax Output Validation");
  const Dtype* prob_ptr = prob_blob->cpu_data();
  int num_samples = prob_blob->shape(0);
  int num_classes = prob_blob->shape(1);
  int prob_count = prob_blob->count();
  bool all_valid = true;
  bool sums_to_one = true;
  int argmax_consistent = 0;
  for (int n = 0; n < num_samples; ++n) {
    Dtype sum = 0;
    Dtype max_p = -1;
    int max_c = -1;
    for (int c = 0; c < num_classes; ++c) {
      Dtype v = prob_ptr[n * num_classes + c];
      if (v < -1e-6f || v > 1.0f + 1e-6f) all_valid = false;
      if (v > max_p) { max_p = v; max_c = c; }
      sum += v;
    }
    if (std::fabs(sum - Dtype(1.0)) > 1e-4f) {
      sums_to_one = false;
    }
    if (max_c >= 0 && max_c < num_classes) argmax_consistent++;
  }
  TEST_CHECK(all_valid, "All probabilities in [0, 1] range");
  TEST_CHECK(sums_to_one, "Per-sample probabilities sum to 1");
  TEST_CHECK(argmax_consistent == num_samples, "All samples have valid argmax");

  Dtype min_val = prob_ptr[0], max_val = prob_ptr[0];
  Dtype total_sum = 0;
  for (int i = 0; i < prob_count; ++i) {
    min_val = std::min(min_val, prob_ptr[i]);
    max_val = std::max(max_val, prob_ptr[i]);
    total_sum += prob_ptr[i];
  }
  std::cout << "  prob min=" << min_val << " max=" << max_val
            << " avg=" << (total_sum / prob_count) << std::endl;
  TEST_CHECK(min_val >= Dtype(-1e-6), "min prob >= 0");
  TEST_CHECK(max_val <= Dtype(1.0) + Dtype(1e-6), "max prob <= 1");
  TEST_CHECK(std::fabs(total_sum / num_samples - Dtype(1.0)) < Dtype(1e-4),
             "Average per-sample sum = 1.0");

  TEST_SECTION("8. Reshape and Re-Forward");
  net->Reshape();
  TEST_CHECK(prob_blob->shape(0) == 64, "Reshape preserves batch size");
  TEST_CHECK(prob_blob->shape(1) == 10, "Reshape preserves num classes");

  for (int i = 0; i < data_count; ++i) {
    data_ptr[i] = static_cast<Dtype>(std::rand()) / RAND_MAX - Dtype(0.5);
  }
  net->ForwardPrefilled();
  TEST_CHECK(true, "Re-forward after Reshape succeeds");

  TEST_SECTION("9. Determinism Check");
  std::vector<Dtype> probs1;
  std::vector<int> shape1;
  bool ok1 = RunLeNetForward(proto_path, probs1, shape1);
  TEST_CHECK(ok1, "First independent Net creation/forward succeeds");
  std::vector<Dtype> probs2;
  std::vector<int> shape2;
  bool ok2 = RunLeNetForward(proto_path, probs2, shape2);
  TEST_CHECK(ok2, "Second independent Net creation/forward succeeds");

  bool same_result = true;
  if (ok1 && ok2 && probs1.size() == probs2.size()) {
    for (size_t i = 0; i < probs1.size(); ++i) {
      if (std::fabs(probs1[i] - probs2[i]) > 1e-5f) {
        same_result = false;
        break;
      }
    }
  } else {
    same_result = false;
  }
  TEST_CHECK(same_result, "Same input produces same output across Net instances (deterministic)");

  TEST_SECTION("10. Multiple Net Create/Destroy (memory safety)");
  bool all_created = true;
  for (int iter = 0; iter < 5; ++iter) {
    Net<Dtype>* temp_net = nullptr;
    try {
      temp_net = new Net<Dtype>(proto_path, caffe::TEST);
    } catch (...) {
      all_created = false;
      break;
    }
    if (!temp_net) { all_created = false; break; }
    Blob<Dtype>* td = temp_net->blob_by_name("data").get();
    if (td) {
      Dtype* tdp = td->mutable_cpu_data();
      int tc = td->count();
      for (int i = 0; i < tc; ++i) tdp[i] = Dtype(0.1) * (i % 10);
      temp_net->ForwardPrefilled();
    }
    delete temp_net;
  }
  TEST_CHECK(all_created, "Create/destroy 5 nets without crash");

  delete net;

  TEST_SECTION("Summary");
  std::cout << "  Passed: " << g_tests_passed << std::endl;
  std::cout << "  Failed: " << g_tests_failed << std::endl;

  if (g_tests_failed > 0) {
    std::cerr << "\n*** SOME TESTS FAILED ***" << std::endl;
    return 1;
  }
  std::cout << "\n*** ALL TESTS PASSED ***" << std::endl;
  return 0;
}
