#ifndef CAFFE_SOLVER_HPP_
#define CAFFE_SOLVER_HPP_
#include <string>
#include <vector>

#include "caffe/compat/function.hpp"
#include "caffe/net.hpp"
#include "caffe/solver_factory.hpp"
#include "caffe/util/benchmark.hpp"

namespace caffe {

namespace SolverAction {
  enum Enum {
    NONE = 0,
    STOP = 1,
    SNAPSHOT = 2
  };
}

typedef caffe::function<SolverAction::Enum()> ActionCallback;

template <typename Dtype>
class Solver {
 public:
  explicit Solver(const SolverParameter& param);
  explicit Solver(const string& param_file);
  void Init(const SolverParameter& param);
  void InitTrainNet();
  void InitTestNets();

  void SetActionFunction(ActionCallback func);
  SolverAction::Enum GetRequestedAction();
  virtual void Solve(const char* resume_file = NULL);
  inline void Solve(const string& resume_file) { Solve(resume_file.c_str()); }
  void Step(int iters);
  void Restore(const char* resume_file);
  void Snapshot();
  virtual ~Solver() {}
  inline const SolverParameter& param() const { return param_; }
  inline shared_ptr<Net<Dtype> > net() { return net_; }
  inline const vector<shared_ptr<Net<Dtype> > >& test_nets() {
    return test_nets_;
  }
  int iter() const { return iter_; }

  class Callback {
   protected:
    virtual void on_start() = 0;
    virtual void on_gradients_ready() = 0;

    template <typename T>
    friend class Solver;
  };
  const vector<Callback*>& callbacks() const { return callbacks_; }
  void add_callback(Callback* value) {
    callbacks_.push_back(value);
  }

  void CheckSnapshotWritePermissions();
  virtual inline const char* type() const { return ""; }

  virtual void ApplyUpdate() = 0;

 protected:
  string SnapshotFilename(const string& extension);
  string SnapshotToBinaryProto();
  string SnapshotToHDF5();
  void TestAll();
  void Test(const int test_net_id = 0);
  virtual void SnapshotSolverState(const string& model_filename) = 0;
  virtual void RestoreSolverStateFromHDF5(const string& state_file) = 0;
  virtual void RestoreSolverStateFromBinaryProto(const string& state_file) = 0;
  void DisplayOutputBlobs(const int net_id);
  void UpdateSmoothedLoss(Dtype loss, int start_iter, int average_loss);

  SolverParameter param_;
  int iter_;
  int current_step_;
  shared_ptr<Net<Dtype> > net_;
  vector<shared_ptr<Net<Dtype> > > test_nets_;
  vector<Callback*> callbacks_;
  vector<Dtype> losses_;
  Dtype smoothed_loss_;

  ActionCallback action_request_function_;

  bool requested_early_exit_;

  Timer iteration_timer_;
  float iterations_last_;

  DISABLE_COPY_AND_ASSIGN(Solver);
};

}  // namespace caffe

#endif  // CAFFE_SOLVER_HPP_
