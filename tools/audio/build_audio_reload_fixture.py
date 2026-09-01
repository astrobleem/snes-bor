#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ARTIFACT=ROOT/"tools/audio/sfx_production_banks.json"
OUT=ROOT/"build/audio_reload_fixture"
SRC=ROOT/"src/audio_reload_fixture.pasm"
NMI_SRC=ROOT/"src/core/nmi_audio_reload_fixture.pasm"
BIN=OUT/"main.bin"; SYM=OUT/"main.sym"; ROM=ROOT/"build/audio_reload_fixture.sfc"
BEAT="bor-original:DATA\\SOUNDS\\BEAT1.WAV"
FIXTURE_BANK=11; BANK_SIZE=0x8000; ROM_SIZE=0x400000
DOTNET=os.environ.get("DOTNET",r"C:\Users\chad\.dotnet\dotnet.exe")
POPPY=os.environ.get("POPPY_DLL",r"E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll")
def fail(s): raise SystemExit("FAIL: "+s)
def select():
    a=json.loads(ARTIFACT.read_text(encoding="utf-8"))
    rows=sorted([r for r in a["maps"] if r["asset"].upper()==BEAT.upper()],key=lambda r:r["bank_id"])
    if not rows: fail("no BOR BEAT1 mapping")
    row=rows[0]; bank=next((b for b in a["banks"] if b["bank_id"]==row["bank_id"]),None)
    if bank is None: fail("selected bank metadata missing")
    payload=ROOT/("soundwork/tad/build/sfx_banks/bank_%02d/common-data.bin"%bank["bank_id"])
    if not payload.is_file(): fail("payload missing: "+str(payload))
    raw=payload.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
    if len(raw)!=bank["common_data_bytes"] or sha!=bank["common_data_sha256"]: fail("payload metadata mismatch")
    return row,bank,payload,sha
def prepare(row,bank,payload,sha):
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True); shutil.copy2(payload,OUT/"common-data.bin")
    inc="; GENERATED TEST-ONLY; never used by production build.\n"
    inc+="AUDIO_RELOAD_FIXTURE_BANK_ID = %d\n"%row["bank_id"]
    inc+="AUDIO_RELOAD_FIXTURE_COMMON_SIZE = %d\n"%len(payload.read_bytes())
    inc+="AUDIO_RELOAD_FIXTURE_COMMON_ROM_BANK = %d\n"%FIXTURE_BANK
    inc+="AUDIO_RELOAD_FIXTURE_COMMON_ROM_ADDR = $8000\n"
    inc+="AUDIO_RELOAD_FIXTURE_BEAT1_LOCAL_ID = %d\n"%row["local_effect_id"]
    inc+="AUDIO_RELOAD_FIXTURE_COMMON_SHA256 = \"%s\"\n"%sha
    (OUT/"audio_reload_fixture.inc").write_text(inc,encoding="ascii")
