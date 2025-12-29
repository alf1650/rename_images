#!/usr/bin/env python3
"""
Debug extraction step by step
"""
import re

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

def extract_simple(text):
    """Simplified extraction without ML"""
    print(f"\n  Original text: {text[:100]}")
    
    # Normalize
    text = re.sub(r'[Vv]ishun', 'Yishun', text)
    text = re.sub(r'\bYish[uiurie]{1,4}\b', 'Yishun', text, flags=re.IGNORECASE)
    print(f"  After normalize: {text[:100]}")
    
    # Fix OCR confusions
    text = re.sub(r'[€¢£0O]', '0', text)
    text = re.sub(r'[l1I]', '1', text)
    print(f"  After OCR fix: {text[:100]}")
    
    block_candidate = None
    road_candidate = None
    
    # PATTERN 1
    pattern1 = re.search(r'\b(\d{2,4}[A-Za-z]*)\b\s*[,;~]\s*(Yishun\s+[A-Za-z]+(?:\s+\d+)?)', text, re.IGNORECASE)
    if pattern1:
        block_candidate = pattern1.group(1)
        road_candidate = pattern1.group(2).strip()
        print(f"  ✅ PATTERN 1 matched: block={block_candidate}, road={road_candidate}")
        return block_candidate, road_candidate
    
    # PATTERN 2
    pattern2 = re.search(r'\b(\d{2,4}[A-Za-z]*)\b\s+(Yishun\s+(?:Street|Avenue|Ave|Road|Rd|Ring\s+Road|Central|Industrial\s+Park)(?:\s+\d+)?)', text, re.IGNORECASE)
    if pattern2:
        block_candidate = pattern2.group(1)
        road_candidate = pattern2.group(2).strip()
        print(f"  ✅ PATTERN 2 matched: block={block_candidate}, road={road_candidate}")
        return block_candidate, road_candidate
    
    # PATTERN 2.5
    pattern2_5 = re.search(r'(?:Block|Blk)\s+(\d{2,4}[A-Za-z]*)[,\s]+(Yishun\s+(?:Street|Avenue|Ave|Road|Rd|Ring\s+Road|Central|Industrial\s+Park)(?:\s+\d+)?)', text, re.IGNORECASE)
    if pattern2_5:
        block_candidate = pattern2_5.group(1)
        road_candidate = pattern2_5.group(2).strip()
        print(f"  ✅ PATTERN 2.5 matched: block={block_candidate}, road={road_candidate}")
        return block_candidate, road_candidate
    
    print(f"  ❌ No pattern matched")
    return None, None

# Test cases
test_cases = [
    "Mon 14.30 %oct 2025 311 Yishun Road, 760311 P1&P2 HRM SPOIL",
    "Fri 11.49 Fo/1o2o25 0 Block 628, Yishun Street 12, #07-131,760628",
    "Fri 09.53 Fo/1oy2o25 Blk 618 Yishun Rd, #01-3240",
    "Mon 15.58 ooct 2025 320 Yishun Central, #04-325",
]

print("="*80)
print("STEP-BY-STEP EXTRACTION DEBUG")
print("="*80)

for text in test_cases:
    block, road = extract_simple(text)
    if block:
        print(f"  FINAL: Block={block.upper()}, Road={clean_road_name(road)}\n")
    else:
        print(f"  FINAL: FAILED\n")
