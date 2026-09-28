#!/usr/bin/env python3
"""
Deep diagnostic: dumps raw content streams and text operators from PDF.
Run: python diagnose_deep.py "10444483 (1).pdf"
"""
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def diagnose(pdf_path):
    out_path = pdf_path.replace('.pdf', '_diag.txt').replace(' ', '_')
    f_out = open(out_path, 'w', encoding='utf-8', errors='replace')
    
    def p(s=''):
        print(s)
        f_out.write(s + '\n')
    
    p(f"{'='*70}")
    p(f"Deep analysis of: {pdf_path}")
    p(f"{'='*70}")
    
    with open(pdf_path, 'rb') as f:
        raw = f.read()
    
    p(f"File size: {len(raw)} bytes")
    
    # Search for personnel ID as ASCII
    for pid in [b'10444483', b'67274571']:
        pos = raw.find(pid)
        if pos >= 0:
            p(f"\nFound ASCII '{pid.decode()}' at byte {pos}")
            ctx = raw[max(0,pos-50):pos+len(pid)+50]
            p(f"  Context hex: {ctx.hex()}")
        else:
            p(f"\nASCII '{pid.decode()}' NOT found in raw bytes")
    
    # Search UTF-16BE for IDs
    for pid in ['10444483', '67274571']:
        enc = pid.encode('utf-16-be')
        pos = raw.find(enc)
        if pos >= 0:
            p(f"Found UTF-16BE '{pid}' at byte {pos}")
            p(f"  Hex: {raw[max(0,pos-20):pos+len(enc)+20].hex()}")
        else:
            p(f"UTF-16BE '{pid}' NOT found")
    
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    
    for page_num, page in enumerate(reader.pages):
        p(f"\n{'='*50}")
        p(f"PAGE {page_num}")
        p(f"{'='*50}")
        
        # Fonts
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
                    enc_f = font.get('/Encoding', '?')
                    st = font.get('/Subtype', '?')
                    p(f"\n  Font {fname}: BaseFont={bf}, Encoding={enc_f}, Subtype={st}")
                    
                    if '/ToUnicode' in font:
                        tu = font['/ToUnicode']
                        if hasattr(tu, 'get_object'):
                            tu = tu.get_object()
                        if hasattr(tu, 'get_data'):
                            cmap = tu.get_data()
                            p(f"    ToUnicode CMap ({len(cmap)} bytes):")
                            p(f"    {cmap.hex()[:2000]}")
        
        # Content streams
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
                p(f"\n  --- Content Stream {si} ({len(stream_data)} bytes) ---")
                p(f"  Full stream hex (first 5000):")
                p(f"  {stream_data[:5000].hex()}")
                p(f"\n  Full stream hex (all):")
                p(f"  {stream_data.hex()}")
    
    f_out.close()
    p(f"\nDiagnostic saved to: {out_path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <pdf_file>")
        sys.exit(1)
    diagnose(sys.argv[1])
