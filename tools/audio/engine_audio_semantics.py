"""Source-backed OpenBOR global sample table for the target legacy engine."""

ENGINE_REVISION = "bcec7cb765eebec555c74aac64a23aa73f1cfe21"
ENGINE_SOURCE = "engine/openbor.c:load_special_sounds"

ENGINE_GLOBAL_AUDIO = [
    {"global": "beat", "asset": "DATA\\SOUNDS\\BEAT1.WAV", "event": "landed-hit", "reachable": True, "reason": "default attack hitsound and accepted attack playback are implemented"},
    {"global": "block", "asset": "DATA\\SOUNDS\\BLOCK.WAV", "event": "blocked-attack", "reachable": False, "reason": "blocking mechanic is not present in the current SNES runtime"},
    {"global": "fall", "asset": "DATA\\SOUNDS\\FALL.WAV", "event": "fall", "reachable": False, "reason": "fall sound dispatch is not present in the current SNES runtime"},
    {"global": "get", "asset": "DATA\\SOUNDS\\GET.WAV", "event": "get-up", "reachable": False, "reason": "get-up sound dispatch is not present in the current SNES runtime"},
    {"global": "get_2", "asset": "DATA\\SOUNDS\\MONEY.WAV", "event": "money-pickup", "reachable": False, "reason": "generic pickup audio dispatch is not implemented"},
    {"global": "jump", "asset": "DATA\\SOUNDS\\JUMP.WAV", "event": "jump", "reachable": False, "reason": "jump sound dispatch is not implemented"},
    {"global": "indirect", "asset": "DATA\\SOUNDS\\INDIRECT.WAV", "event": "indirect-attack", "reachable": False, "reason": "projectile sound dispatch is not implemented"},
    {"global": "punch", "asset": "DATA\\SOUNDS\\PUNCH.WAV", "event": "attack-swing", "reachable": False, "reason": "generic frame/attack sound dispatch is not implemented"},
    {"global": "one_up", "asset": "DATA\\SOUNDS\\1UP.WAV", "event": "one-up", "reachable": False, "reason": "one-up state audio is not implemented"},
    {"global": "time_over", "asset": "DATA\\SOUNDS\\TIMEOVER.WAV", "event": "time-over", "reachable": False, "reason": "time-over state audio is not implemented"},
    {"global": "beep", "asset": "DATA\\SOUNDS\\BEEP.WAV", "event": "ui-beep", "reachable": False, "reason": "no authored reachable UI beep event is represented"},
    {"global": "beep_2", "asset": "DATA\\SOUNDS\\BEEP2.WAV", "event": "ui-beep-secondary", "reachable": False, "reason": "no authored reachable UI beep event is represented"},
    {"global": "pause", "asset": "DATA\\SOUNDS\\PAUSE.WAV", "event": "pause", "reachable": False, "reason": "no source-backed pause sample dispatch is represented"},
    {"global": "bike", "asset": "DATA\\SOUNDS\\BIKE.WAV", "event": "bike", "reachable": False, "reason": "bike mechanic is not present in the shipped runtime"},
    {"global": "go", "asset": "DATA\\SOUNDS\\GO.WAV", "event": "go", "reachable": False, "reason": "go prompt audio is not present in the shipped runtime"},
]
