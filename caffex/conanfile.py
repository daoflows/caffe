from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class caffeRecipe(ConanFile):
    name = "caffe"
    version = "1.0"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    generators = "CMakeDeps", "CMakeToolchain"
    # Sources are located in the same place as this recipe, copy them to the recipe
    exports_sources = "CMakeLists.txt", "src/*", "include/*", "caffe.proto"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("protobuf/6.30.1")
        self.requires('boost/1.76.0')
        self.requires('hdf5/1.12.0')
        self.requires('lmdb/0.9.29')
        self.requires('leveldb/1.22')
        self.requires('glog/0.5.0')
        self.requires('gflags/2.2.2')

        if self.settings.os != 'Macos':
            self.requires('openblas/0.3.17')

        if self.options.tests:
            self.requires('gtest/1.10.0')

    def build_requirements(self):
        self.tool_requires("protobuf/<host_version>")

    def layout(self):
        cmake_layout(self)
        # libs/client/caffe/caffe_src/src/caffe/proto/caffe.proto

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["caffe"]
        self.cpp_info.requires = ["protobuf::libprotobuf"]
