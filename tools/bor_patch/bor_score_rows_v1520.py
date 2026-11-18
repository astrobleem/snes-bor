"""Select active player names on mutable and source-hit score paths, sharing immutable rows."""
from bor_target_rows_v1519 import correct as base
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import Code,imm,far
TABLE=0x32a000
LOOK=0x2df800
CODE=0x2df900
MODELS=('Kula','Max','Mandy','Mighty')

def patterns():
    data=bytearray()
    for model in MODELS:
        for score in range(0,500,5):
            text=('    '+model+' - '+str(score)).ljust(16);assert len(text)==16
            for c in text:data.extend((0x2400|(920+ord(c)-32)).to_bytes(2,'little'))
    data.extend((0x2798).to_bytes(2,'little')*2)
    return bytes(data)

def programs():
    q=Code(CODE);table=bytearray()
    for player,actor in enumerate((0x7e0a0c,0x7e0a91)):
        k=str(player);delta=(4,0)[player]
        for i in range(4):table+=((TABLE+3200*i+delta)&65535).to_bytes(2,'little')
        look=LOOK+8*player
        def model(reject):
            q.put(far(0xaf,actor));q.put(imm(0x29,255));q.put('38');q.put(imm(0xe9,22));q.put(imm(0xc9,4));q.when(0xb0,reject);q.put('0aaa')
        q.lab('dirty'+k);q.put('08c230da5a8b')
        q.put(far(0xaf,0x7e2856));q.when(0xd0,'done'+k)
        q.put(far(0xaf,0x7e2854));q.put(imm(0xc9,500));q.when(0xb0,'done'+k)
        q.put('0aaa');q.put(far(0xbf,0x27aa00));q.when(0x30,'done'+k);q.put('4a48')
        model('skip'+k);q.put('6818');q.put(far(0x7f,look));q.put('aa');q.put(imm(0xa0,0x2700));q.put(imm(0xa9,31));q.put('547e32');q.go('done'+k)
        q.lab('skip'+k);q.put('68')
        q.lab('done'+k);q.put('ab7afa28');q.put(imm(0xa9,(0xd000,0xd020)[player]));q.put(far(0x8f,0x7e0473));q.put(far(0x5c,(0x33e441,0x33e467)[player]))
        q.lab('hit'+k);q.put('08c230da48');model('stock'+k)
        q.put('684a18');q.put(far(0x7f,look));q.put('48e220a932');q.go('bank'+k)
        q.lab('stock'+k);q.put('6818');q.put(imm(0x69,(0xb000,0xc900)[player]));q.put('48e220a927')
        q.lab('bank'+k);q.put(far(0x8f,0x7e0472));q.put('c22068fa286b')
    return q.done(),q.labels,bytes(table)

def correct(image,symbols):
    r=bytearray(base(image,symbols));b,lab,table=programs()
    for a,blob in ((TABLE,patterns()),(LOOK,table),(CODE,b)):
        i=offset(a);assert not any(r[i:i+len(blob)]) and not any(a<=v<a+len(blob) for t in symbols for v in t.values() if type(v)is int),hex(a)
        r[i:i+len(blob)]=blob
    def patch(a,b,n):
        i=offset(a);assert len(n)<=len(b) and r[i:i+len(b)]==b,(hex(a),r[i:i+len(b)].hex());r[i:i+len(b)]=n+b'\xea'*(len(b)-len(n))
    for player in (0,1):
        a=(0x33e43a,0x33e460)[player];old=(0xd000,0xd020)[player]
        patch(a,imm(0xa9,old)+far(0x8f,0x7e0473),far(0x5c,lab['dirty'+str(player)]))
        seq=b'\x48\x18'+imm(0x69,(0xb000,0xc900)[player])+far(0x8f,0x7e0470)
        i=r.find(seq,offset(0x27a900),offset(0x27a9c0));assert i>=0
        patch(0x278000+(i%32768)+1,seq[1:5],far(0x22,lab['hit'+str(player)]))
    seq=b'\xa9\x27'+far(0x8f,0x7e0472);i=r.find(seq,offset(0x27a900),offset(0x27a9c0));assert i>=0
    patch(0x278000+(i%32768),seq,bytes.fromhex('8004'))
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');crc=sum(r)&65535;r[0x7fdc:0x7fe0]=(65535-crc).to_bytes(2,'little')+crc.to_bytes(2,'little')
    return bytes(r)
