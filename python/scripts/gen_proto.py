"""
Caffe Proto Python 代码生成脚本

功能：
1. 检查 protoc 与 Python protobuf 版本一致性
2. 自动查找 protoc 编译器
3. 编译 caffe.proto 生成 caffe_pb2.py（到 caffeproto/ 和 protos/ 两个位置）

使用方法：
    在 scripts/ 目录下执行: python gen_proto.py
"""
import sys
import os
import subprocess
import re
from pathlib import Path


def find_protoc():
    """查找 protoc 编译器，优先使用 grpc_tools.protoc（与 Python protobuf 版本匹配）"""
    try:
        import grpc_tools
        return "grpc_tools"
    except ImportError:
        pass

    search_paths = []
    if sys.platform == "win32":
        search_paths.extend([
            Path(sys.prefix) / "Library" / "bin" / "protoc.exe",
            Path(sys.prefix) / "Scripts" / "protoc.exe",
        ])
        conda_prefix = os.environ.get("CONDA_PREFIX")
        if conda_prefix:
            search_paths.extend([
                Path(conda_prefix) / "Library" / "bin" / "protoc.exe",
                Path(conda_prefix) / "Scripts" / "protoc.exe",
            ])
    else:
        search_paths.extend([
            Path(sys.prefix) / "bin" / "protoc",
        ])
        conda_prefix = os.environ.get("CONDA_PREFIX")
        if conda_prefix:
            search_paths.append(Path(conda_prefix) / "bin" / "protoc")

    for p in search_paths:
        if p.exists():
            return str(p)

    from shutil import which
    protoc = which("protoc")
    if protoc:
        return protoc

    return None


