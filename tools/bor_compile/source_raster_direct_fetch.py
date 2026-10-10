"""Opt-in size-neutral bank-zero routing for a direct palette IRQ entry.

Move only the fetch/budget loop outside bank zero, returning to its original
dispatch/yield/fault continuations with JML. The existing Vm_Fetch JSL/RTS
storage can then route IRQ directly, without a per-interrupt I-bit classifier.
Installation is private until native VM, IRQ and runtime leases are proven.
"""
from pathlib import Path
import re


def emit(sy):
    return f'''SourceRasterDirectFetchLoop:
.a16
.i16
 rep #$31
 lda.l {sy['VmState_Budget']}
 beq SourceRasterDirectFetchYield
 dec a
 sta.l {sy['VmState_Budget']}
 jsl {sy['Vm_FetchSource']}
 bcc SourceRasterDirectFetchDispatch
 jml {sy['Vm_Fault']}
SourceRasterDirectFetchDispatch:
.a16
.i16
 jml {sy['Vm_Run__fetched']}
SourceRasterDirectFetchYield:
.a16
.i16
 jml {sy['Vm_Run__yield']}
'''


def transform(raw,sy,loop,irq,offset,source=Path('src/core/vm/vm_run.pasm')):
    # Sole ordinary fetch callsite must remain inside the loop being redirected.
    text=source.read_text()
    calls=re.findall(r'^\s*jsr\s+Vm_Fetch\s*$',text,re.M)
    if len(calls)!=1:raise ValueError('DIRECT_FETCH_SINGLE_ORDINARY_CALLER_REQUIRED')
    start=offset(sy['Vm_Run__loop']);fetch=offset(sy['Vm_Fetch'])
    expected=bytes.fromhex('c2 31 af')+sy['VmState_Budget'].to_bytes(3,'little')
    if raw[start:start+6]!=expected:raise ValueError('DIRECT_FETCH_LOOP_INSTRUCTION_SHAPE')
    if raw[fetch:fetch+5]!=b'\x22'+sy['Vm_FetchSource'].to_bytes(3,'little')+b'\x60':
        raise ValueError('DIRECT_FETCH_GATEWAY_INSTRUCTION_SHAPE')
    if loop>>16==0 or irq>>16==0:raise ValueError('DIRECT_FETCH_NEW_CODE_MUST_BE_OUTSIDE_BANK_ZERO')
    raw[start:start+6]=b'\x5c'+loop.to_bytes(3,'little')+b'\xea\xea'
    raw[fetch:fetch+4]=b'\x5c'+irq.to_bytes(3,'little')
    raw[0x7fee:0x7ff0]=(sy['Vm_Fetch']&65535).to_bytes(2,'little')
