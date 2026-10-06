import numpy as np
from raster_palette_first_use import fold


def test_prefetch_moves_to_initial_but_later_reuse_remains():
    indices=np.full((224,256),4,dtype=np.uint8)
    indices[100:110]=59;indices[150:]=59
    initial=[0]*236;initial[0]=123
    trace=[dict(scanline=y,updates=[]) for y in range(224)]
    trace[2]['updates']=[dict(slot=56,color=456)]
    trace[150]['updates']=[dict(slot=56,color=789)]
    report,new,proof=fold(dict(trace=trace),initial,indices)
    assert new[55]==456 and new[0]==123
    assert report['trace'][2]['updates']==[]
    assert report['trace'][150]['updates']==[dict(slot=56,color=789)]
    assert proof['pixel_palette_identity_replayed'] and proof['raster_events_removed']==1


def test_slot_used_on_first_line_cannot_move_future_color_to_initial():
    indices=np.full((224,256),59,dtype=np.uint8)
    initial=[0]*236;initial[55]=123
    trace=[dict(scanline=y,updates=[]) for y in range(224)]
    trace[2]['updates']=[dict(slot=56,color=456)]
    report,new,proof=fold(dict(trace=trace),initial,indices)
    assert new[55]==123 and report['trace'][2]['updates']
