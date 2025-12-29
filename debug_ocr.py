#!/usr/bin/env python3
"""
Debug extraction on actual OCR text from failed images
"""
import sys
sys.path.insert(0, '/Users/alfredlim/Redpower/rename_images')

from rename_images_refined import extract_info_from_ocr

# Real OCR texts from the log
test_cases = [
    ("311 Yishun Road", "Mon 14.30 %oct 2025 311 Yishun Road, 760311 P1&P2 HRM SPOIL ,control switch light"),
    ("Block 628", "Fri 11.49 Fo/1o2o25 0 Block 628, Yishun Street 12, #07-131,760628 P2 run light"),
    ("Blk 618", "Fri 09.53 Fo/1oy2o25 Blk 618 Yishun Rd, #01-3240 P1&P2 Pressure Gage meeter"),
    ("320 Central", "Mon 15.58 ooct 2025 320 Yishun Central, #04-325 P1&P2 HRM SPOIL"),
    ("770 Avenue", "Wed 13.09 Wero/2025 770 Yishun Avenue 3, 760770 P1&P2 HRM"),
]

print("="*80)
print("TESTING ACTUAL OCR EXTRACTION")
print("="*80)

for name, ocr_text in test_cases:
    print(f"\n{name}:")
    print(f"  OCR: {ocr_text[:80]}...")
    
    block, road, date = extract_info_from_ocr(ocr_text)
    
    if block and road:
        print(f"  ✅ Block={block}, Road={road}, Date={date}")
    else:
        print(f"  ❌ FAILED: Block={block}, Road={road}")
