#!/usr/bin/env python3
"""
Test script to verify equipment detection improvements
"""
import re

def extract_equipment_type(text):
    """
    Equipment detection with priority to avoid false positives.
    Order: Transfer Pump > Booster Pump > Hosereel > Fire Extinguisher > Others
    Handles split phrases and OCR noise.
    """
    t = text.lower().strip()
    
    # === PREPROCESSING: Handle common OCR errors ===
    # Fix common character substitutions that affect pump detection
    t_cleaned = t
    t_cleaned = re.sub(r'\bpurnp\b', 'pump', t_cleaned)  # OCR: purnp -> pump
    t_cleaned = re.sub(r'\bpumo\b', 'pump', t_cleaned)   # OCR: pumo -> pump
    t_cleaned = re.sub(r'\bpurnpo\b', 'pump', t_cleaned) # OCR: purnpo -> pump
    t_cleaned = re.sub(r'\bpuypno\b', 'pump', t_cleaned) # OCR: puypno -> pump (from log)
    t_cleaned = re.sub(r'\btransier\b', 'transfer', t_cleaned)  # OCR: transier -> transfer
    t_cleaned = re.sub(r'\btranster\b', 'transfer', t_cleaned)  # OCR: transter -> transfer
    t_cleaned = re.sub(r'\bboosier\b', 'booster', t_cleaned)    # OCR: boosier -> booster
    t_cleaned = re.sub(r'\bboster\b', 'booster', t_cleaned)     # OCR: boster -> booster
    t_cleaned = re.sub(r'\bstart\b', 'start', t_cleaned)        # Normalize
    t_cleaned = re.sub(r'\bruy\b', 'run', t_cleaned)            # OCR: ruy -> run
    t_cleaned = re.sub(r'\bru\b', 'run', t_cleaned)             # OCR: ru -> run
    t_cleaned = re.sub(r'\bjrip\b', 'trip', t_cleaned)          # OCR: jrip -> trip
    t_cleaned = re.sub(r'\blught\b', 'light', t_cleaned)        # OCR: lught -> light
    t_cleaned = re.sub(r'\blughi\b', 'light', t_cleaned)        # OCR: lughi -> light
    t_cleaned = re.sub(r'\bhrm\b', 'hrm', t_cleaned)            # Normalize HRM

    # === STEP 1: Check for TRANSFER PUMP FIRST (highest priority) ===
    # Pattern 1: Look for "TP" label followed by pump-related text
    if re.search(r'\btp\b.*?(?:pump|start|run|light|trip)', t_cleaned):
        # Make sure it's not BP
        if not re.search(r'\bbp\b', t_cleaned) and not re.search(r'\bbooster\b', t_cleaned):
            return 'tp'
    
    # Pattern 2: Look for pump control panel text that indicates Transfer Pump
    # Common patterns: "PUMP No.2 START RUN LIGHT TRIP LIGHT" etc.
    if re.search(r'pump\s*no\.?\s*[12].*?(?:start|run|trip)', t_cleaned, re.IGNORECASE):
        # Check if there's any booster indication
        if not re.search(r'\bbooster\b', t_cleaned) and not re.search(r'\bbp\b', t_cleaned):
            # Check if there's transfer indication OR no specific type mentioned
            if re.search(r'\btransfer\b', t_cleaned) or not re.search(r'\bhosereel\b', t_cleaned):
                return 'tp'
    
    # Pattern 3: Look for number + start/run/trip pattern (common in pump panels)
    # e.g., "2 Start Run", "No 2 Start", etc.
    if re.search(r'(?:no\.?\s*)?[12]\s+(?:start|run|trip)', t_cleaned, re.IGNORECASE):
        # Make sure it's not BP or hosereel
        if not re.search(r'\bbooster\b', t_cleaned) and not re.search(r'\bbp\b', t_cleaned) and not re.search(r'\bhosereel\b', t_cleaned):
            return 'tp'
    
    # Pattern 4: Look for P1/P2 indicators with pump-related keywords
    # Common in pump control panels: "P1 HRM SPOIL", "P1 & P2 Run Light", "P1 light"
    # But be more specific to avoid false positives
    if re.search(r'\bp[12]\b.*?(?:run|trip|start)', t_cleaned, re.IGNORECASE):
        # Make sure it's not explicitly BP or hosereel
        if not re.search(r'\bbp\b', t_cleaned) and not re.search(r'\bbooster\b', t_cleaned) and not re.search(r'\bhosereel\s*pump\b', t_cleaned):
            return 'tp'
    # Also check for P1 HRM specifically (common TP indicator)
    if re.search(r'\bp1\b.*?\bhrm\b', t_cleaned, re.IGNORECASE):
        if not re.search(r'\bbp\b', t_cleaned) and not re.search(r'\bbooster\b', t_cleaned):
            return 'tp'
    
    # Pattern 5: Look for "incoming light" pattern (common in pump panels)
    if re.search(r'incoming\s*light', t_cleaned, re.IGNORECASE):
        # Make sure it's not BP or hosereel
        if not re.search(r'\bbp\b', t_cleaned) and not re.search(r'\bbooster\b', t_cleaned) and not re.search(r'\bhosereel\b', t_cleaned):
            return 'tp'
    
    # Pattern 6: Allow up to 5 words between "transfer" and "pump"
    if re.search(r'\btransfer\b(?:\s+\w+){0,5}\s+\bpump\b', t_cleaned):
        return 'tp'
    # Allow "pump" before "transfer"
    if re.search(r'\bpump\b(?:\s+\w+){0,5}\s+\btransfer\b', t_cleaned):
        return 'tp'
    # Exact phrase
    if re.search(r'\btransfer\s*pump\b', t_cleaned):
        return 'tp'

    # === STEP 2: Check for BOOSTER PUMP (second priority) ===
    # Pattern 1: Look for "BP" label followed by pump-related text
    if re.search(r'\bbp\b.*?(?:pump|start|run|light|trip)', t_cleaned):
        return 'bp'
    
    # Pattern 2: Look for P2 with press gauge (common BP indicator)
    if re.search(r'\bp2\b.*?press\s*gauge', t_cleaned, re.IGNORECASE):
        return 'bp'
    
    # Pattern 3: Allow up to 5 words between "booster" and "pump"
    if re.search(r'\bbooster\b(?:\s+\w+){0,5}\s+\bpump\b', t_cleaned):
        return 'bp'
    # Allow "pump" before "booster"
    if re.search(r'\bpump\b(?:\s+\w+){0,5}\s+\bbooster\b', t_cleaned):
        return 'bp'
    # Exact phrase
    if re.search(r'\bbooster\s*pump\b', t_cleaned):
        return 'bp'

    # === STEP 3: Check for HOSEREEL (third priority) ===
    if re.search(r'\bhosereel\b', t_cleaned):
        return 'hr'
    # Handle OCR variations
    if re.search(r'\bhose\s*reel\b', t_cleaned):
        return 'hr'
    # Partial match (only if not part of "fire extinguisher")
    if 'hosereel' in t_cleaned and 'fire extinguisher' not in t_cleaned:
        return 'hr'

    # === STEP 4: Check for FIRE EXTINGUISHER ===
    if re.search(r'\bfire\s*extinguisher\b', t_cleaned):
        return 'fe'
    # Partial match (only if not part of "hosereel" or pumps)
    if 'fire extinguisher' in t_cleaned and 'hosereel' not in t_cleaned and 'transfer pump' not in t_cleaned and 'booster pump' not in t_cleaned:
        return 'fe'

    # === STEP 5: Check for ABBREVIATIONS (fallback) ===
    # Use word boundaries to avoid matching substrings like 'tp' in 'step'
    # Check for TP first (highest priority abbreviation)
    if re.search(r'\btp\b', t_cleaned):
        # Make sure it's not actually BP that was misread
        if not re.search(r'\bbp\b', t_cleaned) and not re.search(r'\bbooster\b', t_cleaned):
            return 'tp'
    
    # Check for BP
    if re.search(r'\bbp\b', t_cleaned):
        return 'bp'
    
    # Check for HR (hosereel)
    if re.search(r'\bhr\b', t_cleaned):
        return 'hr'
    
    # Check for FE (fire extinguisher)
    if re.search(r'\bfe\b', t_cleaned):
        return 'fe'
    
    # Check for RHE (rare)
    if re.search(r'\brhe\b', t_cleaned):
        return 'rhe'
    
    # Check for PT (pressure test)
    if re.search(r'\bpt\b', t_cleaned):
        return 'pt'

    # === DEFAULT ===
    return 'other'

