"""Coherent full-component resource and online publication contract.

Extends the existing component tile caches. This host-side compiler contract
does not supply world results/pixels to a native sample and grants no native
readiness, sustainable cadence or live-world admission.
"""
import copy
import hashlib
import json

from bg_component_residency import OnlinePlaneCache


CONTEXT_FIELDS=('source_tick','actors','camera','underlay','layer_order','hud')
ACTOR_FIELDS=('token','model','model_generation','animation','frame','palette','remap','position','flip','alpha')
FENCES=('high_map','low_map','palette','scanline','hud')


def full_component_layout():
    # The same 768/768 cache and map layout as the passing fixed control.
    allocations=dict(high_chr=(0,49152),low_chr=(49152,61440),
                     high_map=(61440,63488),low_map=(63488,65536))
    spans=sorted(allocations.values())
    if spans[0][0]!=0 or spans[-1][1]!=65536 or any(a[1]!=b[0]for a,b in zip(spans,spans[1:])):
        raise AssertionError('COMPONENT_FULL_VRAM_ACCOUNTING')
    return dict(bg_mode=4,allocations=allocations,high_slots=768,low_slots=768,
                vram_bytes=65536,obj_chr_bytes=0,offset_map_alias='high_map',
                actors_owner='component_canvas',hud_owner='component_canvas',
                simulation_hz=200,presentation_sample_fields=2,
                measured_control_peak_nmi_clocks=50244,native_live_admitted=False)


def context_identity(snapshot):
    if set(snapshot)!=set(CONTEXT_FIELDS) or type(snapshot['source_tick'])is not int or not 0<=snapshot['source_tick']<=0xffffffff:
        raise ValueError('COMPONENT_SNAPSHOT_CONTEXT')
    for actor in snapshot['actors']:
        if set(actor)!=set(ACTOR_FIELDS):raise ValueError('COMPONENT_SNAPSHOT_ACTOR_CONTEXT')
    # All palette/remap, source pose, placement, camera, underlay, ordering and
    # drawn HUD state participate. A dirty-tile producer must use this key.
    return hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class OnlineComponentBundle:
    def __init__(self):
        self.layout=full_component_layout()
        self.high=OnlinePlaneCache(8,self.layout['high_slots'])
        self.low=OnlinePlaneCache(2,self.layout['low_slots'])
        self.pending=None;self.displayed=None

    def prepare(self,epoch,snapshot,high_tiles,low_tiles,palette,scanline,hud):
        if self.pending is not None:raise ValueError('COMPONENT_BUNDLE_PENDING')
        identity=context_identity(snapshot)
        # Every presentation member names the same captured authoritative state.
        for member in (palette,scanline,hud):
            if member.get('epoch')!=epoch or member.get('context')!=identity:
                raise ValueError('COMPONENT_BUNDLE_MIXED_SNAPSHOT')
        if hud.get('drawn')is not True:raise ValueError('COMPONENT_HUD_DRAW_REQUIRED')
        high=self.high.prepare(epoch,high_tiles)
        try:low=self.low.prepare(epoch,low_tiles)
        except Exception:
            self.high.pending=None
            raise
        self.pending=dict(epoch=epoch,context=identity,snapshot=copy.deepcopy(snapshot),
                          palette=copy.deepcopy(palette),scanline=copy.deepcopy(scanline),
                          hud=copy.deepcopy(hud),fences=set(),high=high,low=low)
        return dict(epoch=epoch,context=identity,high=high,low=low)

    def acknowledge(self,epoch,member,slot=None):
        if self.pending is None or self.pending['epoch']!=epoch:
            raise ValueError('COMPONENT_BUNDLE_FENCE_EPOCH')
        if member in ('high_chr','low_chr'):
            (self.high if member=='high_chr' else self.low).acknowledge(epoch,slot)
        elif member in FENCES:
            if member in self.pending['fences']:raise ValueError('COMPONENT_BUNDLE_DUPLICATE_FENCE')
            self.pending['fences'].add(member)
        else:raise ValueError('COMPONENT_BUNDLE_FENCE_MEMBER')

    def publish(self,epoch,*,safe_boundary):
        if not safe_boundary or self.pending is None or self.pending['epoch']!=epoch or self.pending['fences']!=set(FENCES) or not self.high.ready(epoch) or not self.low.ready(epoch):
            raise ValueError('COMPONENT_BUNDLE_NOT_READY')
        self.high.publish(epoch);self.low.publish(epoch)
        self.displayed=self.pending;self.pending=None
        return dict(epoch=epoch,context=self.displayed['context'],source_tick=self.displayed['snapshot']['source_tick'])
