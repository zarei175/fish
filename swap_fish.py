#!/usr/bin/env python3
"""
swap_fish.py - Swap name and personnel ID between two payslip PDFs.

Handles Identity-H encoded fonts with glyph IDs (B Nazanin / Tahoma).
Preserves original fonts, layout, and formatting exactly.

Requirements: pip install pypdf
Usage: python swap_fish.py "10444483 (1).pdf" "67274571.pdf"
"""
import sys, re
from pypdf import PdfReader, PdfWriter

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def parse_cmap(font):
    if '/ToUnicode' not in font:
        return {}
    tu = font['/ToUnicode']
    if hasattr(tu, 'get_object'): tu = tu.get_object()
    if not hasattr(tu, 'get_data'): return {}
    text = tu.get_data().decode('latin-1', errors='replace')
    m = {}
    for match in re.finditer(r'<([0-9A-Fa-f]{2,8})>\s+<([0-9A-Fa-f]{2,8})>', text):
        gid, uc = int(match.group(1), 16), int(match.group(2), 16)
        if gid != 0xFFFF: m[gid] = uc
    return m


def get_fonts(page):
    fonts = {}
    try:
        res = page['/Resources']
        if hasattr(res, 'get_object'): res = res.get_object()
        fd = res['/Font']
        if hasattr(fd, 'get_object'): fd = fd.get_object()
        for name, ref in fd.items():
            f = ref.get_object() if hasattr(ref, 'get_object') else ref
            g2u = parse_cmap(f)
            fonts[name] = {
                'g2u': g2u, 'u2g': {v:k for k,v in g2u.items()},
                'base': str(f.get('/BaseFont','')), 'enc': str(f.get('/Encoding',''))
            }
    except: pass
    return fonts


def hex_decode(h, g2u):
    t = []
    for i in range(0, len(h)-3, 4):
        gid = int(h[i:i+4], 16)
        t.append(chr(g2u.get(gid, gid)))
    return ''.join(t)


def hex_encode(text, u2g):
    return ''.join(f'{u2g[ord(c)]:04X}' for c in text)


def extract_digits(text):
    return ''.join(c for c in text if c.isdigit())


def find_text_items(stream, fonts):
    fsw = [(m.start(), '/'+m.group(1)) for m in re.finditer(r'/(\w+)\s+[\d.]+\s+Tf', stream)]
    tjs = list(re.finditer(r'<([0-9A-Fa-f]+)>\s+Tj', stream))
    items = []
    for tj in tjs:
        h = tj.group(1)
        af = None
        for pos, fn in fsw:
            if pos < tj.start(): af = fn
        if af and af in fonts and fonts[af]['g2u']:
            decoded = hex_decode(h, fonts[af]['g2u'])
            items.append({'font': af, 'hex': h, 'text': decoded, 'match': tj})
    return items


def find_id_item(items):
    """Find the Tj item containing the personnel ID."""
    for item in items:
        text = item['text'].strip()
        digits = extract_digits(text)
        # Personnel ID: 7-10 digit number, no comma formatting
        if text.isdigit() and 7 <= len(text) <= 10:
            return {'id': text, 'item': item}
        # Also check if digits without separators form an 8-digit ID
        if len(digits) == 8 and digits == text.replace(' ', ''):
            return {'id': digits, 'item': item}
    return None


def find_name_items(items, fonts):
    """Find bold Arabic text items (potential names)."""
    result = []
    for item in items:
        finfo = fonts.get(item['font'], {})
        is_bold = 'Bold' in finfo.get('base', '') or 'bold' in finfo.get('base', '').lower()
        has_arabic = any(ord(c) > 0x0600 for c in item['text'])
        if is_bold and has_arabic and len(item['text'].strip()) >= 4:
            result.append(item)
    return result


def process_pdf(in_path, out_path, old_id, new_id, name_replacements):
    """Replace ID and name in a PDF file."""
    print(f"\n  Processing: {in_path}")
    
    reader = PdfReader(in_path)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    
    page = writer.pages[0]
    fonts = get_fonts(page)
    
    contents = page['/Contents']
    if hasattr(contents, 'get_object'): contents = contents.get_object()
    if not hasattr(contents, 'get_data'):
        print("  ERROR: Can't access content stream")
        return
    
    stream = contents.get_data().decode('latin-1')
    modified = stream
    
    items = find_text_items(stream, fonts)
    id_done = False
    name_done = False
    
    for item in items:
        g2u = fonts[item['font']]['g2u']
        u2g = fonts[item['font']]['u2g']
        decoded = item['text']
        hex_str = item['hex']
        
        # Replace personnel ID
        if not id_done:
            digits = extract_digits(decoded)
            if old_id in digits or decoded.strip() == old_id:
                # Find digit positions and replace
                idx = 0
                positions = []
                for i, ch in enumerate(decoded):
                    if ch.isdigit() and idx < len(old_id) and ch == old_id[idx]:
                        positions.append(i)
                        idx += 1
                
                if idx == len(old_id):
                    chars = list(decoded)
                    for pi, ci in enumerate(positions):
                        chars[ci] = new_id[pi]
                    new_decoded = ''.join(chars)
                    try:
                        new_hex = hex_encode(new_decoded, u2g)
                        for cf in [lambda x:x, str.upper, str.lower]:
                            old_p = f'<{cf(hex_str)}>'
                            if old_p in modified:
                                modified = modified.replace(old_p, f'<{cf(new_hex)}>', 1)
                                id_done = True
                                print(f"    ID: {old_id} -> {new_id}")
                                break
                    except KeyError as e:
                        print(f"    ID warning: {e}")
        
        # Replace name
        if not name_done and item['font'] in name_replacements:
            old_nh, new_nh = name_replacements[item['font']]
            if hex_str.upper() == old_nh.upper():
                for cf in [lambda x:x, str.upper, str.lower]:
                    old_p = f'<{cf(hex_str)}>'
                    if old_p in modified:
                        modified = modified.replace(old_p, f'<{cf(new_nh)}>', 1)
                        name_done = True
                        print(f"    Name replaced")
                        break
    
    if not id_done:
        print(f"    WARNING: Personnel ID not replaced")
    if not name_done:
        print(f"    WARNING: Name not replaced (font may lack required glyphs)")
    
    contents.set_data(modified.encode('latin-1'))
    with open(out_path, 'wb') as f:
        writer.write(f)
    print(f"    Saved: {out_path}")


