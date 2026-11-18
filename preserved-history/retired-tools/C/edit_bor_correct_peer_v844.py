from pathlib import Path
import sys
R=Path('E:/gh/snes-bor');p=R/'src/main.pasm';s=p.read_bytes();n=b'\r\n' if b'\r\n' in s else b'\n'
edits=[('    lda #16\n    bra SourceP1Jump_HaveSize','    lda #32\n    bra SourceP1Jump_HaveSize'),('SourceP1Jump_Size8:\n.a16\n.i16\n    lda #8','SourceP1Jump_Size8:\n.a16\n.i16\n    lda #16'),('    sbc.l $437BAE\n    and #511','    sbc.l $437BAE\n    inc a\n    and #511')]
restore='--restore' in sys.argv
for a,b in (reversed(edits) if restore else edits):
 a=a.encode().replace(b'\n',n);b=b.encode().replace(b'\n',n)
 if restore:a,b=b,a
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
p.write_bytes(s);print('Restored inherited peer transform' if restore else 'Corrected peer reflection for mode6 widths and inclusive catalog pixel coordinates')
