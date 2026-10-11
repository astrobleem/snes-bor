"""Conservative source-pixel deadlines for observed native OBJ controls.

The isolated viewport starts on physical scanline one. Controls for logical
row y are written on physical row y, after the preceding visible row's OBJ
pixels and before the next row begins. This checks register timing only;
authored palette DMA, alpha arithmetic and gameplay admission stay separate.
"""
import argparse,hashlib,json
from pathlib import Path
from raster_obj_compact import unpack
from raster_slot_greedy import demand


def verify(source,proof,observer):
    demand(source)
    if not source.get('scanline_math_controls_source_bound'):
        raise ValueError('CONTROL_DEADLINE_SOURCE_BOUND_REQUIRED')
    frames=proof.get('control_traffic_fields',[])
    if proof.get('status')!='PASS'or len(frames)<2 or not proof.get('resources',{}).get('controls_before_palette'):
        raise ValueError('CONTROL_DEADLINE_NATIVE_PREFIX_PROOF_REQUIRED')
    last_x=[-1]*len(source['trace'])
    for piece,mask in zip(source['pieces'],source['piece_pixel_masks']):
        if piece['bank']<4:continue
        image=unpack(mask)
        for ly,row in enumerate(image):
            xs=row.nonzero()[0]
            if len(xs):
                y=piece['y']+ly
                last_x[y]=max(last_x[y],piece['x']+int(xs[-1]))
    expected={int(y):rows for y,rows in proof['resources']['control_traffic_rows'].items()}
    checks=[];margins=[]
    for frame in frames:
        seen={}
        for f,y,line,h,address,value in observer['register_writes']:
            if f!=frame:continue
            if not 0<=y<len(last_x) or line!=y:
                raise ValueError('CONTROL_DEADLINE_PHYSICAL_ROW_ALIGNMENT')
            seen.setdefault(y,[]).append([address,value])
            previous_pixel=last_x[y-1]if y else -1
            previous_complete=88+4*(previous_pixel+1)+8 if previous_pixel>=0 else 0
            next_visible=1364+88
            if h<previous_complete or h+8>=next_visible:
                raise ValueError('CONTROL_DEADLINE_VISIBLE_PIXEL_CONFLICT')
            margins.append(h-previous_complete if previous_pixel>=0 else next_visible-h-8)
            checks.append(dict(frame=f,logical_target_row=y,physical_write_row=line,hclock=h,
                address=address,value=value,previous_math_eligible_rightmost_pixel=previous_pixel,
                previous_pixel_complete_with_guard=previous_complete))
        if seen!=expected:raise ValueError('CONTROL_DEADLINE_REGISTER_IDENTITY')
    if not checks:raise ValueError('CONTROL_DEADLINE_NO_OBSERVED_WRITES')
    return dict(schema='BYOR_SOURCE_CONTROL_DEADLINES_V1',status='SOURCE_CONTROL_DEADLINES_PROVEN',
        complete_observed_fields=frames,observed_writes=len(checks),minimum_guarded_margin=min(margins),
        observed_hclock_range=[min(c['hclock']for c in checks),max(c['hclock']for c in checks)],
        source_rgb555_sha256=source['source_rgb555_sha256'],viewport_to_physical_scanline_offset=1,
        scanline_master_clocks=1364,visible_pixel_start_hclock=88,write_completion_guard_master_clocks=8,
        conservative_all_visible_obj_banks_4_through_7=True,native_authored_palette_transfer_proven=False,
        native_authored_alpha_rendering_proven=False,production_runtime_admitted=False,no_color_reduction=True,
        checks=checks)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('schedule','proof','observer','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();proof=json.loads(a.proof.read_text())
    if proof.get('control_traffic_source_file_sha256')!=hashlib.sha256(a.schedule.read_bytes()).hexdigest():
        raise ValueError('CONTROL_DEADLINE_SOURCE_FILE_IDENTITY')
    result=verify(json.loads(a.schedule.read_text()),proof,json.loads(a.observer.read_text()))
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='checks'}))


if __name__=='__main__':main()
