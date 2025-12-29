#!/usr/bin/env python3
import re

test_cases = [
    "311 Yishun Road, 760311",
    "31BC Yishun Avenue 9,763315",
    "315C Yishun Avenue 9,763315",
    "Block 628, Yishun Street 12, #07-131,760628",
    "Blk 618 Yishun Rd, #01-3240",
    "320 Yishun Central, #04-325"
]

def clean_road_name(road_text):
    if not road_text:
        return None
    road = road_text.strip()
    road = re.sub(r'\s*\d{6}\s*$', '', road)
    road = re.sub(r'[;,]\s*$', '', road)
    road = re.sub(r'\bstree\b', 'street', road, flags=re.IGNORECASE)
    road = re.sub(r'\baven\b', 'avenue', road, flags=re.IGNORECASE)
    road = re.sub(r'\bst\b(?!\w)', 'street', road, flags=re.IGNORECASE)
    road = re.sub(r'\bave\b(?!\w)', 'avenue', road, flags=re.IGNORECASE)
    road = re.sub(r'\brd\b', 'road', road, flags=re.IGNORECASE)
    road = re.sub(r'[^a-zA-Z0-9\s]', ' ', road)
    road = re.sub(r'\s+', '_', road.strip())
    return road.lower()

for text in test_cases:
    print(f"\nTesting: {text}")
    
    # Normalize
    text_norm = re.sub(r'[Vv]ishun', 'Yishun', text)
    text_norm = re.sub(r'\bYish[uiurie]{1,4}\b', 'Yishun', text_norm, flags=re.IGNORECASE)
    
    # Try patterns
    block_candidate = None
    road_candidate = None
    
    # PATTERN 1
    pattern1 = re.search(r'\b(\d{2,4}[A-Za-z]?)\b\s*[,;~]\s*(Yishun\s+[A-Za-z]+(?:\s+\d+)?)', text_norm, re.IGNORECASE)
    if pattern1:
        block_candidate = pattern1.group(1)
        road_candidate = pattern1.group(2).strip()
        print(f"  ✅ PATTERN 1: Block={block_candidate}, Road={road_candidate}")
    
    # PATTERN 2
    if not block_candidate:
        pattern2 = re.search(r'\b(\d{2,4}[A-Za-z]?)\b\s+(Yishun\s+(?:Street|Avenue|Ave|Road|Rd|Ring\s+Road|Central|Industrial\s+Park)(?:\s+\d+)?)', text_norm, re.IGNORECASE)
        if pattern2:
            block_candidate = pattern2.group(1)
            road_candidate = pattern2.group(2).strip()
            print(f"  ✅ PATTERN 2: Block={block_candidate}, Road={road_candidate}")
    
    # PATTERN 2.5
    if not block_candidate:
        pattern2_5 = re.search(r'(?:Block|Blk)\s+(\d{2,4}[A-Za-z]?)[,\s]+(Yishun\s+(?:Street|Avenue|Ave|Road|Rd|Ring\s+Road|Central|Industrial\s+Park)(?:\s+\d+)?)', text_norm, re.IGNORECASE)
        if pattern2_5:
            block_candidate = pattern2_5.group(1)
            road_candidate = pattern2_5.group(2).strip()
            print(f"  ✅ PATTERN 2.5: Block={block_candidate}, Road={road_candidate}")
    
    if block_candidate:
        cleaned_block = re.sub(r'[^0-9A-Za-z]', '', block_candidate)
        num_part = re.sub(r'[A-Za-z]', '', cleaned_block)
        road_clean = clean_road_name(road_candidate)
        
        if num_part.isdigit() and 100 <= int(num_part) <= 9999 and not (2000 <= int(num_part) <= 2099):
            print(f"  ✅ VALID: Block={cleaned_block.upper()}, Road={road_clean}")
        else:
            print(f"  ❌ INVALID: num_part={num_part}")
    else:
        print(f"  ❌ NO MATCH")