def make_source(row,bank):
    text=(ROOT/"src/main.pasm").read_text(encoding="utf-8")
    const="""
; TEST-ONLY reload fixture telemetry.
AudioReloadFixtureEnabled = $7E2A00
AudioReloadFixtureReady = $7E2A01
AudioReloadFixtureBeatQueued = $7E2A02
AudioReloadFixtureRequestCount = $7E2A03
AudioReloadFixtureStateBefore = $7E2A04
AudioReloadFixtureStateAfterProcess = $7E2A05
AudioReloadFixtureStateAfterFinish = $7E2A06
AudioReloadFixtureFinalState = $7E2A07
AudioReloadFixtureMainLoopBefore = $7E2A08
AudioReloadFixtureMainLoopAfter = $7E2A0A
AudioReloadFixtureTransferChunks = $7E2A11
AudioReloadFixtureMainLoopCounter = $7E2A13
AudioReloadFixtureCallbackCount = $7E2A15
AudioReloadFixtureCallbackBank = $7E2A16
AudioReloadFixtureCallbackAddr = $7E2A17
AudioReloadFixtureCallbackSize = $7E2A19
AudioReloadFixtureQueuedBank = $7E2A1B
AudioReloadFixtureQueuedAddr = $7E2A1C
AudioReloadFixtureQueuedSize = $7E2A1E
AudioReloadFixtureRawNmiCounter = $7E2A20
AudioReloadFixtureRawNmiStart = $7E2A21
AudioReloadFixtureRawNmiEnd = $7E2A22
AudioReloadFixtureNmiFrameStart = $7E2A23
AudioReloadFixtureNmiFrameEnd = $7E2A24
AudioReloadFixtureMainLoopStart = $7E2A25
AudioReloadFixtureMainLoopEnd = $7E2A26
AudioReloadFixtureQueuedCaptured = $7E2A27
"""
    const+="AudioReloadFixtureCommonSize = %d\nAudioReloadFixtureBeat1LocalId = %d\n"%(bank["common_data_bytes"],row["local_effect_id"])
    text=text.replace("SFX_HIT_ID = 0\n","SFX_HIT_ID = 0\n"+const,1)
    boot_audio="""    sei
    sep #$20
.a8
    rep #$10
"""
    boot_audio_init="""    sei
    sep #$20
.a8
    lda #0
    sta.l AudioReloadFixtureEnabled
    sta.l AudioReloadFixtureReady
    sta.l AudioReloadFixtureBeatQueued
    sta.l AudioReloadFixtureRequestCount
    sta.l AudioReloadFixtureQueuedCaptured
    rep #$10
"""
    if text.count(boot_audio)!=1: fail("TAD boot initialization anchor is not unique")
    text=text.replace(boot_audio,boot_audio_init,1)
    load_site="TadPrivate_Process_WaitingForLoader__LoadData:\n    jsl LoadAudioData"
    if text.count(load_site)!=1: fail("TAD LoadAudioData call site is not unique")
    text=text.replace(load_site,"TadPrivate_Process_WaitingForLoader__LoadData:\n    jsl AudioReloadFixture_LoadDataDispatch",1)
    if text.count("TadPrivate_Process_WaitingForLoader__LoadData:\n    jsl AudioReloadFixture_LoadDataDispatch")!=1:
        fail("fixture LoadAudioData call-site routing missing")
    if text.count("AudioReloadFixture_LoadDataDispatch__production:\n    jsl LoadAudioData")!=1:
        fail("fixture production LoadAudioData fallback missing")
    loading_branch="        bcs TadPrivate_Process_Loading\n"
    if text.count(loading_branch)!=1: fail("TAD loading branch anchor is not unique")
    text=text.replace(loading_branch,"""        bcc TadPrivate_Process__NotLoadingBranch
        brl TadPrivate_Process_Loading
TadPrivate_Process__NotLoadingBranch:
""",1)
    loop="scpu_main_loop:\n"
    if text.count(loop)!=1: fail("main loop anchor missing")
    text=text.replace(loop,loop,1)
    marker="    sep #$20\n.a8\n    jsl Tad_Process\n"
    request="""    sep #$20
.a8
    lda.l AudioReloadFixtureEnabled
    bne AudioReloadFixture_SkipRequest
    jsr Tad_IsSfxPlaying
    bcc AudioReloadFixture_SkipRequest
    lda #1
    sta.l AudioReloadFixtureEnabled
    sta.l AudioReloadFixtureRequestCount
    lda.l TadPrivate_state
    sta.l AudioReloadFixtureStateBefore
    lda.l AudioReloadFixtureMainLoopCounter
    sta.l AudioReloadFixtureMainLoopBefore
    lda.l Nmi_FrameCounter
    sta.l AudioReloadFixtureNmiCommitStart
    lda.l AudioReloadFixtureRawNmiCounter
    sta.l AudioReloadFixtureRawNmiCounter
    lda #0\n    sta.l AudioReloadFixtureTransferChunks
    jsr Tad_ReloadCommonAudioData
    lda #0
    jsl Tad_LoadSong
AudioReloadFixture_SkipRequest:
    jsl Tad_Process
    lda.l TadPrivate_state
    sta.l AudioReloadFixtureStateAfterProcess
"""
    if text.count(marker)!=1: fail("audio processing marker is not unique")
    request="    sep #$20\n.a8\n    jsl AudioReloadFixture_Process\n"
    text=text.replace(marker,request,1)
    finish="    jsl Tad_FinishLoadingData\n"
    after="""    jsl Tad_FinishLoadingData
    lda.l TadPrivate_state
    sta.l AudioReloadFixtureStateAfterFinish
    lda.l AudioReloadFixtureEnabled
    beq AudioReloadFixture_SkipAfterFinish
    lda.l TadPrivate_state
    sta.l AudioReloadFixtureFinalState
    jsr Tad_IsSfxPlaying
    bcc AudioReloadFixture_SkipAfterFinish
    lda #1
    sta.l AudioReloadFixtureReady
    lda.l AudioReloadFixtureMainLoopCounter
    sta.l AudioReloadFixtureMainLoopAfter
    lda.l Nmi_FrameCounter
    sta.l AudioReloadFixtureNmiCommitEnd
    lda.l AudioReloadFixtureRawNmiCounter
    sta.l AudioReloadFixtureRawNmiCounter
    lda.l AudioReloadFixtureBeatQueued
    bne AudioReloadFixture_SkipAfterFinish
    lda #1
    sta.l AudioReloadFixtureBeatQueued
    lda #AudioReloadFixtureBeat1LocalId
    jsr Tad_QueueSoundEffect
AudioReloadFixture_SkipAfterFinish:
"""
    if text.count(finish)!=1: fail("finish marker is not unique")
    after="    jsl AudioReloadFixture_Finish\n"
    text=text.replace(finish,after,1)
    transfer="TadPrivate_Loader_TransferData:\n"
    if text.count(transfer)!=1: fail("transfer routine anchor missing")
    text=text.replace(transfer,"""TadPrivate_Loader_TransferData:
    lda.l AudioReloadFixtureTransferChunks
    inc a
    sta.l AudioReloadFixtureTransferChunks
""",1)
    nmi=(ROOT/"src/core/nmi.pasm").read_text(encoding="utf-8")
    nmi_anchor="    phd\n\n    sep #$20\n"
    if nmi.count(nmi_anchor)!=1: fail("NMI save anchor is not unique")
    nmi=nmi.replace(nmi_anchor,"""    phd

    sep #$20
    lda.l AudioReloadFixtureRawNmiCounter
    inc a
    sta.l AudioReloadFixtureRawNmiCounter
""",1)
    NMI_SRC.write_text(nmi,encoding="utf-8")
    if text.count('.include "core/nmi.pasm"')!=1: fail("NMI include anchor is not unique")
    text=text.replace('.include "core/nmi.pasm"','.include "core/nmi_audio_reload_fixture.pasm"',1)
    descriptor="    jsr TadPrivate_Loader_SetDataToTransfer\n\n    ; Must set state AFTER"
    if text.count(descriptor)!=1: fail("TAD transfer descriptor anchor is not unique")
    descriptor_replacement="""    jsr TadPrivate_Loader_SetDataToTransfer

    lda.l TadPrivate_dataToTransfer_bank
    sta.l AudioReloadFixtureQueuedBank
    lda.l AudioReloadFixtureCallbackCount
    cmp #1
    beq AudioReloadFixture_CheckQueuedCapture
    jmp AudioReloadFixture_SkipQueuedCapture
AudioReloadFixture_CheckQueuedCapture:
    lda.l AudioReloadFixtureQueuedCaptured
    beq AudioReloadFixture_CaptureQueued
    jmp AudioReloadFixture_SkipQueuedCapture
AudioReloadFixture_CaptureQueued:
    rep #$20
.a16
    txa
    sta.l AudioReloadFixtureQueuedAddr
    tya
    sta.l AudioReloadFixtureQueuedSize
    sep #$20
.a8
    lda #1
    sta.l AudioReloadFixtureQueuedCaptured
AudioReloadFixture_SkipQueuedCapture:

    ; Must set state AFTER"""
    text=text.replace(descriptor,descriptor_replacement,1)
    support="""\n.org $B700\nAudioReloadFixture_LoadDataDispatch:\n.a8\n    cmp #0\n    bne AudioReloadFixture_LoadDataDispatch__production\n    lda.l AudioReloadFixtureEnabled\n    beq AudioReloadFixture_LoadDataDispatch__production\n    lda.l AudioReloadFixtureCallbackCount\n    inc a\n    sta.l AudioReloadFixtureCallbackCount\n    rep #$30\n.a16\n    lda #AudioReloadFixtureCommonSize\n    tay\n    sta.l AudioReloadFixtureCallbackSize\n    ldx #$8000\n    phx\n    pla\n    sta.l AudioReloadFixtureCallbackAddr\n    sep #$20\n.a8\n    lda #11\n    sta.l AudioReloadFixtureCallbackBank\n    sec\n    rtl\nAudioReloadFixture_LoadDataDispatch__production:\n    jsl LoadAudioData\n    rtl\nAudioReloadFixture_Process:\n    lda.l AudioReloadFixtureMainLoopCounter\n    inc a\n    sta.l AudioReloadFixtureMainLoopCounter\n    jsr AudioReloadFixture_Request\n    jsl Tad_Process\n    lda.l TadPrivate_state\n    sta.l AudioReloadFixtureStateAfterProcess\n    rtl\nAudioReloadFixture_Finish:\n    lda.l TadPrivate_state\n    cmp #LOADING_COMMON_AUDIO_DATA\n    bne AudioReloadFixture_Finish__no_common_snapshot\n    lda.l AudioReloadFixtureRawNmiCounter\n    sta.l AudioReloadFixtureRawNmiStart\n    lda.l Nmi_FrameCounter\n    sta.l AudioReloadFixtureNmiFrameStart\n    lda.l AudioReloadFixtureMainLoopCounter\n    sta.l AudioReloadFixtureMainLoopStart\n    lda #0\n    sta.l AudioReloadFixtureTransferChunks\nAudioReloadFixture_Finish__no_common_snapshot:\n    jsl Tad_FinishLoadingData\n    lda.l TadPrivate_state\n    sta.l AudioReloadFixtureStateAfterFinish\n    cmp #WAITING_FOR_LOADER_SONG\n    bne AudioReloadFixture_Finish__no_common_end\n    lda.l AudioReloadFixtureRawNmiCounter\n    sta.l AudioReloadFixtureRawNmiEnd\n    lda.l Nmi_FrameCounter\n    sta.l AudioReloadFixtureNmiFrameEnd\n    lda.l AudioReloadFixtureMainLoopCounter\n    sta.l AudioReloadFixtureMainLoopEnd\nAudioReloadFixture_Finish__no_common_end:\n    jsr AudioReloadFixture_AfterFinish\n    rtl\nAudioReloadFixture_Request:\n.a8\n    lda.l AudioReloadFixtureEnabled\n    bne AudioReloadFixture_Request__done\n    jsr Tad_IsSfxPlaying\n    bcc AudioReloadFixture_Request__done\n    lda #1\n    sta.l AudioReloadFixtureEnabled\n    sta.l AudioReloadFixtureRequestCount\n    lda.l TadPrivate_state\n    sta.l AudioReloadFixtureStateBefore\n    lda #0\n    sta.l AudioReloadFixtureTransferChunks\n    jsr Tad_ReloadCommonAudioData\n    lda #0\n    jsl Tad_LoadSong\nAudioReloadFixture_Request__done:\n    rts\nAudioReloadFixture_AfterFinish:\n    lda.l AudioReloadFixtureEnabled\n    beq AudioReloadFixture_AfterFinish__done\n    lda.l TadPrivate_state\n    sta.l AudioReloadFixtureFinalState\n    jsr Tad_IsSfxPlaying\n    bcc AudioReloadFixture_AfterFinish__done\n    lda #1\n    sta.l AudioReloadFixtureReady\n    lda.l AudioReloadFixtureBeatQueued\n    bne AudioReloadFixture_AfterFinish__done\n    lda #1\n    sta.l AudioReloadFixtureBeatQueued\n    lda #AudioReloadFixtureBeat1LocalId\n    jsr Tad_QueueSoundEffect\nAudioReloadFixture_AfterFinish__done:\n    rts\n"""
    marker2="    .db $00\n\n; Msu1_LoadFrame"
    if text.count(marker2)!=1: fail("blank-song insertion anchor is not unique")
    text=text.replace(marker2,"    .db $00\n"+support+"\n; Msu1_LoadFrame",1)
    if text.count(".org $FC00")!=1: fail("fixture boot origin is not unique")
    text=text.replace(".org $FC00", ".org $FC10", 1)
    text+="\n.bank 11\n.org $8000\n    .incbin \"../build/audio_reload_fixture/common-data.bin\"\n"
    SRC.write_text(text,encoding="utf-8")
