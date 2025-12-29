# rename_images.py

import os
import re
import shutil
import cv2
import numpy as np
import easyocr
from datetime import datetime
import csv

# --- CONFIGURATION ---
SOURCE_DIR = "/Users/alfredlim/Redpower/rename_images/images"
DEST_DIR   = "/Users/alfredlim/Redpower/rename_images/images_renamed"
FAILED_DIR = "/Users/alfredlim/Redpower/rename_images/failed"
LOG_FILE   = "/Users/alfredlim/Redpower/rename_images/success_log.csv"
ML_TRAINING_DATA = "/Users/alfredlim/Redpower/rename_images/ml_training_data.csv"

# Initialize EasyOCR reader (once, at startup)
print("Initializing EasyOCR (may take a few seconds)...")
easyocr_reader = easyocr.Reader(['en'], gpu=True)  # Set gpu=True if you have CUDA

# --- FUNCTIONS ---

def extract_equipment_type(text):
    """
    Extract equipment type by matching ONLY uppercase standalone abbreviations:
      BP, TP, PT, HR, FE, RHE
    Priority order: BP > TP > PT > HR > FE > RHE
    Uses case-sensitive word boundaries to avoid false matches from words like 'Fern'.
    """
    if re.search(r'\bBP\b', text):
        return 'bp'
    elif re.search(r'\bTP\b', text):
        return 'tp'
    elif re.search(r'\bPT\b', text):
        return 'pt'
    elif re.search(r'\bHR\b', text):
        return 'hr'
    elif re.search(r'\bFE\b', text):
        return 'fe'
    elif re.search(r'\bRHE\b', text):
        return 'rhe'
    else:
        return 'other'

def parse_date_from_text(text):
    """
    Extract date from noisy OCR with support for:
      - 28/09/2025, 28-09-2025, 28.09.2025
      - 28092025 (8-digit)
      - 2809/2025, 28.09/2025 (mixed separators)
    Also fixes common OCR errors and validates dates.
    """
    cleaned = re.sub(r'[vV]', '/', text)
    cleaned = re.sub(r'[Oo]', '0', cleaned)
    cleaned = re.sub(r'[lI]', '1', cleaned)
    cleaned = re.sub(r'[^\d/]', ' ', cleaned)

    patterns = [
        r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',
        r'\b(\d{4})/(\d{4})\b',
        r'\b(\d{8})\b',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, cleaned):
            try:
                groups = match.groups()
                if pattern == patterns[0]:  # DD/MM/YYYY
                    day, month, year = groups
                elif pattern == patterns[1]:  # DDMM/YYYY
                    ddmm, year = groups
                    if len(ddmm) == 4:
                        day, month = ddmm[:2], ddmm[2:4]
                    else:
                        continue
                elif pattern == patterns[2]:  # DDMMYYYY
                    ddmmyyyy = groups[0]
                    day, month, year = ddmmyyyy[:2], ddmmyyyy[2:4], ddmmyyyy[4:8]
                else:
                    continue

                day = int(day)
                month = int(month)
                year = int(year)

                if day > 31:
                    if day in (38, 39) and month in (9, 10):
                        day = day - 10
                    else:
                        continue
                if year == 2025 and month == 9 and day == 19:
                    day = 29

                d = datetime(year, month, day)
                return f"{d.day:02d}{d.month:02d}{d.year}"
            except (ValueError, OverflowError):
                continue

    return None

def clean_road_name(road_text):
    road = road_text.lower()
    road = re.sub(r'\bstree\b', 'street', road)
    road = re.sub(r'\baven\b', 'avenue', road)
    road = re.sub(r'\bst\b', 'street', road)
    road = re.sub(r'\bave\b', 'avenue', road)
    road = re.sub(r'[^a-zA-Z0-9\s]', ' ', road)
    road = re.sub(r'\s+', '_', road.strip())
    return road

