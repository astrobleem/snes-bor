"""Source-backed OpenBOR global sample table for the target legacy engine."""

ENGINE_REVISION = "bcec7cb765eebec555c74aac64a23aa73f1cfe21"
ENGINE_SOURCE = "engine/openbor.c:load_special_sounds"

ENGINE_GLOBAL_AUDIO = [
    {"global": "beat", "asset": "DATA\\SOUNDS\\BEAT1.WAV", "event": "landed-hit", "mechanic_reachable": True, "audio_implemented": True, "reason": "default attack hitsound and accepted attack playback are implemented"},
    {"global": "block", "asset": "DATA\\SOUNDS\\BLOCK.WAV", "event": "blocked-attack", "mechanic_reachable": False, "audio_implemented": False, "reason": "blocking mechanic is not present in the current SNES runtime"},
    {"global": "fall", "asset": "DATA\\SOUNDS\\FALL.WAV", "event": "ordinary-thrown-landing", "mechanic_reachable": True, "audio_implemented": False, "reason": "Documented SNES adaptation: ordinary thrown ground impact is the reachable analogue of OpenBOR's qualifying bounce; the simplified SNES throw model does not reproduce every tobounce predicate"},
    {"global": "get", "asset": "DATA\\SOUNDS\\GET.WAV", "event": "health-pickup", "mechanic_reachable": True, "audio_implemented": False, "reason": "OpenBOR health/item pickup calls global_sample_list.get; current health pickups are implemented but audio dispatch remains unimplemented"},
    {"global": "get_2", "asset": "DATA\\SOUNDS\\MONEY.WAV", "event": "score-pickup", "mechanic_reachable": True, "audio_implemented": False, "reason": "OpenBOR score/money pickup calls global_sample_list.get_2; current score pickups are implemented but audio dispatch remains unimplemented"},
    {"global": "jump", "asset": "DATA\\SOUNDS\\JUMP.WAV", "event": "jump", "mechanic_reachable": True, "audio_implemented": False, "reason": "core/jump.pasm implements the source-backed jump mechanic; audio dispatch remains unimplemented"},
    {"global": "indirect", "asset": "DATA\\SOUNDS\\INDIRECT.WAV", "event": "indirect-attack", "mechanic_reachable": False, "audio_implemented": False, "reason": "OpenBOR indirect-sound call requires a projectile/indirect attack entity; current SNES runtime has no projectile entity or indirect attack path"},
    {"global": "punch", "asset": "DATA\\SOUNDS\\PUNCH.WAV", "event": "attack-swing", "mechanic_reachable": True, "audio_implemented": False, "reason": "current attack/attack-chain path is source-backed; generic swing audio remains unimplemented"},
    {"global": "one_up", "asset": "DATA\\SOUNDS\\1UP.WAV", "event": "one-up", "mechanic_reachable": True, "audio_implemented": False, "reason": "current pickup path implements ONEUP; audio dispatch remains unimplemented"},
    {"global": "time_over", "asset": "DATA\\SOUNDS\\TIMEOVER.WAV", "event": "time-over", "mechanic_reachable": False, "audio_implemented": False, "reason": "OpenBOR time-over call requires a level countdown reaching zero; current SNES runtime has no level timer state or expiration transition"},
    {"global": "beep", "asset": "DATA\\SOUNDS\\BEEP.WAV", "event": "ui-beep", "mechanic_reachable": True, "audio_implemented": False, "reason": "OpenBOR pause selector and character selection call global_sample_list.beep; current SNES menus have corresponding input paths"},
    {"global": "beep_2", "asset": "DATA\\SOUNDS\\BEEP2.WAV", "event": "ui-beep-secondary", "mechanic_reachable": True, "audio_implemented": False, "reason": "OpenBOR pause commit/exit and character confirmation call global_sample_list.beep_2; current SNES menus have corresponding paths"},
    {"global": "pause", "asset": "DATA\\SOUNDS\\PAUSE.WAV", "event": "pause-entry", "mechanic_reachable": True, "audio_implemented": False, "reason": "OpenBOR pause entry calls global_sample_list.pause; current SNES pause state is implemented"},
    {"global": "bike", "asset": "DATA\\SOUNDS\\BIKE.WAV", "event": "bike", "mechanic_reachable": False, "audio_implemented": False, "reason": "bike mechanic is not present in the shipped runtime"},
    {"global": "go", "asset": "DATA\\SOUNDS\\GO.WAV", "event": "go", "mechanic_reachable": False, "audio_implemented": False, "reason": "go prompt audio is not present in the shipped runtime"},
]
