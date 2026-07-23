#ifndef CAFFE_UTIL_UPGRADE_PROTO_H_
#define CAFFE_UTIL_UPGRADE_PROTO_H_

#include <string>

#include "caffe/proto/caffe.pb.h"

namespace caffe {

bool NetNeedsUpgrade(const NetParameter& net_param);

bool UpgradeNetAsNeeded(const string& param_file, NetParameter* param);

void ReadNetParamsFromTextFileOrDie(const string& param_file,
                                    NetParameter* param);
void ReadNetParamsFromBinaryFileOrDie(const string& param_file,
                                      NetParameter* param);

bool NetNeedsV0ToV1Upgrade(const NetParameter& net_param);

bool UpgradeV0Net(const NetParameter& v0_net_param, NetParameter* net_param);

bool NetNeedsDataUpgrade(const NetParameter& net_param);

void UpgradeNetDataTransformation(NetParameter* net_param);

bool NetNeedsV1ToV2Upgrade(const NetParameter& net_param);

bool UpgradeV1Net(const NetParameter& v1_net_param, NetParameter* net_param);

bool NetNeedsInputUpgrade(const NetParameter& net_param);

void UpgradeNetInput(NetParameter* net_param);

bool NetNeedsBatchNormUpgrade(const NetParameter& net_param);

void UpgradeNetBatchNorm(NetParameter* net_param);

}  // namespace caffe

#endif
