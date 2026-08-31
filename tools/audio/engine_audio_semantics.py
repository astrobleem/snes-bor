"""Source-backed OpenBOR global sample table for the target legacy engine."""

ENGINE_REVISION = "bcec7cb765eebec555c74aac64a23aa73f1cfe21"
ENGINE_SOURCE = "engine/openbor.c:load_special_sounds"

ENGINE_GLOBAL_AUDIO = [
    {"global": "beat", "asset": "DATA\\SOUNDS\\BEAT1.WAV", "event": "landed-hit", "mechanic_reachable": True, "audio_implemented": True, "reason": "default attack hitsound and accepted attack playback are implemented"},
    {"global": "block", "asset": "DATA\\SOUNDS\\BLOCK.WAV", "event": "blocked-attack", "mechanic_reachable": False, "audio_implemented": False, "reason": "blocking mechanic is not present in the current SNES runtime"},
    {"global": "fall", "asset": "DATA\\SOUNDS\\FALL.WAV", "event": "fall", "mechanic_reachable": False, "audio_implemented": False, "reason": "fall sound dispatch is not present in the current SNES runtime"},
    {"global": "get", "asset": "DATA\\SOUNDS\\GET.WAV", "event": "get-up", "mechanic_reachable": True, "audio_implemented": False, "reason": "get-up/death recovery mechanic exists; audio dispatch remains unimplemented"},
    {"global": "get_2", "asset": "DATA\\SOUNDS\\MONEY.WAV", "event": "money-pickup", "mechanic_reachable": True, "audio_implemented": False, "reason": "money pickup exists; generic pickup audio dispatch remains unimplemented"},
    {"global": "jump", "asset": "DATA\\SOUNDS\\JUMP.WAV", "event": "jump", "mechanic_reachable": True, "audio_implemented": False, "reason": "core/jump.pasm implements the source-backed jump mechanic; audio dispatch remains unimplemented"},
    {"global": "indirect", "asset": "DATA\\SOUNDS\\INDIRECT.WAV", "event": "indirect-attack", "mechanic_reachable": False, "audio_implemented": False, "reason": "projectile sound dispatch is not implemented"},
    {"global": "punch", "asset": "DATA\\SOUNDS\\PUNCH.WAV", "event": "attack-swing", "mechanic_reachable": True, "audio_implemented": False, "reason": "current attack/attack-chain path is source-backed; generic swing audio remains unimplemented"},
    {"global": "one_up", "asset": "DATA\\SOUNDS\\1UP.WAV", "event": "one-up", "mechanic_reachable": True, "audio_implemented": False, "reason": "current pickup path implements ONEUP; audio dispatch remains unimplemented"},
    {"global": "time_over", "asset": "DATA\\SOUNDS\\TIMEOVER.WAV", "event": "time-over", "mechanic_reachable": False, "audio_implemented": False, "reason": "time-over state audio is not implemented"},
    {"global": "beep", "asset": "DATA\\SOUNDS\\BEEP.WAV", "event": "ui-beep", "mechanic_reachable": False, "audio_implemented": False, "reason": "no authored reachable UI beep event is represented"},
    {"global": "beep_2", "asset": "DATA\\SOUNDS\\BEEP2.WAV", "event": "ui-beep-secondary", "mechanic_reachable": False, "audio_implemented": False, "reason": "no authored reachable UI beep event is represented"},
    {"global": "pause", "asset": "DATA\\SOUNDS\\PAUSE.WAV", "event": "pause", "mechanic_reachable": False, "audio_implemented": False, "reason": "no source-backed pause sample dispatch is represented"},
    {"global": "bike", "asset": "DATA\\SOUNDS\\BIKE.WAV", "event": "bike", "mechanic_reachable": False, "audio_implemented": False, "reason": "bike mechanic is not present in the shipped runtime"},
    {"global": "go", "asset": "DATA\\SOUNDS\\GO.WAV", "event": "go", "mechanic_reachable": False, "audio_implemented": False, "reason": "go prompt audio is not present in the shipped runtime"},
]
