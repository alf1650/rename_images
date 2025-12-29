import csv
import re
from collections import Counter
from rename_images_refined import extract_equipment_type

def analyze_others():
    input_file = '/tmp/sample_test_data_500.csv'
    
    misclassified = []
    
    print("Loading data...")
    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['equipment'] == 'other':
                ocr_text = row['ocr_text']
                predicted = extract_equipment_type(ocr_text)
                
                if predicted != 'other':
                    misclassified.append({
                        'filename': row['filename'],
                        'ocr': ocr_text,
                        'predicted': predicted
                    })
    
    print(f"\nTotal 'other' cases re-classified as equipment: {len(misclassified)}")
    
    # Group by predicted type
    by_type = {}
    for item in misclassified:
        p = item['predicted']
        if p not in by_type:
            by_type[p] = []
        by_type[p].append(item)
        
    for p_type in sorted(by_type.keys()):
        items = by_type[p_type]
        print(f"\n=== Re-classified as {p_type.upper()} ({len(items)} cases) ===")
        
        # Find common keywords to explain why
        keywords = []
        for item in items:
            text = item['ocr'].lower()
            if 'glass' in text or 'gla' in text: keywords.append('glass/gla')
            if 'broken' in text: keywords.append('broken')
            if 'missing' in text: keywords.append('missing')
            if 'alarm' in text: keywords.append('alarm')
            if 'bell' in text: keywords.append('bell')
            if 'timer' in text: keywords.append('timer')
            if 'trip' in text: keywords.append('trip')
            if 'pump' in text: keywords.append('pump')
            if 'start' in text: keywords.append('start')
            if 'run' in text: keywords.append('run')
            if 'light' in text: keywords.append('light')
            if 'valve' in text: keywords.append('valve')
            if 'pressure' in text: keywords.append('pressure')
            if 'gauge' in text: keywords.append('gauge')
            if 'capacitor' in text: keywords.append('capacitor')
            if 'bearing' in text: keywords.append('bearing')
            if 'soft starter' in text: keywords.append('soft starter')
            
        common_keywords = Counter(keywords).most_common(5)
        print(f"Top triggers: {', '.join([f'{k} ({v})' for k,v in common_keywords])}")
        
        print("Examples:")
        for i, item in enumerate(items[:5]):
            print(f"  {i+1}. {item['filename']}")
            print(f"     OCR: {item['ocr'][:100]}...")

if __name__ == "__main__":
    analyze_others()
