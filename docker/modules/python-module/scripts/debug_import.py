import sys
print("sys.path:", sys.path)
print()
try:
    import caffeproto
    print("caffeproto imported OK")
    print("dir(caffeproto):", [x for x in dir(caffeproto) if not x.startswith("_")])
    print("caffeproto.caffe_pb2:", getattr(caffeproto, "caffe_pb2", "NOT FOUND"))
except Exception as e:
    print(f"ERROR importing caffeproto: {e}")