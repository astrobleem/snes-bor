# Long one-shot streaming feasibility

This is capacity and compatibility evidence, not a production streaming design.
The baseline policy remains `normal`, `one_channel=true`, and
`interruptible=true`.

## Static-common escape hatches

Exact recompilation is recorded in
`tools/audio/streaming_witnesses.json`. The repeated TMNT Foot combat set is
70,260 bytes. Removing only `FOOTDIE.WAV` from static common storage produces
a 37,508-byte common environment with 23,320 bytes margin. Kula's worst BOR
set fits after externalizing `EEK.WAV`. Max's worst set requires at least two
of the audited long candidates; the minimum-storage witness is `EEK.WAV` plus
`MAXROCKT.WAV`.

This does not authorize removal or streaming. Short, unpredictable effects are
not candidate witnesses.

## Super Dragon's Lair donor

Audited source: `E:/gh/SNES-SuperDragonsLairArcade`.

The 65816 builds a channel-7 HDMA table in a 256-byte WRAM staging buffer. Each
requested stream frame is 144 BRR bytes. HDMA writes all four APU ports over 36
scanlines. The SPC requests frames by number and acknowledges start/completion
through the same ports. The SPC uses eight 144-byte buffers (`$480` bytes) at
`$FB80`, starts after seven buffers, and refills according to an SPC timer. It
uses sample-directory entry 33 and directly programs physical DSP voice 0
(called channel 1 in donor comments), pitch `$0400`, direct gain `$7f`, and
explicit KON/KOFF. Streaming temporarily owns the donor port protocol and a
MOD voice; it is integrated with that driver's command state machine rather
than being an independent peripheral.

There is no underrun recovery protocol beyond cadence/handshake preservation;
the producer must answer requested frames on time.

## TAD 0.3.0 compatibility

Audited official tag `v0.3.0` (`00215a2`) and the vendored 65816 port.

TAD exclusively owns `$2140-$2143`. Its driver defines eight virtual music
channels and two virtual SFX channels. Physical voices 6 and 7 are shared by
music channels 6/7 and SFX channels 8/9. Consequently there is no unused DSP
voice. In the project's blank-song/SFX-only mode, a specialized stream could
reserve physical voice 7 only after modifying TAD to suppress its normal
voice-shadow, KON, KOFF, noise, and echo writes for that voice while streaming.
Resident TAD SFX concurrency would fall from two physical voices to one during
the stream.

The donor protocol cannot coexist unchanged because both systems own all four
APU ports. A viable experiment would require a TAD-owned streaming command and
bulk-transfer state in the SPC driver. The 37,508-byte reduced Foot common set
leaves enough ARAM headroom for the donor-sized 1,152-byte ring, but placement
must be compiler/driver-owned so it cannot collide with common data, song data,
the directory, or echo memory.

## Concurrency blocker

The current runtime has three simultaneous non-player slots. A player attack
checks slots 1, 2, and 3 in one action pass, so multiple Foot entities can die
on the same gameplay frame. Foot level content fills multiple Foot slots. A
source-faithful semantic diesound dispatcher is not implemented yet, so there
is no honest pre-TAD live trace of those requests in the current ROM.

One streamed voice would therefore require an explicit restart/drop/suppress
policy for overlapping Foot deaths and would leave only one physical TAD SFX
voice for landed-hit/attack effects during the vocal. That fidelity decision
is unresolved. Per the feasibility gate, no streaming fixture or multi-voice
extension is implemented yet.
