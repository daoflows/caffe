#!/usr/bin/env python3
"""
步骤2产出：Proto 代码生成脚本演示
=====================================
本脚本演示 gen_proto.py 的核心逻辑：版本检查 + protoc 调用 + 验证。
实际项目中使用 python/python/scripts/gen_proto.py，此文件仅作教学演示。

防御点：
- ✅ 版本兼容性检查（防止protoc版本与Python runtime不匹配导致崩溃）
- ✅ protoc可执行文件自动查找
- ✅ 生成后验证可导入
- ✅ 错误信息包含解决建议
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def find_protoc() -> str:
    """查找系统 protoc 可执行文件"""
    protoc = shutil.which("protoc")
    if protoc is None:
        print("❌ 错误：未找到 protoc 编译器", file=sys.stderr)
        print("   安装方法：conda install -c conda-forge libprotobuf", file=sys.stderr)
        print("   或从 https://github.com/protocolbuffers/protobuf/releases 下载", file=sys.stderr)
        sys.exit(1)
    return protoc


def get_protoc_version(protoc: str) -> tuple[int, int, int]:
    """获取 protoc 版本号"""
    result = subprocess.run(
        [protoc, "--version"],
        capture_output=True, text=True, check=True
    )
    # 输出格式: "libprotoc X.Y.Z"
    parts = result.stdout.strip().split()[-1].split(".")
    return tuple(map(int, parts))  # type: ignore[return-value]


def get_python_proto_version() -> tuple[int, int, int]:
    """获取 Python protobuf runtime 版本"""
    try:
        import google.protobuf
        version_str = google.protobuf.__version__
    except ImportError:
        print("❌ 错误：Python protobuf 库未安装", file=sys.stderr)
        print("   安装方法：pip install protobuf", file=sys.stderr)
        sys.exit(1)
    parts = version_str.split(".")
    return tuple(map(int, parts[:3]))  # type: ignore[return-value]


def check_version_compatibility(
    protoc_ver: tuple[int, int, int],
    python_ver: tuple[int, int, int]
) -> bool:
    """
    检查 protoc 与 Python protobuf runtime 版本兼容性
    规则：major.minor 必须一致（patch可以不同）
    """
    compatible = protoc_ver[:2] == python_ver[:2]
    if not compatible:
        print("❌ 版本不兼容！", file=sys.stderr)
        print(f"   protoc 版本: {protoc_ver[0]}.{protoc_ver[1]}.{protoc_ver[2]}", file=sys.stderr)
        print(f"   Python protobuf: {python_ver[0]}.{python_ver[1]}.{python_ver[2]}", file=sys.stderr)
        print("   要求：major.minor 版本必须一致", file=sys.stderr)
        print("   解决：", file=sys.stderr)
        print(f"   1. 升级 Python protobuf: pip install 'protobuf=={protoc_ver[0]}.{protoc_ver[1]}.*'", file=sys.stderr)
        print(f"   2. 或安装匹配的 protoc {python_ver[0]}.{python_ver[1]}.*", file=sys.stderr)
        return False
    return True


def run_protoc(protoc: str, proto_dir: Path, output_dir: Path, proto_file: str = "caffe.proto") -> bool:
    """执行 protoc 编译"""
    cmd = [
        protoc,
        f"--proto_path={proto_dir}",
        f"--python_out={output_dir}",
        proto_file
    ]
    print(f"🔧 执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ protoc 编译失败:\n{result.stderr}", file=sys.stderr)
        return False
    print("✅ protoc 编译成功")
    return True


def verify_generated_code(output_dir: Path) -> bool:
    """验证生成的代码可正常导入"""
    sys.path.insert(0, str(output_dir))
    try:
        # 验证导入
        import caffe_pb2  # type: ignore

        # 验证新添加的 HardSigmoidParameter 是否存在
        # （防御性检查：字段没添加到proto或生成失败会在这里报错）
        param = caffe_pb2.HardSigmoidParameter()
        assert hasattr(param, "alpha"), "HardSigmoidParameter 缺少 alpha 字段"
        assert hasattr(param, "beta"), "HardSigmoidParameter 缺少 beta 字段"

        # 验证默认值正确
        assert abs(param.alpha - 0.2) < 1e-6, f"alpha 默认值错误: {param.alpha}"
        assert abs(param.beta - 0.5) < 1e-6, f"beta 默认值错误: {param.beta}"

        # 验证字段可赋值和序列化往返
        param.alpha = 0.1
        param.beta = 0.6
        serialized = param.SerializeToString()
        param2 = caffe_pb2.HardSigmoidParameter()
        param2.ParseFromString(serialized)
        assert abs(param2.alpha - 0.1) < 1e-6, "序列化往返失败"
        assert abs(param2.beta - 0.6) < 1e-6, "序列化往返失败"

        print("✅ 生成代码验证通过：HardSigmoidParameter 可正常使用")
        return True
    except ImportError as e:
        print(f"❌ 生成代码导入失败: {e}", file=sys.stderr)
        return False
    except AssertionError as e:
        print(f"❌ 生成代码验证失败: {e}", file=sys.stderr)
        return False
    finally:
        if str(output_dir) in sys.path:
            sys.path.remove(str(output_dir))


def main() -> int:
    """主流程"""
    print("=" * 60)
    print("Caffe Proto 代码生成器（演示版）")
    print("=" * 60)

    # 1. 查找 protoc
    protoc = find_protoc()
    protoc_ver = get_protoc_version(protoc)
    print(f"📦 找到 protoc: {protoc} (版本 {protoc_ver[0]}.{protoc_ver[1]}.{protoc_ver[2]})")

    # 2. 检查 Python protobuf 版本
    python_ver = get_python_proto_version()
    print(f"📦 Python protobuf: {python_ver[0]}.{python_ver[1]}.{python_ver[2]}")

    # 3. 版本兼容性检查
    if not check_version_compatibility(protoc_ver, python_ver):
        return 1

    # 4. 确定路径（实际项目中从配置读取）
    script_dir = Path(__file__).parent
    proto_dir = script_dir  # 演示：proto在当前目录
    output_dir = script_dir / "generated"
    output_dir.mkdir(exist_ok=True)

    # 对于演示，我们需要先生成一个最小的caffe.proto
    demo_proto = proto_dir / "caffe.proto"
    if not demo_proto.exists():
        create_demo_proto(demo_proto)

    # 5. 运行 protoc
    if not run_protoc(protoc, proto_dir, output_dir):
        return 1

    # 6. 验证生成结果
    if not verify_generated_code(output_dir):
        return 1

    print("\n" + "=" * 60)
    print("🎉 Proto 代码生成完成！")
    print(f"📂 输出目录: {output_dir}")
    print("=" * 60)
    return 0


def create_demo_proto(path: Path) -> None:
    """创建演示用的最小 caffe.proto（仅包含HardSigmoidParameter）"""
    content = '''syntax = "proto2";

package caffe;

message HardSigmoidParameter {
  optional float alpha = 1 [default = 0.2];
  optional float beta = 2 [default = 0.5];
}

message LayerParameter {
  optional HardSigmoidParameter hardsigmoid_param = 1;
}
'''
    path.write_text(content, encoding="utf-8")
    print(f"📝 创建演示 proto: {path}")


if __name__ == "__main__":
    sys.exit(main())
