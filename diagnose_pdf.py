#!/usr/bin/env python3
"""
Diagnostic script: analyzes PDF encoding to find how text is stored internally.
Run: python diagnose_pdf.py "10444483 (1).pdf"
"""
import sys
from pypdf import PdfReader

def diagnose(pdf_path):
    print(f"\n{'='*60}")
    print(f"Analyzing: {pdf_path}")
    print(f"{'='*60}")
    
    # 1. Read raw bytes and search for known strings
    with open(pdf_path, 'rb') as f:
        raw = f.read()
    
    # Search for personnel ID in raw bytes (ASCII digits should be findable)
    test_strings = ["10444483", "67274571"]
    for s in test_strings:
        for enc in ['ascii', 'utf-8', 'utf-16-be', 'utf-16-le']:
            encoded = s.encode(enc)
            positions = []
            start = 0
            while True:
                pos = raw.find(encoded, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            if positions:
                print(f"\n  Found '{s}' [{enc}] at byte positions: {positions}")
                for p in positions[:3]:
                    context = raw[max(0,p-30):p+len(encoded)+30]
                    print(f"    Context around {p}: {context}")
    
    # 2. Analyze with pypdf
    reader = PdfReader(pdf_path)
    print(f"\n  Pages: {len(reader.pages)}")
    
    for page_num, page in enumerate(reader.pages):
        print(f"\n  --- Page {page_num} ---")
        
        # Extract text
        text = page.extract_text()
        if text:
            # Show first 500 chars
            print(f"  Extracted text (first 500 chars):")
            print(f"  {text[:500]}")
        
        # Look at content stream
        if '/Contents' in page:
            contents = page['/Contents']
            if hasattr(contents, 'get_object'):
                contents = contents.get_object()
            
            # Handle array of streams
            if hasattr(contents, '__iter__') and not hasattr(contents, 'get_data'):
                streams = [c.get_object() for c in contents]
            else:
                streams = [contents]
            
            for i, stream in enumerate(streams):
                if hasattr(stream, 'get_data'):
                    data = stream.get_data()
                    print(f"\n  Content stream {i}: {len(data)} bytes")
                    # Show first 2000 bytes as string (lossy)
                    try:
                        text_repr = data[:2000].decode('latin-1')
                        print(f"  First 2000 bytes (latin-1):")
                        print(f"  {text_repr}")
                    except:
                        print(f"  First 200 bytes (hex): {data[:200].hex()}")
        
        # Check fonts
        if '/Resources' in page:
            resources = page['/Resources']
            if hasattr(resources, 'get_object'):
                resources = resources.get_object()
            if '/Font' in resources:
                fonts = resources['/Font']
                if hasattr(fonts, 'get_object'):
                    fonts = fonts.get_object()
                print(f"\n  Fonts used on page {page_num}:")
                for font_name, font_ref in fonts.items():
                    font = font_ref.get_object() if hasattr(font_ref, 'get_object') else font_ref
                    base_font = font.get('/BaseFont', 'unknown')
                    encoding = font.get('/Encoding', 'unknown')
                    subtype = font.get('/Subtype', 'unknown')
                    print(f"    {font_name}: BaseFont={base_font}, Encoding={encoding}, Subtype={subtype}")
                    
                    # Check ToUnicode
                    if '/ToUnicode' in font:
                        tounicode = font['/ToUnicode']
                        if hasattr(tounicode, 'get_object'):
                            tounicode = tounicode.get_object()
                        if hasattr(tounicode, 'get_data'):
                            cmap_data = tounicode.get_data().decode('latin-1', errors='replace')
                            print(f"      ToUnicode CMap (first 500 chars): {cmap_data[:500]}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <pdf_file>")
        sys.exit(1)
    diagnose(sys.argv[1])