def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <fish1.pdf> <fish2.pdf>")
        sys.exit(1)
    
    path1, path2 = sys.argv[1], sys.argv[2]
    
    print("=" * 60)
    print("Payslip Swap Tool")
    print("=" * 60)
    
    # Read and analyze both PDFs
    r1, r2 = PdfReader(path1), PdfReader(path2)
    p1, p2 = r1.pages[0], r2.pages[0]
    f1, f2 = get_fonts(p1), get_fonts(p2)
    
    c1 = p1['/Contents']
    if hasattr(c1, 'get_object'): c1 = c1.get_object()
    s1 = c1.get_data().decode('latin-1')
    
    c2 = p2['/Contents']
    if hasattr(c2, 'get_object'): c2 = c2.get_object()
    s2 = c2.get_data().decode('latin-1')
    
    items1 = find_text_items(s1, f1)
    items2 = find_text_items(s2, f2)
    
    # Find IDs
    id1 = find_id_item(items1)
    id2 = find_id_item(items2)
    
    if not id1 or not id2:
        print("\nERROR: Could not detect personnel IDs!")
        print("Decoded text items:")
        for items, label in [(items1, "PDF1"), (items2, "PDF2")]:
            print(f"  {label}:")
            for item in items:
                d = extract_digits(item['text'])
                if d:
                    print(f"    '{item['text'].strip()}' digits='{d}' font={item['font']}")
        sys.exit(1)
    
    print(f"\n  PDF1 ID: {id1['id']}")
    print(f"  PDF2 ID: {id2['id']}")
    
    # Find names
    names1 = find_name_items(items1, f1)
    names2 = find_name_items(items2, f2)
    
    print(f"\n  PDF1 bold Arabic text:")
    for n in names1:
        print(f"    [{n['font']}] '{n['text']}'")
    print(f"  PDF2 bold Arabic text:")
    for n in names2:
        print(f"    [{n['font']}] '{n['text']}'")
    
    # Try cross-encoding names
    name_1to2 = {}  # Replacements for PDF1 (put PDF2's name)
    name_2to1 = {}  # Replacements for PDF2 (put PDF1's name)
    
    for n1 in names1:
        for n2 in names2:
            if n1['font'] != n2['font']:
                continue  # Only match same font slots
            u2g1 = f1[n1['font']]['u2g']
            u2g2 = f2[n2['font']]['u2g']
            
            # Try: can we write n2's text using PDF1's font?
            try:
                new_hex = hex_encode(n2['text'], u2g1)
                if n1['font'] not in name_1to2:
                    name_1to2[n1['font']] = (n1['hex'], new_hex)
                    print(f"\n  Name swap PDF1 OK: '{n1['text']}' -> '{n2['text']}'")
            except KeyError as e:
                print(f"\n  Name swap PDF1 FAIL: missing glyph {e}")
                # Try to find which glyphs are missing
                missing = []
                for ch in n2['text']:
                    if ord(ch) not in u2g1:
                        missing.append(f"U+{ord(ch):04X} ({ch})")
                if missing:
                    print(f"    Missing in PDF1 font: {', '.join(missing)}")
            
            # Try: can we write n1's text using PDF2's font?
            try:
                new_hex = hex_encode(n1['text'], u2g2)
                if n2['font'] not in name_2to1:
                    name_2to1[n2['font']] = (n2['hex'], new_hex)
                    print(f"  Name swap PDF2 OK: '{n2['text']}' -> '{n1['text']}'")
            except KeyError as e:
                print(f"  Name swap PDF2 FAIL: missing glyph {e}")
                missing = []
                for ch in n1['text']:
                    if ord(ch) not in u2g2:
                        missing.append(f"U+{ord(ch):04X} ({ch})")
                if missing:
                    print(f"    Missing in PDF2 font: {', '.join(missing)}")
    
    # Do the swap
    out1 = path1.replace('.pdf', '_swapped.pdf').replace(' ', '_')
    out2 = path2.replace('.pdf', '_swapped.pdf').replace(' ', '_')
    
    process_pdf(path1, out1, id1['id'], id2['id'], name_1to2)
    process_pdf(path2, out2, id2['id'], id1['id'], name_2to1)
    
    print(f"\n{'='*60}")
    print(f"DONE!")
    print(f"  {out1}")
    print(f"  {out2}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