def assemble():
    if not Path(DOTNET).is_file() or not Path(POPPY).is_file(): fail("Poppy toolchain unavailable")
    r=subprocess.run([DOTNET,POPPY,str(SRC),"-s",str(SYM),"-o",str(BIN)])
    if r.returncode: fail("fixture assembly exit %d"%r.returncode)
def pack(payload,sha,row):
    sys.path.insert(0,str(ROOT))
    sys.path.insert(0,str(ROOT/"tools/bor_converter"))
    import build_rom,pack_msu_roster
    data=BIN.read_bytes()
    if len(data)>ROM_SIZE: fail("fixture exceeds ROM size")
    embedded=data[FIXTURE_BANK*BANK_SIZE:FIXTURE_BANK*BANK_SIZE+len(payload.read_bytes())]
    if embedded!=payload.read_bytes(): fail("assembled bank-11 payload byte comparison failed")
    if hashlib.sha256(embedded).hexdigest()!=sha: fail("assembled payload SHA mismatch")
    rom=bytearray(ROM_SIZE); rom[:len(data)]=data
    rom[0x7FC0:0x7FD5]=b"AUDIO RELOAD FIXTURE".ljust(21,b" ")
    rom[0x7FD5:0x7FDC]=bytes([0x23,0x35,0x0C,0x08,0x01,0x33,0])
    for off,val in ((0x7FE4,0xFFB0),(0x7FE6,0xFFB0),(0x7FE8,0xFFB0),(0x7FEA,0xFFA0),(0x7FEC,0xFFB0),(0x7FF4,0xFFB0),(0x7FF8,0xFFB0),(0x7FFA,0xFFA0),(0x7FFC,0xFC10),(0x7FFE,0xFFB0)):
        rom[off]=val&255; rom[off+1]=val>>8
    total=sum(rom)&65535; comp=(~total)&65535
    rom[0x7FDC:0x7FE0]=bytes([comp&255,comp>>8,total&255,total>>8])
    missing=[p for p in build_rom.SPAWN_TABLES+[build_rom.VM_MODULE] if not Path(p).exists()]
    if missing: fail("missing MSU input(s): "+", ".join(missing))
    msu,_=pack_msu_roster.pack_roster(build_rom.ROSTER_PREFIXES,bgs=build_rom.BG_SCREENS,fps=build_rom.FP_SCREENS,spawns=[Path(p).read_bytes() for p in build_rom.SPAWN_TABLES],vm_blob=Path(build_rom.VM_MODULE).read_bytes(),playable_count=build_rom.PLAYABLE_ROSTER_COUNT)
    ROM.write_bytes(rom); (ROOT/"build/audio_reload_fixture.msu").write_bytes(msu)
    print("fixture ROM written: %s"%ROM)
    print("fixture payload bank %d, mapped $8000, %d bytes, byte-match PASS"%(FIXTURE_BANK,len(payload.read_bytes())))
    print("source bank %d; common sha256 %s; BEAT1 local %d"%(row["bank_id"],sha,row["local_effect_id"]))
if __name__=="__main__":
    row,bank,payload,sha=select(); prepare(row,bank,payload,sha); make_source(row,bank); assemble(); pack(payload,sha,row)


