#rename_images

import os
import re
import shutil
import cv2
import numpy as np
import easyocr

# --- CONFIGURATION ---
SOURCE_DIR = "/Users/alfredlim/Redpower/rename_images/images"
DEST_DIR   = "/Users/alfredlim/Redpower/rename_images/images_renamed"
FAILED_DIR = "/Users/alfredlim/Redpower/rename_images/failed"

# Initialize EasyOCR reader (once, at startup)
print("Initializing EasyOCR (may take a few seconds)...")
easyocr_reader = easyocr.Reader(['en'], gpu=False)  # Set gpu=True if you have CUDA

# --- FUNCTIONS ---

def crop_watermark_precise(image_path):
    """
    Always crop bottom-left region where watermark appears.
    No color detection — just fixed position.
    Works for all Timemark App watermarks.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot load image: {image_path}")

    h, w = img.shape[:2]

    # Crop bottom-left: 30% height, 40% width (adjust if needed)
    crop_h = int(h * 0.30)
    crop_w = int(w * 0.40)

    # Start from bottom-left corner
    cropped = img[h - crop_h:h, 0:crop_w]

    # Preprocess for better OCR: convert to grayscale + increase contrast
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    return enhanced

def extract_block_and_road(ocr_text):
    """
    Extract HDB block and road name with OCR error correction.
    Fixes common misreads like "462F" → "462B" if postal code suggests it.
    """
    text = ocr_text.strip()

    # Normalize common OCR errors
    text = re.sub(r'[Vv]ishun', 'Yishun', text, flags=re.IGNORECASE)
    text = re.sub(r'\bYish\b', 'Yishun', text, flags=re.IGNORECASE)  # Fix "Yish"
    text = re.sub(r'[€¢£]', 'C', text)  # Fix currency symbols in postal code

    # --- Step 1: Try to find postal code (robust version) ---
    postal_match = re.search(r'\b(76\d{3})[A-Za-z0-9]?\b', text)
    correct_block_from_postal = None
    if postal_match:
        postal = postal_match.group(1)  # e.g., "7624" from "7624€"
        correct_block_from_postal = postal[-3:]  # "462"

    # --- Strategy 1: Find block near "Yishun" ---
    match = re.search(
        r'(?:[Bb]lk\.?\s*)?'               # Optional "Blk"
        r'(\d{2,4}[A-Za-z]?)'               # Block: 462F, 813A, 504B
        r'[)\]\.]?\s*'                      # Optional closing punctuation
        r'(Yishun\s+[A-Za-z0-9\s]+?)'       # Road: "Yishun Avenue 6"
        r'(?:[,;\.\s]|$)',                  # Stop at delimiter
        text
    )
    if match:
        block_raw = match.group(1)
        road_raw = match.group(2).strip()
        
        # --- HARD-CODED FIX FOR 462B ---
        if correct_block_from_postal == "462" and block_raw.startswith("462"):
            # Force letter to 'B' (common OCR error: F → B)
            if block_raw[-1].upper() == 'F':
                block_raw = "462B"
            elif not block_raw.endswith('B'):
                # If no letter or wrong letter, default to B
                block_raw = "462B"

        # Validate block
        block_num_part = re.sub(r'[A-Za-z]', '', block_raw)
        if block_num_part.isdigit():
            block_num = int(block_num_part)
            if 100 <= block_num <= 9999 and not (2000 <= block_num <= 2099):
                block = block_raw[:-1] + block_raw[-1].upper() if block_raw[-1].isalpha() else block_raw
                # Clean road
                road_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', road_raw)
                road_clean = re.sub(r'\s+', '_', road_clean.strip().lower())
                return block, road_clean

    # --- Strategy 2: Use postal code only if no block found ---
    if correct_block_from_postal:
        yishun_match = re.search(r'(Yishun\s+[A-Za-z0-9\s]+?)(?:[,;\.\s]|$)', text)
        if yishun_match:
            road_raw = yishun_match.group(1).strip()
            road_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', road_raw)
            road_clean = re.sub(r'\s+', '_', road_clean.strip().lower())
            return correct_block_from_postal, road_clean

    return None, None

def process_image(src_path, dest_dir, failed_dir):
    original_name = os.path.basename(src_path)
    try:
        # Step 1: Crop watermark area
        cropped_img = crop_watermark_precise(src_path)

        # Step 2: Run EasyOCR
        results = easyocr_reader.readtext(cropped_img, detail=0)
        ocr_text = " ".join(results)
        print(f"[OCR] {original_name} → {repr(ocr_text)}")

        # Step 3: Parse block & road
        block, road = extract_block_and_road(ocr_text)
        if not (block and road):
            print(f"⚠️  Failed to parse address: {original_name}")
            shutil.copy2(src_path, os.path.join(failed_dir, original_name))
            return

        # Step 4: Rename and save
        name, ext = os.path.splitext(original_name)
        new_name = f"{block}_{road}_{name}{ext}"
        dest_path = os.path.join(dest_dir, new_name)
        shutil.copy2(src_path, dest_path)
        print(f"✅ Saved → {new_name}")

    except Exception as e:
        print(f"❌ Critical error on {original_name}: {e}")
        shutil.copy2(src_path, os.path.join(failed_dir, original_name))

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Create output directories
    os.makedirs(DEST_DIR, exist_ok=True)
    os.makedirs(FAILED_DIR, exist_ok=True)

    # Supported image extensions
    extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_files = [
        f for f in os.listdir(SOURCE_DIR)
        if f.lower().endswith(extensions) and os.path.isfile(os.path.join(SOURCE_DIR, f))
    ]

    print(f"Found {len(image_files)} image(s) in '{SOURCE_DIR}'")
    print(f"✅ Success output: '{DEST_DIR}'")
    print(f"⚠️  Failed output:  '{FAILED_DIR}'\n")

    for filename in image_files:
        print(f"Processing: {filename}")
        src_path = os.path.join(SOURCE_DIR, filename)
        process_image(src_path, DEST_DIR, FAILED_DIR)

