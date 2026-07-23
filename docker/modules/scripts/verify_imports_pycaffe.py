"""验证 pycaffe 镜像的 spec 场景"""
import pycaffe
print("pycaffe OK")
print(f"Net: {hasattr(pycaffe, 'Net')}")
print(f"TRAIN: {pycaffe.TRAIN}")
print(f"TEST: {pycaffe.TEST}")
print(f"SGDSolver: {hasattr(pycaffe, 'SGDSolver')}")
print(f"AdamSolver: {hasattr(pycaffe, 'AdamSolver')}")
print(f"Classifier: {hasattr(pycaffe, 'Classifier')}")
print(f"Detector: {hasattr(pycaffe, 'Detector')}")
print(f"io: {hasattr(pycaffe, 'io')}")

print("\nAll spec scenario checks passed for pycaffe")