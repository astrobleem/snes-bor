"""Conservative 65816 A16/I16 statement-length audit for this emitted patch.

Not a Poppy assembler and cannot validate symbols/branch reach or the *whole*
bank. Used to flag unexpectedly large growth before Sol's real build.
"""
from rect_map_opt import ORIGINAL_SCAN, SCAN_REPLACEMENT, COMMIT_ROUTINE


def sizes(lines):
    total=0
    for s in lines:
        s=s.strip()
        if not s or s.endswith(':') or s in ('.a16','.i16'):continue
        op,_,arg=s.partition(' ')
        if op in ('mvn','mvp'):n=3
        elif op in ('rts','rtl','clc','sec','inx','iny','dex','dey','tax','tay','tya','txa','pha','phb','plb','pla','asl','lsr','rol','ror','nop'):
            if op in ('asl','lsr','rol','ror') and arg not in ('a',''):raise AssertionError((s,'size'))
            n=1
        elif op in ('jmp','jsr'):n=3
        elif op in ('bcc','bcs','beq','bne','bpl','bmi'):n=2
        elif op in ('lda','ldx','ldy','sta','stx','sty','cmp','cpx','cpy','adc','sbc','inc','dec'):
            if arg.startswith('#'):n=3
            elif '.l' in op:n=4
            elif arg.endswith(',x') or arg.endswith(',y'):n=3
            elif arg.startswith('$'):
                n=2 if len(arg)<=3 else 3
            elif arg=='a':n=1
            else:raise AssertionError((s,'addr'))
        elif op in ('lda.l','cmp.l','sta.l'):n=4
        else:raise AssertionError((s,'opcode'))
        total+=n
    return total


def report():
    old=sizes(ORIGINAL_SCAN)
    new=sizes(SCAN_REPLACEMENT)+sizes(COMMIT_ROUTINE)
    return dict(old_scan_bytes=old,new_scan_bytes=sizes(SCAN_REPLACEMENT),new_commit_bytes=sizes(COMMIT_ROUTINE),
                net_d000_growth_bytes=new-old,
                estimated_map_dma_entry_from_d1cc=0xD1CC+(new-old),
                hard_next_org=0xD400)

if __name__=='__main__':print(report())
