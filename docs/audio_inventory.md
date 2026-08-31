# Audio Inventory

This is a source-backed inventory, not a claim that the game's audio is
complete. Asset names and counts were read from the local OpenBOR `PACK`
archives with `tools/bor_converter/pak_extract.py` on 2026-08-31.

Status values are restricted to: `implemented`, `present in source/content but
not implemented`, `content-inapplicable`, `intentionally deferred`, and
`unknown requiring source research`.

| Source/content | Inventory | Status | Evidence/current handling |
|---|---|---|---|
| BOR Original `DATA\\SOUNDS` | 29 WAV assets: `BEAT1`, `DIE1`, `FALL`, `GET`, `DIE2`, `JUMP`, `KLUNK`, `MONEY`, `BEEP`, `BEEP2`, `MAXBOOM`, `TIMEOVER`, `INDIRECT`, `EEK`, `PUNCH`, `1UP`, `KULAHEY`, `KULABLOW`, `MAXROCKT`, `MAXUH`, `LEONAHEY`, `WOOD`, `BIKE`, `MARYTOSS`, `MARY_FFP`, `SHAAH`, `DRILL`, `ALIEN`, `ZOEF` | `implemented` for `BEAT1`; `present in source/content but not implemented` for the other 28 | G11's `sfx_hit` plays `soundwork/tad/project/samples/beat1.wav`; no other BOR sound asset is in the TAD SFX project |
| TMNT `data\\SOUNDS` | 57 sound assets, including `BEAT1`, `BEAT`, `BEAT01`, `DASH`, `THROW`, `PUNCH0`, `PIZZA`, `SPIN`, `COWABUNG`, `BEBOPDIE`, `FOOTDIE`, `TURTLE~1`, `ROCKDIE`, `GUNSHOT`, `ELECTRIC`, `METAL`, `WAVE`, and the remaining archive entries | `present in source/content but not implemented` | TMNT visual/stage data is converted, but its sound assets are not imported into TAD |
| BOR Original level/scene music | Referenced tracks include `asc.bor`, `kof.bor`, `1boss.bor`, `saviour.bor`, `control.bor`, `scorcher.bor`, `necktie.bor`, `supertb.bor`, `goarge.bor`, `trick.bor`, `exist.bor`, `joe.bor`, `fsol.bor`, `time.bor`, and `haha.bor` | `present in source/content but not implemented` | The current TAD song is `s02_coin`, reconstructed from surviving compiled artifacts; it is not these BOR music files |
| TMNT level/scene music | Referenced tracks include `NYstreet.bor`, `boss.bor`, `Fire.bor`, `Sewers.bor`, `remix/Gliese86.bor`, `remix/Painovo.bor`, `remix/Tau1.bor`, `remix/Zeta1.bor`, `TMNT.bor`, and `TMNTEnd.bor` | `present in source/content but not implemented` | No BOR/TMNT music track is converted to the current MSU-1 PCM track |
| Character and prop `sound`/`diesound` directives | BOR and TMNT character text files reference death, attack, voice, prop, pickup, and special-effect WAVs | `present in source/content but not implemented` | These directives are source evidence only; no runtime sound dispatch exists for them |
| Menu/game-state audio cues | OpenBOR scene files contain music directives for ending and other scenes; current title, character-select, pause, game-over, and ending paths have no corresponding real BOR cue assets | `intentionally deferred` | Keep future UI/state cue work separate from G11's landed-hit scope |
| `distribution/bor-1.pcm` | One MSU-1 PCM track next to the ROM | `content-inapplicable` | It is a placeholder/proof clip, explicitly not a BOR soundtrack asset |
| TAD `s02_coin` song | One reconstructed TAD song plus `sfx_stub` and `sfx_hit` exports | `intentionally deferred` for soundtrack; `implemented` for `sfx_hit` | TAD/SPC700 remains the short gameplay/UI SFX path; MSU-1 PCM is reserved for the eventual full-quality soundtrack |

## Scope boundary

G11 is complete because its defined scope is one real landed-hit SFX path using
`BEAT1.WAV`. This inventory is future work and does not reopen G11. The full
BOR soundtrack is not currently implemented, and the placeholder MSU-1 PCM
track must not be described as that soundtrack.
