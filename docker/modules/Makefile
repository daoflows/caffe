# ==============================================================================
# Caffe Docker 模块镜像统一构建入口
# ==============================================================================
# 目标:
#   all              - 一键构建全部镜像（先复盘分析，再按序构建）
#   analyze          - 执行项目复盘分析
#   python-module    - 构建 python-module 镜像（主力模块）
#   pycaffe          - 构建 pycaffe 镜像（对标废弃 caffex/python）
#   clean            - 清理构建产物
#
# 用法:
#   make -C docker/modules all
#   make -C docker/modules python-module
#   make -C docker/modules pycaffe
#   make -C docker/modules analyze
#   make -C docker/modules clean
# ==============================================================================

.PHONY: all analyze python-module pycaffe clean

# Docker 镜像标签
PYTHON_MODULE_IMAGE := caffe-cpu:python-module
PYCAFFE_IMAGE := caffe-cpu:pycaffe

# Dockerfile 路径
PYTHON_MODULE_DOCKERFILE := docker/modules/python-module/Dockerfile
PYCAFFE_DOCKERFILE := docker/modules/pycaffe/Dockerfile

# 构建上下文（项目根目录）
BUILD_CONTEXT := .

# ==============================================================================
# 默认目标：一键构建全部
# ==============================================================================
all: analyze python-module pycaffe
	@echo ""
	@echo "=============================================="
	@echo "  全部镜像构建完成！"
	@echo "  - $(PYTHON_MODULE_IMAGE)"
	@echo "  - $(PYCAFFE_IMAGE)"
	@echo "=============================================="

# ==============================================================================
# 复盘分析
# ==============================================================================
analyze:
	@bash docker/modules/scripts/analyze-project.sh

# ==============================================================================
# python-module 镜像（主力模块）
# 含 Caffe 编译 + caffe-slim/ 目录（caffeproto, operators, protos, scripts, tests）
# ==============================================================================
python-module:
	@echo "=============================================="
	@echo "  构建 $(PYTHON_MODULE_IMAGE) 镜像..."
	@echo "=============================================="
	docker build \
		-t $(PYTHON_MODULE_IMAGE) \
		--target runtime \
		-f $(PYTHON_MODULE_DOCKERFILE) \
		$(BUILD_CONTEXT)
	@echo ""
	@echo "  $(PYTHON_MODULE_IMAGE) 构建完成"
	@echo ""
	@echo "  验证镜像..."
	docker run --rm $(PYTHON_MODULE_IMAGE) \
		"verify-python-module.sh"
	@echo ""

# ==============================================================================
# pycaffe 镜像（对标废弃 caffex/python）
# 基于 python-module 镜像，构建 pycaffe wheel 并安装
# ==============================================================================
pycaffe: python-module
	@echo "=============================================="
	@echo "  构建 $(PYCAFFE_IMAGE) 镜像..."
	@echo "=============================================="
	docker build \
		-t $(PYCAFFE_IMAGE) \
		-f $(PYCAFFE_DOCKERFILE) \
		$(BUILD_CONTEXT)
	@echo ""
	@echo "  $(PYCAFFE_IMAGE) 构建完成"
	@echo ""
	@echo "  验证镜像..."
	docker run --rm $(PYCAFFE_IMAGE) \
		"verify-pycaffe.sh"
	@echo ""
	@echo "  对标验证..."
	docker run --rm $(PYCAFFE_IMAGE) \
		"verify-parity.sh"
	@echo ""

# ==============================================================================
# 清理
# ==============================================================================
clean:
	@echo "清理构建产物..."
	-docker rmi $(PYCAFFE_IMAGE) 2>/dev/null || true
	-docker rmi $(PYTHON_MODULE_IMAGE) 2>/dev/null || true
	@echo "清理完成"