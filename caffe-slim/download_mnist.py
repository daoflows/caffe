#!/usr/bin/env python3
"""Download LeNet pretrained weights and MNIST test data."""
import os
import sys
import urllib.request
import gzip
import struct
import numpy as np

CAFFE_SLIM_DIR = os.path.dirname(os.path.abspath(__file__))
PYCAFFE_DIR = os.path.join(CAFFE_SLIM_DIR, "pycaffe")

MODEL_URLS = [
    "https://github.com/pertusa/caffe-lenet-mnist/raw/master/lenet_iter_10000.caffemodel",
    "https://raw.githubusercontent.com/pertusa/caffe-lenet-mnist/master/lenet_iter_10000.caffemodel",
    "https://github.com/sergey3d/LeNet-MNIST-Caffe/raw/master/lenet_iter_10000.caffemodel",
    "https://github.com/CSsaan/MNIST-Caffe/raw/master/model/lenet_iter_10000.caffemodel",
]

MNIST_URLS = {
    "test_images": "https://ossci-datasets.s3.amazonaws.com/mnist/t10k-images-idx3-ubyte.gz",
    "test_labels": "https://ossci-datasets.s3.amazonaws.com/mnist/t10k-labels-idx1-ubyte.gz",
}

def download_file(url, dest, expected_size=None):
    """Download a file with progress reporting."""
    print(f"  Downloading: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
        with open(dest, "wb") as f:
            f.write(data)
        size = os.path.getsize(dest)
        print(f"  Saved: {dest} ({size} bytes)")
        if expected_size and size < expected_size * 0.5:
            print(f"  WARNING: File seems too small (expected ~{expected_size} bytes)")
            return False
        return True
    except Exception as e:
        print(f"  Failed: {e}")
        return False

def load_mnist_images(filepath):
    """Load MNIST IDX3 image format."""
    with gzip.open(filepath, "rb") as f:
        magic, num, rows, cols = struct.unpack(">IIII", f.read(16))
        data = np.frombuffer(f.read(), dtype=np.uint8)
        return data.reshape(num, rows, cols)

def load_mnist_labels(filepath):
    """Load MNIST IDX1 label format."""
    with gzip.open(filepath, "rb") as f:
        magic, num = struct.unpack(">II", f.read(8))
        return np.frombuffer(f.read(), dtype=np.uint8)

def main():
    os.makedirs(PYCAFFE_DIR, exist_ok=True)
    data_dir = os.path.join(CAFFE_SLIM_DIR, "data", "mnist")
    os.makedirs(data_dir, exist_ok=True)

    # Step 1: Download caffemodel
    print("=" * 60)
    print("Step 1: Downloading LeNet pretrained weights")
    print("=" * 60)
    model_path = os.path.join(PYCAFFE_DIR, "lenet_iter_10000.caffemodel")
    
    # Expected size ~1.7MB for LeNet
    success = False
    for url in MODEL_URLS:
        if download_file(url, model_path, expected_size=1600000):
            size = os.path.getsize(model_path)
            if size > 1000000:
                print(f"  [OK] Model downloaded successfully ({size} bytes)")
                success = True
                break
            else:
                print(f"  File too small ({size} bytes), trying next URL...")
                os.remove(model_path)
    
    if not success:
        print("  [WARNING] Could not download caffemodel from any URL")
        print("  Continuing with MNIST data download only...")

    # Step 2: Download MNIST test data
    print("\n" + "=" * 60)
    print("Step 2: Downloading MNIST test data")
    print("=" * 60)
    
    images_gz = os.path.join(data_dir, "t10k-images-idx3-ubyte.gz")
    labels_gz = os.path.join(data_dir, "t10k-labels-idx1-ubyte.gz")
    
    if not os.path.exists(images_gz) or os.path.getsize(images_gz) < 1000000:
        download_file(MNIST_URLS["test_images"], images_gz)
    else:
        print(f"  [OK] MNIST images already exist: {images_gz}")
    
    if not os.path.exists(labels_gz) or os.path.getsize(labels_gz) < 10000:
        download_file(MNIST_URLS["test_labels"], labels_gz)
    else:
        print(f"  [OK] MNIST labels already exist: {labels_gz}")
    
    # Step 3: Convert MNIST to numpy
    print("\n" + "=" * 60)
    print("Step 3: Converting MNIST to numpy format")
    print("=" * 60)
    
    try:
        images = load_mnist_images(images_gz)
        labels = load_mnist_labels(labels_gz)
        print(f"  Images shape: {images.shape}, dtype: {images.dtype}")
        print(f"  Labels shape: {labels.shape}, dtype: {labels.dtype}")
        print(f"  Label distribution: {np.bincount(labels)}")
        
        # Save as numpy for easy loading
        np.savez_compressed(
            os.path.join(data_dir, "mnist_test.npz"),
            images=images,
            labels=labels,
        )
        print(f"  Saved: {os.path.join(data_dir, 'mnist_test.npz')}")
    except Exception as e:
        print(f"  Failed to convert MNIST: {e}")
        images = None
        labels = None
    
    print("\n" + "=" * 60)
    print("Download complete!")
    print("=" * 60)
    print(f"  Model: {model_path} ({os.path.getsize(model_path) if os.path.exists(model_path) else 'NOT FOUND'})")
    print(f"  Data:  {os.path.join(data_dir, 'mnist_test.npz')}")

if __name__ == "__main__":
    main()
