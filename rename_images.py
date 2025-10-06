# rename_images.py

import os
import re
import shutil
import cv2
import numpy as np
import easyocr
from datetime import datetime

# --- CONFIGURATION ---
SOURCE_DIR = "/Users/alfredlim/Redpower/rename_images/images"
DEST_DIR   = "/Users/alfredlim/Redpower/rename_images/images_renamed"
FAILED_DIR = "/Users/alfredlim/Redpower/rename_images/failed"

# Initialize EasyOCR reader (once, at startup)
print("Initializing EasyOCR (may take a few seconds)...")
easyocr_reader = easyocr.Reader(['en'], gpu=False)  # Set gpu=True if you have CUDA

# --- FUNCTIONS ---

def extract_equipment_type(text):
    """
    Simplified equipment detection:
      - If 'fire extinguisher' → fire_extinguisher
      - If 'transfer pump'     → transfer_pump
      - If 'pressure tank'     → pressure_tank
      - If 'hosereel'          → hosereel   (covers pump, drum, or just "hosereel")
      - Otherwise              → other
    Note: "NSTC" in text is ignored for logic (since OCR is flat), 
          but if your images always include it, the keywords will still be detected.
    """
    t = text.lower()
    if 'fire extinguisher' in t or re.search(r'\bfire\s*extinguisher\b', t):
        return 'fire_extinguisher'
    if 'transfer pump' in t or re.search(r'\btransfer\s*pump\b', t):
        return 'transfer_pump'
    if 'pressure tank' in t or re.search(r'\bpressure\s*tank\b', t):
        return 'pressure_tank'
    if 'hosereel' in t:
        return 'hosereel'
    return 'other'


