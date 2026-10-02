from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str((ROOT / "tools/audio").resolve()))
import build_audio_reload_fixture as base


def main():
    base.OUT = (ROOT / "build/audio_reload_async_fixture").resolve()
    base.SRC = (ROOT / "src/audio_reload_async_fixture.pasm").resolve()
    base.BIN = base.OUT / "main.bin"
    base.SYM = base.OUT / "main.sym"
    base.ROM = (ROOT / "build/audio_reload_async_fixture.sfc").resolve()
    row, bank, payload, sha = base.select()
    base.prepare(row, bank, payload, sha)
    base.make_source(row, bank)
    text = base.SRC.read_text(encoding="utf-8")
    text = text.replace(
        "AudioReloadFixtureQueuedCaptured = $7E2A27\n",
        "AudioReloadFixtureQueuedCaptured = $7E2A27\n"
        "AudioReloadAsyncRequestRaw = $7E2A28\n"
        "AudioReloadAsyncRequestNmi = $7E2A29\n"
        "AudioReloadAsyncRequestMain = $7E2A2A\n"
        "AudioReloadAsyncCommonRaw = $7E2A2B\n"
        "AudioReloadAsyncCommonNmi = $7E2A2C\n"
        "AudioReloadAsyncCommonMain = $7E2A2D\n"
        "AudioReloadAsyncReadyRaw = $7E2A2E\n"
        "AudioReloadAsyncReadyNmi = $7E2A2F\n"
        "AudioReloadAsyncReadyMain = $7E2A30\n"
        "AudioReloadAsyncCommonSeen = $7E2A31\n",
        1,
    )
    request_start = text.index("AudioReloadFixture_Request:")
    request = "    sta.l AudioReloadFixtureRequestCount\n"
    request_at = text.index(request, request_start)
    request_extra = (
        "    lda.l AudioReloadFixtureRawNmiCounter\n"
        "    sta.l AudioReloadAsyncRequestRaw\n"
        "    lda.l Nmi_FrameCounter\n"
        "    sta.l AudioReloadAsyncRequestNmi\n"
        "    lda.l AudioReloadFixtureMainLoopCounter\n"
        "    sta.l AudioReloadAsyncRequestMain\n"
        "    ldx #800\n"
        "    jsr Tad_SetTransferSize\n"
    )
    text = text[:request_at] + request + request_extra + text[request_at + len(request):]
    process_marker = "    sta.l AudioReloadFixtureStateAfterProcess\n"
    process_at = text.index(process_marker, text.index("AudioReloadFixture_Process:"))
    process_extra = (
        "    lda.l AudioReloadAsyncCommonSeen\n"
        "    bne AudioReloadAsync_ProcessDone\n"
        "    lda.l TadPrivate_state\n"
        "    cmp #WAITING_FOR_LOADER_SONG\n"
        "    bne AudioReloadAsync_ProcessDone\n"
        "    lda #1\n"
        "    sta.l AudioReloadAsyncCommonSeen\n"
        "    lda.l AudioReloadFixtureRawNmiCounter\n"
        "    sta.l AudioReloadAsyncCommonRaw\n"
        "    lda.l Nmi_FrameCounter\n"
        "    sta.l AudioReloadAsyncCommonNmi\n"
        "    lda.l AudioReloadFixtureMainLoopCounter\n"
        "    sta.l AudioReloadAsyncCommonMain\n"
        "AudioReloadAsync_ProcessDone:\n"
    )
    process_at_end = process_at + len(process_marker)
    text = text[:process_at_end] + process_extra + text[process_at_end:]
    start = text.index("AudioReloadFixture_Finish:")
    end = text.index("AudioReloadFixture_Request:", start)
    async_finish = """AudioReloadFixture_Finish:
    lda.l AudioReloadFixtureEnabled
    beq AudioReloadFixture_Finish__production
    lda.l TadPrivate_state
    cmp #PLAYING_SFX
    bcc AudioReloadFixture_Finish__async_wait
    jsl Tad_FinishLoadingData
    lda.l TadPrivate_state
    sta.l AudioReloadFixtureStateAfterFinish
    jsr AudioReloadFixture_AfterFinish
AudioReloadFixture_Finish__async_wait:
    rtl
AudioReloadFixture_Finish__production:
    jsl Tad_FinishLoadingData
    rtl
"""
    text = text[:start] + async_finish + text[end:]
    after_start = text.index("AudioReloadFixture_AfterFinish:")
    ready_marker = "    sta.l AudioReloadFixtureReady\n"
    ready_at = text.index(ready_marker, after_start) + len(ready_marker)
    ready_extra = (
        "    lda.l AudioReloadFixtureRawNmiCounter\n"
        "    sta.l AudioReloadAsyncReadyRaw\n"
        "    lda.l Nmi_FrameCounter\n"
        "    sta.l AudioReloadAsyncReadyNmi\n"
        "    lda.l AudioReloadFixtureMainLoopCounter\n"
        "    sta.l AudioReloadAsyncReadyMain\n"
    )
    text = text[:ready_at] + ready_extra + text[ready_at:]
    base.SRC.write_text(text, encoding="utf-8")
    base.assemble()
    base.pack(payload, sha, row)
    print("async fixture uses Tad_Process only while fixture reload is active")


if __name__ == "__main__":
    main()
