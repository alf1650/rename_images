#!/usr/bin/env python3
"""
Test script to process a small batch of images
"""
import os
import sys

# Temporarily modify SOURCE_DIR for testing
import rename_images_refined as rir

# Override directories for test
rir.SOURCE_DIR = "/tmp/test_images"
rir.DEST_DIR = "/tmp/test_renamed"
rir.FAILED_DIR = "/tmp/test_failed"

# Create test directory and copy 5 images
os.makedirs(rir.SOURCE_DIR, exist_ok=True)
os.makedirs(rir.DEST_DIR, exist_ok=True)
os.makedirs(rir.FAILED_DIR, exist_ok=True)

import shutil
source_images = "/Users/alfredlim/Redpower/rename_images/images"
test_count = 5

# Copy first 5 images
copied = 0
for filename in os.listdir(source_images):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        src = os.path.join(source_images, filename)
        dst = os.path.join(rir.SOURCE_DIR, filename)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            copied += 1
            print(f"Copied: {filename}")
            if copied >= test_count:
                break

print(f"\n✅ Copied {copied} test images to {rir.SOURCE_DIR}")
print(f"Running rename script...\n")

# Load dependencies
rir.load_dependencies()

# Process images
extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
image_files = [
    f for f in os.listdir(rir.SOURCE_DIR)
    if f.lower().endswith(extensions) and os.path.isfile(os.path.join(rir.SOURCE_DIR, f))
]

print(f"Found {len(image_files)} image(s) to process\n")

for filename in image_files:
    print(f"Processing: {filename}")
    src_path = os.path.join(rir.SOURCE_DIR, filename)
    rir.process_image(src_path, rir.DEST_DIR, rir.FAILED_DIR)
    print()

print("\n" + "="*80)
print("RESULTS:")
print("="*80)
print(f"✅ Renamed: {len(os.listdir(rir.DEST_DIR))} files")
print(f"⚠️  Failed: {len(os.listdir(rir.FAILED_DIR))} files")
print(f"📁 Renamed files location: {rir.DEST_DIR}")
print(f"📁 Failed files location: {rir.FAILED_DIR}")