def parse_date_from_text(text):
    """
    Extract date from noisy OCR with support for:
      - 28/09/2025, 28-09-2025, 28.09.2025
      - 28092025 (8-digit)
      - 2809/2025, 28.09/2025 (mixed separators)
    Also fixes common OCR errors and validates dates.
    """
    # Pre-clean common OCR substitutions
    cleaned = re.sub(r'[vV]', '/', text)          # v → /
    cleaned = re.sub(r'[Oo]', '0', cleaned)       # O → 0
    cleaned = re.sub(r'[lI]', '1', cleaned)       # l/I → 1
    # Normalize all separators to '/'
    cleaned = re.sub(r'[^\d/]', ' ', cleaned)

    # Patterns to try (in order of reliability)
    patterns = [
        # Standard: 28/09/2025
        r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',
        # Mixed: 2809/2025 → split first 4 digits as DDMM
        r'\b(\d{4})/(\d{4})\b',
        # Compact: 28092025
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

                # Fix common day typos (e.g., 38→28, 39→29, 19→29 in context)
                if day > 31:
                    if day in (38, 39) and month in (9, 10):  # Your data uses 28/29 Sep
                        day = day - 10
                    else:
                        continue
                # Optional: if you know all dates are 28th or 29th Sep 2025:
                if year == 2025 and month == 9 and day == 19:
                    day = 29  # Assume 19 is typo for 29

                # Validate
                d = datetime(year, month, day)
                return f"{d.day:02d}{d.month:02d}{d.year}"
            except (ValueError, OverflowError):
                continue

    return None


def clean_road_name(road_text):
    """
    Clean and standardize road names:
      - stree → street
      - aven → avenue
      - st → street
      - ave → avenue
    """
    road = road_text.lower()
    # Expand common abbreviations
    road = re.sub(r'\bstree\b', 'street', road)
    road = re.sub(r'\baven\b', 'avenue', road)
    road = re.sub(r'\bst\b', 'street', road)
    road = re.sub(r'\bave\b', 'avenue', road)
    # Clean non-alphanumeric (keep spaces)
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


def extract_info_from_ocr(ocr_text):
    """
    Extract block, road, and date from messy OCR.
    Handles "Yi Street", postal codes, and fragmented addresses.
    """
    text = ocr_text.strip()

    # === AGGRESSIVE YISHUN NORMALIZATION ===
    text = re.sub(r'[Vv]ishun', 'Yishun', text)
    # Fix common OCR corruptions of "Yishun"
    text = re.sub(r'\bYish[uiurie]{1,4}\b', 'Yishun', text, flags=re.IGNORECASE)
    # Fix "Yi Street" → "Yishun Street" (critical for your data!)
    text = re.sub(r'\bYi\s+Street\b', 'Yishun Street', text, flags=re.IGNORECASE)
    text = re.sub(r'\bYi\s+St\b', 'Yishun Street', text, flags=re.IGNORECASE)
    text = re.sub(r'\bYi\s+Ave\b', 'Yishun Avenue', text, flags=re.IGNORECASE)
    text = re.sub(r'\bYi\s+Aven\b', 'Yishun Aven', text, flags=re.IGNORECASE)

    # Fix character confusions
    text = re.sub(r'[€¢£0O]', '0', text)
    text = re.sub(r'[l1I]', '1', text)

    # Extract date
    date_str = parse_date_from_text(text)

    # === STEP 1: Get block from postal code (760xxx–763xxx) ===
    postal_match = re.search(r'\b(76[0-3]\d{3})\b', text)
    block_from_postal = None
    if postal_match:
        postal = postal_match.group(1)
        block_from_postal = postal[-3:]  # e.g., 761469 → '469'

    # === STEP 2: Find block + road near "Yishun" ===
    block_candidate = None
    road_candidate = None

    # Pattern: <block> Yishun <road>
    match1 = re.search(r'(\d{2,4}[A-Za-z]?)\s+(Yishun\s+[A-Za-z0-9\s]{3,}?)\s*(?:[,;\.\d]|$)', text, re.IGNORECASE)
    # Pattern: Yishun <road> <block> (less common)
    match2 = re.search(r'(Yishun\s+[A-Za-z0-9\s]{3,}?)\s+(\d{2,4}[A-Za-z]?)\b', text, re.IGNORECASE)

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

    # Final block: prefer postal
    final_block = block_from_postal or block_candidate

    # Final road: clean if found
    final_road = None
    if road_candidate:
        final_road = clean_road_name(road_candidate)

    # If we have postal block but no road, try to extract road after "Yishun"
    if block_from_postal and not final_road:
        yishun_road_match = re.search(r'(Yishun\s+[A-Za-z0-9\s]{3,}?)\s*(?:\d{6}|spoil|[,;\.\s]|$)', text, re.IGNORECASE)
        if yishun_road_match:
            final_road = clean_road_name(yishun_road_match.group(1))

    # === VALIDATE AND RETURN ===
    if final_block and final_road:
        final_block = re.sub(r'[^0-9A-Za-z]', '', final_block)
        if not final_block:
            return None, None, date_str

        if final_block.isdigit():
            block_num = int(final_block)
            if 100 <= block_num <= 9999 and not (2000 <= block_num <= 2099):
                return final_block, final_road, date_str
        elif re.match(r'^\d{2,4}[A-Za-z]$', final_block):
            num_part = re.sub(r'[A-Za-z]', '', final_block)
            if num_part.isdigit():
                block_num = int(num_part)
                if 100 <= block_num <= 9999 and not (2000 <= block_num <= 2099):
                    return final_block.upper(), final_road, date_str

    # Last resort: use postal block + any Yishun fragment
    if block_from_postal and 'yishun' in text.lower():
        yishun_idx = text.lower().find('yishun')
        if yishun_idx != -1:
            road_guess = text[yishun_idx:yishun_idx+60]
            road_guess = re.split(r'[,;\.\d\s]{2,}', road_guess)[0]
            if len(road_guess) > 8:
                final_road = clean_road_name(road_guess)
                return block_from_postal, final_road, date_str

    return None, None, date_str


def process_image(src_path, dest_dir, failed_dir):
    original_name = os.path.basename(src_path)
    try:
        # Step 1: Try cropped watermark OCR
        cropped_img = crop_watermark_precise(src_path)
        results = easyocr_reader.readtext(cropped_img, detail=0)
        ocr_text = " ".join(results)
        print(f"[OCR] {original_name} → {repr(ocr_text)}")

        equipment = extract_equipment_type(ocr_text)
        block, road, date_str = extract_info_from_ocr(ocr_text)

        # Step 2: Fallback to full image OCR if equipment is 'other'
        if equipment == 'other':
            print(f"  ⚠️  Equipment = 'other' — trying full image OCR...")
            full_img = cv2.imread(src_path)
            if full_img is not None:
                full_results = easyocr_reader.readtext(full_img, detail=0, width_ths=0.7, height_ths=0.7)
                full_ocr = " ".join(full_results)
                print(f"  [FULL OCR] → {repr(full_ocr)}")
                better_equipment = extract_equipment_type(full_ocr)
                if better_equipment != 'other':
                    equipment = better_equipment
                    block, road, date_str = extract_info_from_ocr(full_ocr)

        # Step 3: Validate and save
        if not (block and road):
            print(f"⚠️  Failed to parse address: {original_name}")
            shutil.copy2(src_path, os.path.join(failed_dir, original_name))
            return  # Do NOT delete failed files

        # Build new filename
        date_part = date_str if date_str else "nodate"
        name, ext = os.path.splitext(original_name)
        new_name = f"{equipment}_{block}_{road}_{date_part}_{name}{ext}"
        dest_path = os.path.join(dest_dir, new_name)
        shutil.copy2(src_path, dest_path)
        print(f"✅ Saved → {new_name}")

        # ✅ DELETE ORIGINAL FILE AFTER SUCCESSFUL PROCESSING
        os.remove(src_path)
        print(f"🗑️  Deleted original: {original_name}")

    except Exception as e:
        print(f"❌ Critical error on {original_name}: {e}")
        shutil.copy2(src_path, os.path.join(failed_dir, original_name))
        # Do NOT delete on error


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
    print(f"⚠️  Failed output:  '{FAILED_DIR}'\n")

    for filename in image_files:
        print(f"Processing: {filename}")
        src_path = os.path.join(SOURCE_DIR, filename)
        process_image(src_path, DEST_DIR, FAILED_DIR)