#!/usr/bin/env python3
"""
Analyze failed extractions to identify patterns
"""
import re
from collections import Counter

# Sample failed OCR texts from the log
failed_samples = [
    "311 Yishun Road, 760311 P1&P2 HRM SPOIL",
    "31BC Yishun Avenue 9,763315",
    "Block 628, Yishun Street 12, #07-131,760628",
    "Blk 618 Yishun Rd, #01-3240",
    "320 Yishun Central, #04-325",
    "728 Yishun Street 71 , 760728",
    "770 Yishun Avenue 3, 760770",
    "800 Yishun Road, 760800",
    "425 Yishun Avenue 11, 760425",
    "629 Yishun Street 61",
    "802 Yishun Ring Rd,Block 802",
    "259 Yishun Street 22, 760259",
    "806 Yishun Ring Road, 760806",
]

def extract_info_from_ocr(text):
    """Current extraction logic"""
    # Normalize
    text = re.sub(r'[Vv]ishun', 'Yishun', text)
    text = re.sub(r'\bYish[uiurie]{1,4}\b', 'Yishun', text, flags=re.IGNORECASE)
    
    block_candidate = None
    road_candidate = None
    
    # PATTERN 1: "block, Yishun road"
    pattern1 = re.search(r'\b(\d{2,4}[A-Za-z]*)\b\s*[,;~]\s*(Yishun\s+[A-Za-z]+(?:\s+\d+)?)', text, re.IGNORECASE)
    if pattern1:
        block_candidate = pattern1.group(1)
        road_candidate = pattern1.group(2).strip()
        return block_candidate, road_candidate, "PATTERN 1"
    
    # PATTERN 2: "block Yishun road"
    if not block_candidate:
        pattern2 = re.search(r'\b(\d{2,4}[A-Za-z]*)\b\s+(Yishun\s+(?:Street|Avenue|Ave|Road|Rd|Ring\s+Road|Central|Industrial\s+Park)(?:\s+\d+)?)', text, re.IGNORECASE)
        if pattern2:
            block_candidate = pattern2.group(1)
            road_candidate = pattern2.group(2).strip()
            return block_candidate, road_candidate, "PATTERN 2"
    
    # PATTERN 2.5: "Block XXX, Yishun road"
    if not block_candidate:
        pattern2_5 = re.search(r'(?:Block|Blk)\s+(\d{2,4}[A-Za-z]*)[,\s]+(Yishun\s+(?:Street|Avenue|Ave|Road|Rd|Ring\s+Road|Central|Industrial\s+Park)(?:\s+\d+)?)', text, re.IGNORECASE)
        if pattern2_5:
            block_candidate = pattern2_5.group(1)
            road_candidate = pattern2_5.group(2).strip()
            return block_candidate, road_candidate, "PATTERN 2.5"
    
    return None, None, "NO MATCH"

print("="*80)
print("ANALYZING FAILED EXTRACTION PATTERNS")
print("="*80)

for text in failed_samples:
    block, road, pattern = extract_info_from_ocr(text)
    if block:
        print(f"✅ {pattern:12s} | Block={block:6s} Road={road:25s} | {text[:60]}")
    else:
        print(f"❌ {pattern:12s} | {text}")

# Analyze what's common in failed cases
print("\n" + "="*80)
print("PATTERN ANALYSIS")
print("="*80)

# Check if addresses have postal codes
postal_pattern = r'\b(76\d{4})\b'
for text in failed_samples:
    postal = re.search(postal_pattern, text)
    if postal:
        print(f"Postal code found: {postal.group(1)} in '{text[:50]}...'")
