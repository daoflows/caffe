if(NOT HAVE_PYTHON)
  message(STATUS "Python interface is disabled or not all required dependencies found. Building without it...")
  return()
endif()

file(GLOB_RECURSE python_srcs ${PROJECT_SOURCE_DIR}/python/*.cpp)


add_library(pycaffe MODULE ${python_srcs})
find_package(Boost REQUIRED COMPONENTS python3)
include_directories(${Boost_INCLUDE_DIRS})
caffe_default_properties(pycaffe)
set_target_properties(pycaffe PROPERTIES PREFIX "" OUTPUT_NAME "_caffe")
target_link_libraries(pycaffe PRIVATE caffe Python3::Module Python3::NumPy boost::boost)
if(MSVC)
  set_target_properties(pycaffe PROPERTIES SUFFIX ".pyd")
endif()


if(UNIX OR APPLE)
    set(__linkname "${PROJECT_SOURCE_DIR}/python/caffe/_caffe.so")
    add_custom_command(TARGET pycaffe POST_BUILD
                       COMMAND ln -sf $<TARGET_LINKER_FILE:pycaffe> "${__linkname}"
                       COMMAND ${CMAKE_COMMAND} -E make_directory ${PROJECT_SOURCE_DIR}/python/caffe/proto
                       COMMAND touch ${PROJECT_SOURCE_DIR}/python/caffe/proto/__init__.py
                       COMMAND cp ${proto_gen_folder}/*.py ${PROJECT_SOURCE_DIR}/python/caffe/proto/
                       COMMENT "Creating symlink ${__linkname} -> ${PROJECT_BINARY_DIR}/lib/_caffe${Caffe_POSTFIX}.so")
elseif(WIN32)
    set(__linkname "${PROJECT_SOURCE_DIR}/python/caffe/_caffe.pyd")
    add_custom_command(TARGET pycaffe POST_BUILD
                       COMMAND ${CMAKE_COMMAND} -E create_symlink $<TARGET_FILE:pycaffe> "${__linkname}"
                       COMMAND ${CMAKE_COMMAND} -E make_directory ${PROJECT_SOURCE_DIR}/python/caffe/proto
                       COMMAND ${CMAKE_COMMAND} -E touch ${PROJECT_SOURCE_DIR}/python/caffe/proto/__init__.py
                       COMMAND (robocopy  "\"${proto_gen_folder}\" \"${PROJECT_SOURCE_DIR}/python/caffe/proto\" *.py") ^& IF %ERRORLEVEL% LEQ 4 set ERRORLEVEL=0
                       COMMENT "Creating symlink ${__linkname} -> ${PROJECT_BINARY_DIR}/lib/_caffe.pyd")
endif()

# ---[ Install
# scripts
file(GLOB python_files *.py requirements.txt)
install(FILES ${python_files} DESTINATION python)

# module
install(DIRECTORY caffe
    DESTINATION python
    FILES_MATCHING
    PATTERN "*.py"
    PATTERN "ilsvrc_2012_mean.npy"
    PATTERN "test" EXCLUDE
    )

# _caffe.so
install(TARGETS pycaffe  DESTINATION python/caffe)

