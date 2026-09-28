#!/usr/bin/env python3
"""
Swap name and personnel ID between two payslip PDFs.
Handles Arabic Presentation Forms-B (U+FE70-U+FEFF) used in these PDFs.

Requirements:
    pip install pypdf

Usage:
    python swap_fish.py "10444483 (1).pdf" "67274571.pdf"
"""

import sys

# === Names in Arabic Presentation Forms-B (as stored in the PDF) ===
# Fish 1: سیدعباس محسنی کیا
FISH1_NAME_PRES = "\ufeb3\ufef4\ufeaa\ufecb\ufe92\ufe8e\ufeb1 \ufee3\ufea4\ufeb4\ufee8\ufef2 \ufedb\ufef4\ufe8e"
# Fish 1: standard Arabic
FISH1_NAME_STD = "\u0633\u064a\u062f\u0639\u0628\u0627\u0633 \u0645\u062d\u0633\u0646\u06cc \u06a9\u064a\u0627"

# Fish 2: ناجی نصاری پوزه
FISH2_NAME_PRES = "\ufee7\ufe8e\ufe9f\ufef2 \ufee7\ufebc\ufe8e\ufead\ufef1 \u067e\ufeee\ufeaf\ufee9"
# Fish 2: standard Arabic
FISH2_NAME_STD = "\u0646\u0627\u062c\u06cc \u0646\u0635\u0627\u0631\u06cc \u067e\u0648\u0632\u0647"

FISH1_ID = "10444483"
FISH2_ID = "67274571"


def find_and_replace(pdf_bytes, old_text, new_text):
    """Try multiple encodings to find and replace text in PDF bytes."""
    modified = pdf_bytes
    found = False
    
    for encoding in ['utf-16-be', 'utf-8', 'utf-16-le', 'latin-1']:
        try:
            old_enc = old_text.encode(encoding)
            new_enc = new_text.encode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        
        if old_enc in modified:
            # For different-length replacements, pad with spaces in same encoding
            if len(new_enc) < len(old_enc):
                space = ' '.encode(encoding)
                while len(new_enc) < len(old_enc):
                    new_enc += space
            modified = modified.replace(old_enc, new_enc[:len(old_enc)] if len(new_enc) > len(old_enc) else new_enc)
            print(f"  [{encoding}] Replaced: {repr(old_text)[:50]} -> {repr(new_text)[:50]}")
            found = True
            break
    
    return modified, found


def swap_in_pdf(input_path, name_replacements, id_old, id_new, output_path):
    """Replace text in PDF preserving original format and fonts."""
    with open(input_path, 'rb') as f:
        pdf_bytes = f.read()
    
    modified = pdf_bytes
    found_name = False
    found_id = False
    
    # Try each name variant pair
    for old_name, new_name in name_replacements:
        modified, found = find_and_replace(modified, old_name, new_name)
        if found:
            found_name = True
            break
    
    # Replace personnel ID
    modified, found_id = find_and_replace(modified, id_old, id_new)
    
    if found_name or found_id:
        with open(output_path, 'wb') as f:
            f.write(modified)
        print(f"  Saved: {output_path}")
        if not found_name:
            print(f"  WARNING: Name not found/replaced")
        if not found_id:
            print(f"  WARNING: ID not found/replaced")
    else:
        print(f"  ERROR: Nothing was replaced in {input_path}")


def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <fish1.pdf> <fish2.pdf>")
        sys.exit(1)
    
    fish1_path = sys.argv[1]
    fish2_path = sys.argv[2]
    
    fish1_out = fish1_path.replace('.pdf', '_swapped.pdf').replace(' ', '_')
    fish2_out = fish2_path.replace('.pdf', '_swapped.pdf').replace(' ', '_')
    
    # Fish 1: replace person1 -> person2
    print(f"\n=== Processing {fish1_path} ===")
    name_pairs_1 = [
        (FISH1_NAME_PRES, FISH2_NAME_PRES),
        (FISH1_NAME_STD, FISH2_NAME_STD),
    ]
    swap_in_pdf(fish1_path, name_pairs_1, FISH1_ID, FISH2_ID, fish1_out)
    
    # Fish 2: replace person2 -> person1
    print(f"\n=== Processing {fish2_path} ===")
    name_pairs_2 = [
        (FISH2_NAME_PRES, FISH1_NAME_PRES),
        (FISH2_NAME_STD, FISH1_NAME_STD),
    ]
    swap_in_pdf(fish2_path, name_pairs_2, FISH2_ID, FISH1_ID, fish2_out)
    
    print(f"\nDone!")
    print(f"  {fish1_out}")
    print(f"  {fish2_out}")


if __name__ == '__main__':
    main()