def get_protoc_version(protoc_path):
    """获取 protoc 版本号"""
    try:
        if protoc_path == "grpc_tools":
            result = subprocess.run(
                [sys.executable, "-m", "grpc_tools.protoc", "--version"],
                capture_output=True, text=True, timeout=10
            )
        else:
            result = subprocess.run(
                [protoc_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
        output = result.stdout.strip()
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", output)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2))
            patch = int(match.group(3)) if match.group(3) else 0
            return major, minor, patch, output
    except Exception as e:
        return None
    return None


def get_python_protobuf_version():
    """获取 Python protobuf runtime 版本号"""
    try:
        from google.protobuf import __version__
        parts = __version__.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return major, minor, patch, __version__
    except ImportError:
        return None


def version_check(protoc_path):
    """
    版本一致性预检。
    
    兼容性规则：
    - Python protobuf runtime 主版本 >= protoc 生成代码的 gencode 主版本
    - protoc 35.x -> gencode 7.35.x (protobuf 7.x 匹配)
    - protoc 29.x-34.x -> gencode 5.29.x-6.x (protobuf 5.x/6.x/7.x 兼容)
    - protoc 25.x-28.x -> gencode 4.x (protobuf 4.x+ 兼容)
    - protoc 3.x -> gencode 3.x (protobuf 3.x+ 兼容)
    - 高版本 runtime 向后兼容低版本 gencode
    
    grpc_tools.protoc 始终与安装的 protobuf Python 包版本精确匹配，无需额外检查
    """
    protoc_ver = get_protoc_version(protoc_path)
    pb_ver = get_python_protobuf_version()

    if protoc_ver is None:
        print(f"ERROR: 无法获取 protoc 版本: {protoc_path}")
        return False

    if pb_ver is None:
        print("ERROR: 无法导入 Python protobuf 库，请先安装: pip install protobuf")
        return False

    p_major, p_minor, p_patch, p_str = protoc_ver
    pb_major, pb_minor, pb_patch, pb_str = pb_ver

    if protoc_path == "grpc_tools":
        print(f"protoc 版本: {p_str} (via grpcio-tools, 与 Python protobuf 精确匹配)")
    else:
        print(f"protoc 版本: {p_str}")
    print(f"Python protobuf 版本: {pb_str}")

    if protoc_path == "grpc_tools":
        print("版本检查通过 ✓ (grpcio-tools 版本精确匹配)")
        return True

    gencode_major = None
    if p_major >= 35:
        gencode_major = 7
    elif p_major >= 29:
        gencode_major = 5
    elif p_major >= 25:
        gencode_major = 4
    elif p_major >= 3:
        gencode_major = 3

    if gencode_major is not None and pb_major < gencode_major:
        print(f"ERROR: 版本不兼容！protoc {p_str} 生成的代码需要 protobuf runtime >= {gencode_major}.0.0，"
              f"但当前为 {pb_str}。建议: pip install grpcio-tools 以获取精确匹配版本")
        return False

    print("版本检查通过 ✓")
    return True


def generate(protoc_path, proto_dir, out_dirs):
    """执行 protoc 编译"""
    proto_file = os.path.join(proto_dir, "caffe.proto")
    if not os.path.exists(proto_file):
        print(f"ERROR: proto 文件不存在: {proto_file}")
        return False

    for out_dir in out_dirs:
        os.makedirs(out_dir, exist_ok=True)
        if protoc_path == "grpc_tools":
            cmd = [
                sys.executable, "-m", "grpc_tools.protoc",
                f"--proto_path={proto_dir}",
                f"--python_out={out_dir}",
                proto_file,
            ]
        else:
            cmd = [
                protoc_path,
                f"--proto_path={proto_dir}",
                f"--python_out={out_dir}",
                proto_file,
            ]
        print(f"生成: {os.path.join(out_dir, 'caffe_pb2.py')}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"ERROR: protoc 编译失败:\n{result.stderr}")
            return False

    print("代码生成完成 ✓")
    return True


def verify_generated(out_dirs):
    """验证生成的代码可正常 import 且包含 NormalizeParameter"""
    for out_dir in out_dirs:
        sys.path.insert(0, out_dir)

    try:
        import importlib
        if "caffe_pb2" in sys.modules:
            importlib.reload(sys.modules["caffe_pb2"])
        import caffe_pb2 as pb2

        np = pb2.NormalizeParameter()
        np.across_spatial = False
        np.channel_shared = True
        np.eps = 1e-10
        np.scale_filler.type = "constant"
        np.scale_filler.value = 20.0

        data = np.SerializeToString()
        np2 = pb2.NormalizeParameter()
        np2.ParseFromString(data)
        assert np2.channel_shared == True
        assert np2.scale_filler.value == 20.0

        lp = pb2.LayerParameter()
        lp.norm_param.across_spatial = False
        assert lp.HasField("norm_param")

        print("生成代码验证通过 ✓ (NormalizeParameter + norm_param 可用)")
        return True
    except Exception as e:
        print(f"ERROR: 生成代码验证失败: {e}")
        return False
    finally:
        for out_dir in out_dirs:
            if out_dir in sys.path:
                sys.path.remove(out_dir)


def main():
    script_dir = Path(__file__).parent.resolve()
    # proto 文件位于项目根目录的 protos/ 下
    proto_dir = str(script_dir.parent.parent / "protos")
    # 输出到 caffeproto/ 和 protos/
    out_dirs = [
        str(script_dir.parent / "caffeproto"),
        str(script_dir.parent / "protos"),
    ]

    print("=" * 50)
    print("Caffe Proto Python 代码生成器")
    print("=" * 50)

    protoc_path = find_protoc()
    if protoc_path is None:
        print("ERROR: 未找到 protoc 编译器。推荐安装方式（版本精确匹配）:")
        print("  pip install grpcio-tools")
        print("备选方式:")
        print("  conda install -c conda-forge libprotobuf")
        print("  或从 https://github.com/protocolbuffers/protobuf/releases 下载")
        sys.exit(1)

    if protoc_path == "grpc_tools":
        print("protoc: grpc_tools.protoc (via grpcio-tools, 版本与 Python protobuf 精确匹配)")
    else:
        print(f"protoc 路径: {protoc_path}")

    if not version_check(protoc_path):
        sys.exit(1)

    if not generate(protoc_path, proto_dir, out_dirs):
        sys.exit(1)

    if not verify_generated(out_dirs):
        sys.exit(1)

    print("=" * 50)
    print("全部完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()