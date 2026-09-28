#!/usr/bin/env python3
"""
Swap personnel ID and full name between the two payslips.
The name is moved using the embedded original B Nazanin font from the other PDF,
so subset-glyph differences do not cause a false replacement.

Usage:
    pip install pypdf
    python swap_fish.py "10444483 (1).pdf" "67274571.pdf"
"""
import sys, re
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# These are the exact logical strings produced by pypdf for the embedded PDFs.
NAME1 = "ﺎﻴﻛ ﻲﻨﺴﺤﻣ ﺱﺎﺒﻋﺪﻴﺳ"
NAME2 = "ﻪﺯﻮﭘ ﻱﺭﺎﺼﻧ ﻲﺟﺎﻧ"


def cmap(font):
    if '/ToUnicode' not in font: return {}
    x = font['/ToUnicode']
    if hasattr(x, 'get_object'): x = x.get_object()
    if not hasattr(x, 'get_data'): return {}
    s = x.get_data().decode('latin-1', errors='replace')
    out = {}
    for m in re.finditer(r'<([0-9A-Fa-f]{2,8})>\s+<([0-9A-Fa-f]{2,8})>', s):
        a,b = int(m.group(1),16), int(m.group(2),16)
        if a != 0xFFFF: out[a] = b
    return out


def fonts(page):
    r = page['/Resources']
    if hasattr(r,'get_object'): r=r.get_object()
    d = r['/Font']
    if hasattr(d,'get_object'): d=d.get_object()
    out={}
    for n,ref in d.items():
        f=ref.get_object() if hasattr(ref,'get_object') else ref
        g=cmap(f)
        out[str(n)]={'obj':f,'g2u':g,'u2g':{v:k for k,v in g.items()}}
    return out


def stream_obj(page):
    x=page['/Contents']
    if hasattr(x,'get_object'): x=x.get_object()
    return x


def items(s, fs):
    switches=[(m.start(), '/'+m.group(1), m.group(2)) for m in re.finditer(r'/(\w+)\s+([\d.]+)\s+Tf',s)]
    out=[]
    for m in re.finditer(r'<([0-9A-Fa-f]+)>\s+Tj',s):
        active=None; size='9.57'
        for pos,n,z in switches:
            if pos < m.start(): active=n; size=z
        if active not in fs: continue
        g=fs[active]['g2u']; h=m.group(1)
        text=''.join(chr(g.get(int(h[i:i+4],16),int(h[i:i+4],16))) for i in range(0,len(h)-3,4))
        out.append((m,active,size,h,text))
    return out


def encode(text,u2g):
    return ''.join(f'{u2g[ord(c)]:04X}' for c in text)


def id_replace(s, fs, old, new):
    for m,fn,size,h,text in items(s,fs):
        if text.strip()!=old: continue
        u2g=fs[fn]['u2g']
        try: nh=encode(new,u2g)
        except KeyError: continue
        return s[:m.start(1)]+nh+s[m.end(1):], True
    return s,False


def add_font(writer, page, source_font, name='/Fswap'):
    # clone() recursively carries the embedded descendant/font-file objects.
    cloned=source_font.clone(writer, force_duplicate=True) if hasattr(source_font,'clone') else source_font
    ref=writer._add_object(cloned)
    r=page['/Resources']
    if hasattr(r,'get_object'): r=r.get_object()
    d=r['/Font']
    if hasattr(d,'get_object'): d=d.get_object()
    d[NameObject(name)]=ref
    return name


def process(dest_path, source_path, old_id, new_id, old_name, new_name, out_path):
    print(f'\nProcessing {dest_path}')
    dest=PdfReader(dest_path); src=PdfReader(source_path)
    writer=PdfWriter(); writer.append_pages_from_reader(dest)
    page=writer.pages[0]; source_page=src.pages[0]
    fs=fonts(page); s=stream_obj(page).get_data().decode('latin-1')
    # ID: exact decoded text match, never a heuristic match.
    s,idok=id_replace(s,fs,old_id,new_id)
    if idok: print(f'  ID replaced: {old_id} -> {new_id}')
    else: print('  ERROR: ID was not replaced')
    
    # Name: exact decoded logical string, then use source PDF's embedded font/glyphs.
    srcfs=fonts(source_page); srcs=stream_obj(source_page).get_data().decode('latin-1')
    src_item=next((x for x in items(srcs,srcfs) if x[4]==new_name),None)
    dst_item=next((x for x in items(s,fs) if x[4]==old_name),None)
    nameok=False
    if src_item and dst_item:
        dm,dfn,dsize,dh,dt=dst_item
        sm,sfn,ssize,sh,st=src_item
        # Add source's exact embedded font as a separate resource, then switch only for this Tj.
        swap_font=add_font(writer,page,srcfs[sfn]['obj'],'/Fswap')
        replacement=f'/Fswap {dsize} Tf <{sh}> Tj /{dfn} {dsize} Tf'
        s=s[:dm.start()]+replacement+s[dm.end():]
        nameok=True
        print(f'  Name replaced: exact match, source font {sfn} transplanted as /Fswap')
    else:
        print(f'  ERROR: exact name item not found (destination={bool(dst_item)}, source={bool(src_item)})')
    stream_obj(page).set_data(s.encode('latin-1'))
    with open(out_path,'wb') as f: writer.write(f)
    print(f'  Saved: {out_path}')
    return idok and nameok


def main():
    if len(sys.argv)!=3:
        print(f'Usage: python {sys.argv[0]} <fish1.pdf> <fish2.pdf>'); raise SystemExit(1)
    p1,p2=sys.argv[1],sys.argv[2]
    o1=p1.replace('.pdf','_swapped.pdf').replace(' ','_')
    o2=p2.replace('.pdf','_swapped.pdf').replace(' ','_')
    ok1=process(p1,p2,'10444483','67274571',NAME1,NAME2,o1)
    ok2=process(p2,p1,'67274571','10444483',NAME2,NAME1,o2)
    print('\nDONE' if ok1 and ok2 else '\nFAILED: no partial success claimed')

if __name__=='__main__': main()
