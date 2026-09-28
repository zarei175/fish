#!/usr/bin/env python3
"""
Swap name and personnel ID between two payslip PDFs.
Modifies the raw PDF bytes directly to preserve original fonts, layout, and formatting.

Requirements:
    pip install pypdf

Usage:
    python swap_fish.py "10444483 (1).pdf" "67274571.pdf"

Output:
    10444483_(1)_swapped.pdf
    67274571_swapped.pdf
"""

import sys

# === CONFIG: Edit these values for your payslips ===
FISH1_NAME_VARIANTS = [
    "\u0633\u06cc\u062f\u0639\u0628\u0627\u0633 \u0645\u062d\u0633\u0646\u06cc \u06a9\u06cc\u0627",
    "\ufeb3\ufef4\ufea0\ufecb\ufea8\ufeb7 \ufee3\ufea4\ufeb4\ufee8\ufef2 \ufedb\ufef4\ufeb5",
]
FISH1_ID = "10444483"

FISH2_NAME_VARIANTS = [
    "\u0646\u0627\u062c\u06cc \u0646\u0635\u0627\u0631\u06cc \u067e\u0648\u0632\u0647",
    "\ufee7\ufeb7\ufe9e\ufef2 \ufee7\ufea0\ufeb7\ufe8d\ufead\ufef2 \u067e\ufeed\ufeaf\ufeeb",
]
FISH2_ID = "67274571"
# === END CONFIG ===


def swap_in_pdf(input_path, replacements, output_path):
    """Replace text directly in PDF bytes to preserve fonts and layout."""
    with open(input_path, 'rb') as f:
        pdf_bytes = f.read()

    modified = pdf_bytes
    found_any = False

    for old_text, new_text in replacements:
        for encoding in ['utf-8', 'utf-16-be', 'utf-16-le', 'latin-1']:
            try:
                old_enc = old_text.encode(encoding)
                new_enc = new_text.encode(encoding)
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if old_enc in modified:
                modified = modified.replace(old_enc, new_enc)
                print(f"  [{encoding}] Replaced: {repr(old_text)} -> {repr(new_text)}")
                found_any = True
                break

    if found_any:
        with open(output_path, 'wb') as f:
            f.write(modified)
        print(f"  Saved: {output_path}")
    else:
        print(f"  WARNING: Could not find matching text in {input_path}")
        print(f"  The PDF may use glyph IDs instead of Unicode text.")
        print(f"  Try opening the PDF in a text editor to inspect the encoding.")


def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <fish1.pdf> <fish2.pdf>")
        print(f"Example: python {sys.argv[0]} '10444483 (1).pdf' '67274571.pdf'")
        sys.exit(1)

    fish1_path = sys.argv[1]
    fish2_path = sys.argv[2]

    fish1_out = fish1_path.replace('.pdf', '_swapped.pdf').replace(' ', '_')
    fish2_out = fish2_path.replace('.pdf', '_swapped.pdf').replace(' ', '_')

    # Fish 1: replace person1's info with person2's
    print(f"\n=== Processing {fish1_path} ===")
    r1 = []
    for v1 in FISH1_NAME_VARIANTS:
        for v2 in FISH2_NAME_VARIANTS:
            r1.append((v1, v2))
    r1.append((FISH1_ID, FISH2_ID))
    swap_in_pdf(fish1_path, r1, fish1_out)

    # Fish 2: replace person2's info with person1's
    print(f"\n=== Processing {fish2_path} ===")
    r2 = []
    for v2 in FISH2_NAME_VARIANTS:
        for v1 in FISH1_NAME_VARIANTS:
            r2.append((v2, v1))
    r2.append((FISH2_ID, FISH1_ID))
    swap_in_pdf(fish2_path, r2, fish2_out)

    print(f"\nDone!")
    print(f"  {fish1_out}")
    print(f"  {fish2_out}")


if __name__ == '__main__':
    main()