# Test cases from the log
test_cases = [
    # Transfer Pump cases that should be detected
    ("TP 55 3555 Sat 10.25 11/10/2025 Fern Grove @ Yishun; 6 Yishun Avenue 4,76367 P1 HRM SPOIL", "tp"),
    ("PUMP No.2 START RUN LIGHT TRIP LIGHT", "tp"),
    ("Puypno 2 Start Ruy JRIP FLiGhi", "tp"),  # OCR error case
    ("NSGlNos TP 5> Thurs 09.45 09/10/2025 502C Yishun St 51 P1&P2 Run Light. spoil]", "tp"),
    ("Noit Njs TP Thurs 11:15 09/10/2025 506C Yishun Ave 4 P1 Run Light. spoil", "tp"),
    ("Fri 14.22 03/10/2025 229 Yishun Street 21, 760229 P1 HRM SPOIL and P2r light and L2 light spoil|", "tp"),
    ("TP 55 3555 Sat 10.25 11/10/2025 Blk 672C, Yishun 763672 P2 run light spoil Ring;", "tp"),
    ("Wed_ 13.49 91/10/2025 Flexstyle LLP?11SC Yish Road, #10-809,76 LiGHT HOUR ART incoming light LI,2,38 control switch light SP Ring", "tp"),
    
    # Booster Pump cases
    ("BP Tues 09-58  21/10/2025 WorkContent:P1 P2 Ru light,HRM Spoil. 424C Yishun Ave 11", "bp"),
    ("BP Fri 10-19 17/1042025 Work Content:P1 P2 Ru light Spoil; 382A Yishun Street 31", "bp"),
    ("Wed 15.06 22/10/2025 Work Content P2 press gaugemissing: Casa Spring @ Yishun; Yishun Avenue 6,7624", "bp"),
    ("BP 53 Fri 13.34 24/10/2025 Work Content P1 Spoil: Valley Spring @ Yishun Yishun Street 42,7634", "bp"),
    
    # Hosereel cases
    ("Hosereel pump 555 3535557,7,,7>,88873>>>>>5> Sat 10.58 04 Oct 2025 269A Yishun Street 22, 761269 PT1 & PT2 SPOIL", "hr"),
    ("Hosereel pump 55,,,,,,6,5,,,,,,,,7666565>, Tues 14.57 8ue1072025 315 Yishun Avenue 9 760315 Am timer sko spoil", "hr"),
    
    # Other cases (should remain 'other')
    ("Tues 15.29 21/104/2025 siatic WorkContent:P1 P2 HF Spoil, Vista Spring,431B Yish Avenue 1,762431", "other"),
    ("Thurs 1406 23/10/2025 WorkContent P1 press gauge Spoil; Forest Spring @ Yishun 473B Yishun Street 42, 762473", "other"),
]

print("Testing Equipment Detection\n" + "="*60)
passed = 0
failed = 0

for text, expected in test_cases:
    result = extract_equipment_type(text)
    status = "✅ PASS" if result == expected else "❌ FAIL"
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"\n{status}")
    print(f"Text: {text[:80]}...")
    print(f"Expected: {expected}, Got: {result}")

print("\n" + "="*60)
print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
