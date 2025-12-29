#!/usr/bin/env python3
"""
Enhanced test script with 100 real OCR examples from success log
"""
import re
import csv

from rename_images_refined import extract_equipment_type



# Read test data from CSV
test_cases = []
with open('/tmp/sample_test_data_500.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ocr_text = row['ocr_text']
        expected = row['equipment']
        test_cases.append((ocr_text, expected, row['filename']))

print(f"Testing Equipment Detection with {len(test_cases)} Real Examples")
print("="*80)

passed = 0
failed = 0
failures_by_type = {'tp': [], 'bp': [], 'hr': [], 'fe': [], 'other': [], 'rhe': [], 'pt': []}
confusion_matrix = {}

for ocr_text, expected, filename in test_cases:
    result = extract_equipment_type(ocr_text)
    
    # Track confusion matrix
    key = f"{expected}→{result}"
    confusion_matrix[key] = confusion_matrix.get(key, 0) + 1
    
    if result == expected:
        passed += 1
    else:
        failed += 1
        failures_by_type[expected].append({
            'filename': filename,
            'ocr': ocr_text[:100],
            'expected': expected,
            'got': result
        })

print(f"\n{'='*80}")
print(f"OVERALL RESULTS: {passed}/{len(test_cases)} passed ({100*passed/len(test_cases):.1f}%)")
print(f"{'='*80}\n")

# Show confusion matrix
print("CONFUSION MATRIX:")
print("-"*80)
for key in sorted(confusion_matrix.keys()):
    expected, result = key.split('→')
    count = confusion_matrix[key]
    status = "✅" if expected == result else "❌"
    print(f"{status} {expected:8s} → {result:8s}: {count:3d} cases")

# Show failures by type
print(f"\n{'='*80}")
print("FAILURES BY EXPECTED TYPE:")
print("="*80)

for eq_type in ['tp', 'bp', 'hr', 'fe', 'other', 'rhe', 'pt']:
    failures = failures_by_type[eq_type]
    if failures:
        print(f"\n{eq_type.upper()} Misclassifications: {len(failures)}")
        print("-"*80)
        for i, failure in enumerate(failures[:5], 1):  # Show first 5
            print(f"{i}. {failure['filename']}")
            print(f"   OCR: {failure['ocr']}...")
            print(f"   Expected: {failure['expected']}, Got: {failure['got']}")
        if len(failures) > 5:
            print(f"   ... and {len(failures)-5} more")

# Summary statistics
print(f"\n{'='*80}")
print("SUMMARY BY EQUIPMENT TYPE:")
print("="*80)
type_stats = {}
for ocr_text, expected, filename in test_cases:
    if expected not in type_stats:
        type_stats[expected] = {'total': 0, 'correct': 0}
    type_stats[expected]['total'] += 1
    result = extract_equipment_type(ocr_text)
    if result == expected:
        type_stats[expected]['correct'] += 1

for eq_type in sorted(type_stats.keys()):
    stats = type_stats[eq_type]
    accuracy = 100 * stats['correct'] / stats['total']
    print(f"{eq_type:8s}: {stats['correct']:3d}/{stats['total']:3d} correct ({accuracy:5.1f}%)")
