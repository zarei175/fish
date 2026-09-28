#!/usr/bin/env python3
"""
Deep diagnostic: dumps raw content streams and text operators from PDF.
Run: python diagnose_deep.py "10444483 (1).pdf" > diag_output.txt
Then share diag_output.txt
"""
import sys
import re

def diagnose(pdf_path):
    print(f"\n{'='*70}")
    print(f"Deep analysis of: {pdf_path}")
    print(f"{'='*70}")
    
    # Step 1: Raw byte search for ASCII personnel IDs
    with open(pdf_path, 'rb') as f:
        raw = f.read()
    
    print(f"\nFile size: {len(raw)} bytes")
    
    # Search for personnel ID as ASCII in raw bytes
    for pid in [b'10444483', b'67274571']:
        pos = raw.find(pid)
        if pos >= 0:
            print(f"\nFound ASCII '{pid.decode()}' at byte {pos}")
            print(f"  Context: {raw[max(0,pos-50):pos+len(pid)+50]}")
        else:
            print(f"\nASCII '{pid.decode()}' NOT found in raw bytes")
    
    # Search UTF-16BE for IDs
    for pid in ['10444483', '67274571']:
        enc = pid.encode('utf-16-be')
        pos = raw.find(enc)
        if pos >= 0:
            print(f"\nFound UTF-16BE '{pid}' at byte {pos}")
            print(f"  Hex context: {raw[max(0,pos-20):pos+len(enc)+20].hex()}")
        else:
            print(f"UTF-16BE '{pid}' NOT found")
    
    # Step 2: Find all stream objects and decode them
    # Look for stream...endstream blocks
    stream_pattern = rb'stream\r?\n(.+?)\r?\nendstream'
    
    # Use pypdf for proper stream decoding
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    
    for page_num, page in enumerate(reader.pages):
        print(f"\n{'='*50}")
        print(f"PAGE {page_num}")
        print(f"{'='*50}")
        
        # Get fonts info
        if '/Resources' in page:
            res = page['/Resources']
            if hasattr(res, 'get_object'):
                res = res.get_object()
            if '/Font' in res:
                fonts = res['/Font']
                if hasattr(fonts, 'get_object'):
                    fonts = fonts.get_object()
                for fname, fref in fonts.items():
                    font = fref.get_object() if hasattr(fref, 'get_object') else fref
                    bf = font.get('/BaseFont', '?')
                    enc = font.get('/Encoding', '?')
                    st = font.get('/Subtype', '?')
                    print(f"\n  Font {fname}: BaseFont={bf}, Encoding={enc}, Subtype={st}")
                    
                    # Dump ToUnicode CMap
                    if '/ToUnicode' in font:
                        tu = font['/ToUnicode']
                        if hasattr(tu, 'get_object'):
                            tu = tu.get_object()
                        if hasattr(tu, 'get_data'):
                            cmap = tu.get_data()
                            print(f"    ToUnicode CMap ({len(cmap)} bytes):")
                            try:
                                print(f"    {cmap.decode('latin-1')}")
                            except:
                                print(f"    (hex): {cmap[:500].hex()}")
        
        # Get decoded content stream
        if '/Contents' in page:
            contents = page['/Contents']
            if hasattr(contents, 'get_object'):
                contents = contents.get_object()
            
            streams = []
            if hasattr(contents, '__iter__') and not hasattr(contents, 'get_data'):
                for c in contents:
                    obj = c.get_object() if hasattr(c, 'get_object') else c
                    if hasattr(obj, 'get_data'):
                        streams.append(obj.get_data())
            elif hasattr(contents, 'get_data'):
                streams.append(contents.get_data())
            
            for si, stream_data in enumerate(streams):
                print(f"\n  --- Content Stream {si} ({len(stream_data)} bytes) ---")
                
                # Show full decoded stream
                try:
                    text = stream_data.decode('latin-1')
                except:
                    text = stream_data.hex()
                
                # Find all text operators: Tj, TJ, ', "
                # TJ looks like: [(bytes) num (bytes) num ...] TJ
                # Tj looks like: (bytes) Tj or <hex> Tj
                lines = text.split('\n')
                for li, line in enumerate(lines):
                    line = line.strip()
                    if any(op in line for op in ['Tj', 'TJ', "'", '"', 'Tf']):
                        print(f"    L{li}: {line[:200]}")
                
                # Also dump hex of the full stream for thorough analysis
                print(f"\n  Full stream hex (first 3000 bytes):")
                print(f"  {stream_data[:3000].hex()}")
                print(f"\n  Full stream text (first 3000 chars):")
                print(f"  {text[:3000]}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <pdf_file>")
        sys.exit(1)
    diagnose(sys.argv[1])
