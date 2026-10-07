"""Isolated ASAD backend proof for a selected source namespace asset."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture,REQUEST
from _harness import Reporter
from m4_projectile_audio_fixture import configure
from m4_source_audio_native_verify import verify
from m4_input_controller_native import offset

ASM=r'''
; Private benchmark dispatch in the foreground wait. It owns no source VM
; callbacks and cannot certify an authored gameplay sound event.
SourceAudioAssetWait:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l REQUEST
 cmp #$b4ad
 bne SourceAudioAssetWaitDone
 lda #0
 sta.l REQUEST
 jsl SourceAudioAssetFixture
 bcs SourceAudioAssetWaitBad
 lda #1
 sta.l INDEX
 bra SourceAudioAssetWaitDone
SourceAudioAssetWaitBad:
.a16
.i16
 lda #1
 sta.l ERROR
SourceAudioAssetWaitDone:
.a16
.i16
 ply
 plx
 pla
 plp
 jml REALWAIT
SourceAudioAssetFixture:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 phd
 phb
 lda #0
 tcd
 sep #$20
.a8
 pha
 plb
 rep #$30
.a16
.i16
 lda #ASSETINDEX
 jsl STARTSOURCE
 bcs SourceAudioAssetFixtureBad
 plb
 pld
 ply
 plx
 pla
 plp
 clc
 rtl
SourceAudioAssetFixtureBad:
.a16
.i16
 plb
 pld
 ply
 plx
 pla
 plp
 sec
 rtl
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['rom','assets','packed','output']:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--sound-index',type=int,default=0);a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((a.assets/'report.json').read_text())
    row=next(r for r in manifest['compiled']if r['sound_index']==a.sound_index)
    row,transform,before,closeout=configure(a.output,a.assets.resolve(),row['source_path'],isolate=True,prefill=True,generic_rom=a.packed.resolve())
    audio_transform=transform
    def transform(raw,sy):
        audio_transform(raw,sy)
        at=offset(sy['Core_Nmi_WaitFrame'])
        assert raw[at:at+4]==b'\x5c'+sy['Tad_StreamWaitFrame'].to_bytes(3,'little')
        raw[at+1:at+4]=sy['SourceAudioAssetWait'].to_bytes(3,'little')
    audio_before=before
    def before(m,sy):
        audio_before(m,sy)
        m.write_u16(REQUEST+6,0)
        # This backend fixture owns no foreign script context. Disable its
        # dormant coroutine lease before posting the isolated audio request.
        m.write_u16(sy['SourceVMRun4086_Ready'],0)
        m.write_u16(sy['SourceVMRun4086_Busy'],0)
        m.write_u16(sy['VmSourceFrame_Pending'],0)
        m.write_u16(sy['Game_State'],3)
    r=Reporter('M4-ASAD-SOURCE-STREAM',kind='GATE')
    env={'MESEN_VOICE_CAPTURE_PATH':str(a.output/'voice0.raw'),'MESEN_VOICE_CAPTURE_VOICE':'0','MESEN_VOICE_CAPTURE_ARM_FILE':str(a.output/'voice0.raw.arm')}
    raw,log=run_fixture(a.rom,a.output,[dict(sound_index=a.sound_index)],'SourceAudioAssetFixture','SourceAudio_Status',0xb4ad,[],
        '',r,append=ASM.replace('ASSETINDEX',str(a.sound_index)),bindings={'STARTSOURCE':'SourceAudio_Start','REALWAIT':'Tad_StreamWaitFrame'},batch_size=1,frame_limit=200,
        rom_transform=transform,before_start=before,closeout=closeout,emulator_env=env)
    proof=verify(a.output,a.assets.resolve(),require_dsp_trace=True)
    trace=json.loads((a.output/'audio-stream-trace.json').read_text())
    r.check('full acknowledged source cursor equals meaningful asset length',trace['observations'][-1]['source_offset']==row['brr_bytes'])
    r.check('ASAD full source block traversal and END',proof['status']=='PASS')
    result=dict(schema='BYOR_ASAD_NATIVE_ASSET_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',
        checks=r.results,proof=proof,rom_sha256=hashlib.sha256(raw).hexdigest(),sound_index=a.sound_index,
        namespace_derived=True,source_binding_instrumented=True,production_driver_override=False,
        foreign_vm_owner_disabled_for_backend_fixture=True,
        authored_source_event_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