def crop_watermark_precise(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot load image: {image_path}")
    h, w = img.shape[:2]
    crop_h = int(h * 0.30)
    crop_w = int(w * 0.40)
    cropped = img[h - crop_h:h, 0:crop_w]
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return enhanced

def build_correction_rules_from_log():
    """Learn common OCR → correct mappings from success log"""
    corrections = {}
    if not os.path.exists(LOG_FILE):
        return corrections
    try:
        with open(LOG_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ocr_text = row['ocr_text']
                correct_block = row['block']
                correct_road = row['road']
                block_num = re.sub(r'[A-Za-z]', '', correct_block)
                if block_num:
                    corrupted_match = re.search(rf'\b{block_num}[\/\\,\s]?\b', ocr_text)
                    if corrupted_match:
                        corrupted = corrupted_match.group().strip()
                        if corrupted != correct_block:
                            corrections[corrupted] = correct_block
                if 'yishun' in correct_road.lower():
                    yishun_match = re.search(r'\b(Yi[shn]*[ea]?)\b', ocr_text, re.IGNORECASE)
                    if yishun_match:
                        bad_yishun = yishun_match.group()
                        if bad_yishun.lower() != 'yishun':
                            corrections[bad_yishun] = 'Yishun'
    except Exception as e:
        print(f"⚠️ Error reading log: {e}")
    return corrections

def log_success(filename, original_ocr, block, road, equipment, date_str):
    """Log successful extraction for rule learning"""
    try:
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(['filename', 'ocr_text', 'block', 'road', 'equipment', 'date'])
            writer.writerow([filename, original_ocr, block, road, equipment, date_str])
    except Exception as e:
        print(f"⚠️ Error writing to log: {e}")

def save_training_pair(filename, watermark_ocr, block, road, equipment, date_str):
    """Save (watermark_ocr, block, road) pairs for ML training"""
    try:
        with open(ML_TRAINING_DATA, 'a', newline='') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(['filename', 'watermark_ocr', 'block_label', 'road_label', 'equipment_label', 'date_label'])
            writer.writerow([filename, watermark_ocr, block, road, equipment, date_str])
    except Exception as e:
        print(f"⚠️ Error saving training pair: {e}")

def extract_info_from_ocr(ocr_text):
    text = ocr_text.strip()

    # Apply learned corrections from past successes
    correction_rules = build_correction_rules_from_log()
    for bad, good in correction_rules.items():
        text = re.sub(re.escape(bad), good, text, flags=re.IGNORECASE)

    # === Yishun Normalization ===
    text = re.sub(r'[Vv]ishun', 'Yishun', text)
    text = re.sub(r'\bYish[uiurie]{1,4}\b', 'Yishun', text, flags=re.IGNORECASE)
    text = re.sub(r'\bYi\s+Street\b', 'Yishun Street', text, flags=re.IGNORECASE)
    text = re.sub(r'\bYi\s+St\b', 'Yishun Street', text, flags=re.IGNORECASE)
    text = re.sub(r'\bYi\s+Ave\b', 'Yishun Avenue', text, flags=re.IGNORECASE)
    text = re.sub(r'\bYi\s+Aven\b', 'Yishun Aven', text, flags=re.IGNORECASE)

    # Fix common OCR confusions
    text = re.sub(r'[€¢£0O]', '0', text)
    text = re.sub(r'[l1I]', '1', text)
    text = re.sub(r'(\d{3})\s*/\s*([A-Za-z])?', r'\1\2', text)
    text = re.sub(r'(\d{3})\s*/', r'\1A', text)
    text = re.sub(r'(\d{3})\s*[\/\\]\s*([A-Za-z])', r'\1\2', text)
    text = re.sub(r'(\d{3})\s*(?:[\/\\]|,\s*|\s+)([A-Za-z])', r'\1\2', text)
    text = re.sub(r'(\d{3})\s+([A-Za-z])', r'\1\2', text)

    # Extract date
    date_str = parse_date_from_text(text)

    # === STEP 1: Find block and road near "Yishun" ===
    block_candidate = None
    road_candidate = None

    # Look for "block Yishun road" or "Yishun road block"
    match1 = re.search(r'(\d{2,4}[A-Za-z]?[/\\]?)\s+(Yishun\s+[A-Za-z0-9\s]{3,}?)\s*(?:[,;\.\d]|$)', text, re.IGNORECASE)
    match2 = re.search(r'(Yishun\s+[A-Za-z0-9\s]{3,}?)\s+(\d{2,4}[A-Za-z]?[/\\]?)\b', text, re.IGNORECASE)

    if match1:
        block_candidate = match1.group(1)
        road_candidate = match1.group(2)
    elif match2:
        road_candidate = match2.group(1)
        block_candidate = match2.group(2)

    # Fallback: MSCP/Blk patterns
    if not block_candidate:
        mscp_match = re.search(r'(?:MSCP|Blk|Block)\s*(\d{2,4}[A-Za-z]?)', text, re.IGNORECASE)
        if mscp_match:
            block_candidate = mscp_match.group(1)

    # Fallback: Extract from context near "Yishun"
    if not block_candidate and 'yishun' in text.lower():
        address_match = re.search(r'(?:Yishun\s+[A-Za-z0-9\s]*?,\s*|\s*)(\d{2,4}[A-Za-z]?)[,\s]*', text, re.IGNORECASE)
        if address_match:
            block_candidate = address_match.group(1)

    # Finalize
    final_block = block_candidate
    final_road = clean_road_name(road_candidate) if road_candidate else None

    # Validate block
    if final_block and final_road:
        cleaned_block = re.sub(r'[^0-9A-Za-z]', '', final_block)
        num_part = re.sub(r'[A-Za-z]', '', cleaned_block)
        if num_part.isdigit() and 100 <= int(num_part) <= 9999 and not (2000 <= int(num_part) <= 2099):
            return final_block.upper(), final_road, date_str

    return None, None, date_str

def extract_ground_truth_from_full_ocr(full_ocr):
    """
    Extract block and road from full OCR text using heuristic rules.
    Returns: (block, road, date_str, equipment)
    """
    # Extract equipment FIRST using uppercase-only logic
    equipment = extract_equipment_type(full_ocr)
    
    # Extract date
    date_str = parse_date_from_text(full_ocr)

    # Clean text for address parsing (but keep original for equipment)
    text = full_ocr.strip()
    text = re.sub(r'[vV]', '/', text)
    text = re.sub(r'[Oo]', '0', text)
    text = re.sub(r'[lI]', '1', text)
    text = re.sub(r'[€¢£]', '0', text)
    text = re.sub(r'\s+', ' ', text)  # Normalize spaces

    # === Block and road extraction patterns ===
    block_patterns = [
        r'(\d{3}[A-Za-z])\s+Yishun',
        r'Yishun.*?(\d{3}[A-Za-z])\s+',
        r'(Yishun\s+[A-Za-z0-9\s]{2,})\s+(\d{3}[A-Za-z])',
        r'(\d{3}[A-Za-z])\s+(Yishun\s+[A-Za-z0-9\s]{2,})',
        r'(Yishun\s+[A-Za-z0-9\s]{2,})[,\s]+(\d{3}[A-Za-z])',
        r'Blk\s*(\d{2,4}[A-Za-z]?)',
        r'(\d{2,4}[A-Za-z]?)\s+Yishun',
        r'Yishun.*?(\d{2,4}[A-Za-z]?)\s+',
        r'(Yishun\s+[A-Za-z0-9\s]{2,})\s+(\d{2,4}[A-Za-z]?)',
        r'(\d{2,4}[A-Za-z]?)\s+(Yishun\s+[A-Za-z0-9\s]{2,})',
    ]

    for pattern in block_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                if 'Yishun' in groups[0]:
                    road_candidate = groups[0]
                    block_candidate = groups[1]
                else:
                    block_candidate = groups[0]
                    road_candidate = groups[1]
            else:
                block_candidate = groups[0]
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]
                yishun_match = re.search(r'(Yishun\s+[A-Za-z0-9\s]{2,})', context, re.IGNORECASE)
                if yishun_match:
                    road_candidate = yishun_match.group(1)
                else:
                    road_candidate = "yishun"
            
            block_clean = re.sub(r'[^0-9A-Za-z]', '', str(block_candidate))
            
            # Skip if looks like a year (2025, etc.)
            if len(block_clean) >= 4 and block_clean.isdigit():
                if 2000 <= int(block_clean) <= 2099:
                    continue
            
            num_part = re.sub(r'[A-Za-z]', '', block_clean)
            
            if num_part.isdigit() and 100 <= int(num_part) <= 9999:
                road_clean = clean_road_name(road_candidate) if 'Yishun' in str(road_candidate) else "yishun"
                return block_clean.upper(), road_clean, date_str, equipment

    # === Postal code fallback ===
    postal_match = re.search(r'\b(76[0-3]\d{3})\b', text)
    if postal_match:
        postal = postal_match.group(1)
        block_num = postal[-3:]
        near_postal = text[postal_match.start()-50:postal_match.end()+50]
        block_near_postal = re.search(r'(\d{2,4}[A-Za-z]?)\s*Yishun', near_postal, re.IGNORECASE)
        if block_near_postal:
            block_candidate = block_near_postal.group(1)
            block_clean = re.sub(r'[^0-9A-Za-z]', '', block_candidate)
            if len(block_clean) >= 4 and block_clean.isdigit():
                if 2000 <= int(block_clean) <= 2099:
                    block_clean = block_num + "B"
            else:
                num_part = re.sub(r'[A-Za-z]', '', block_clean)
                if num_part.isdigit() and 100 <= int(num_part) <= 9999:
                    yishun_match = re.search(r'(Yishun\s+[A-Za-z0-9\s]{2,})', near_postal, re.IGNORECASE)
                    road_clean = clean_road_name(yishun_match.group(1)) if yishun_match else "yishun"
                    return block_clean.upper(), road_clean, date_str, equipment

    return None, None, date_str, equipment

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    os.makedirs(DEST_DIR, exist_ok=True)
    os.makedirs(FAILED_DIR, exist_ok=True)

    extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_files = [
        f for f in os.listdir(SOURCE_DIR)
        if f.lower().endswith(extensions) and os.path.isfile(os.path.join(SOURCE_DIR, f))
    ]

    print(f"Found {len(image_files)} image(s) in '{SOURCE_DIR}'")
    print(f"✅ Success output: '{DEST_DIR}'")
    print(f"⚠️  Failed output:  '{FAILED_DIR}'")
    print(f"📊 ML Training data will be saved to: '{ML_TRAINING_DATA}'\n")

    for filename in image_files:
        print(f"Processing: {filename}")
        src_path = os.path.join(SOURCE_DIR, filename)
        process_image(src_path, DEST_DIR, FAILED_DIR)
        