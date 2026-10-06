"""Bounded offline VBlank assignment with explicit contiguous packet costs.

A solver timeout is not a hardware limit. Every solution is independently
replayed against the source tile identities before it becomes a candidate.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from bg_component_deadlines import cost, replay


def solve(plan, budget=50000, setup=216, allowance=9000, seconds=90):
    jobs=plan['jobs'];last=plan['source_frame_start_fields'][-1]
    # A failed greedy attempt may stop before the last transition. Its field
    # list is not the authority for required map publication.
    mandatory={plan['source_frame_start_fields'][t['to_frame']]:[
        dict(address=v['vram_byte_address'],bytes=v['bytes'],kind='tilemap')
        for v in t['tilemap_transfers']] for t in plan['transitions']}
    assignments=[];by_job=[[] for _ in jobs];by_field=[{} for _ in range(last+1)]
    for i,j in enumerate(jobs):
        for f in range(j['release'],j['deadline']+1):
            v=len(assignments);assignments.append((i,f));by_job[i].append(v)
            by_field[f].setdefault(j['address'],[]).append(v)
    n=len(assignments);starts=[];constraints=[];lower=[];upper=[]
    def row(values,lo=-np.inf,hi=np.inf):
        constraints.append(values);lower.append(lo);upper.append(hi)
    for variables in by_job:row([(v,1) for v in variables],1,1)
    for f,addresses in enumerate(by_field):
        fixed=mandatory.get(f,[])
        fixed_addresses={j['address']:j['bytes'] for j in fixed}
        ends={a+jobs[assignments[vs[0]][0]]['bytes']:a for a,vs in addresses.items()}
        ends.update({a+b:a for a,b in fixed_addresses.items()})
        coefficients=[(v,jobs[i]['bytes']*8) for v,(i,t) in enumerate(assignments) if t==f]
        for a,vs in addresses.items():
            row([(v,1) for v in vs],hi=1)
            previous=ends.get(a)
            if previous in fixed_addresses:continue
            y=n+len(starts);starts.append((f,a));coefficients.append((y,setup))
            row([(y,1),*[(v,-1) for v in vs],*[(v,1) for v in addresses.get(previous,[])]],lo=0)
        fixed_runs=0
        for a in fixed_addresses:
            previous=ends.get(a)
            if previous in fixed_addresses:continue
            if previous in addresses:
                y=n+len(starts);starts.append((f,a));coefficients.append((y,setup))
                row([(y,1),*[(v,1) for v in addresses[previous]]],lo=1)
            else:fixed_runs+=1
        if f:
            row(coefficients,hi=budget-allowance-sum(j['bytes']*8 for j in fixed)-fixed_runs*setup)
    rr=[];cc=[];vv=[]
    for r,values in enumerate(constraints):
        for c,v in values:rr.append(r);cc.append(c);vv.append(v)
    total=n+len(starts)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(constraints),total)).tocsc()
    objective=np.zeros(total);objective[n:]=1
    # Prefer early completion among solutions with the same packet count.
    for v,(i,f) in enumerate(assignments):objective[v]=f*1e-6
    result=milp(objective,integrality=np.r_[np.ones(n),np.zeros(len(starts))],
        bounds=Bounds(np.zeros(total),np.ones(total)),constraints=LinearConstraint(matrix,lower,upper),
        options=dict(time_limit=seconds,mip_rel_gap=.02))
    if result.x is None:return None,dict(status=int(result.status),message=result.message,variables=total)
    selected=[[] for _ in range(last+1)]
    for v,(i,f) in enumerate(assignments):
        if result.x[v]>.5:selected[f].append(jobs[i])
    fields=[dict(field=f,jobs=js,mandatory=mandatory.get(f,[]),
        estimated_master_clocks=cost(js+mandatory.get(f,[]),setup)+(allowance if f else 0),
        missed_deadline_jobs=[],mandatory_budget_exceeded=False) for f,js in enumerate(selected)]
    if any(r['field'] and r['estimated_master_clocks']>budget for r in fields):
        raise ValueError('MILP_COST_REPLAY_DISAGREEMENT')
    return fields,dict(status=int(result.status),message=result.message,variables=total,
        mip_gap=float(result.mip_gap),optimal=bool(result.status==0))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--residency',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--window-master-clocks',type=int,default=50000)
    p.add_argument('--packet-setup-master-clocks',type=int,default=216)
    p.add_argument('--palette-allowance-master-clocks',type=int,default=9000)
    p.add_argument('--seconds',type=float,default=90);a=p.parse_args()
    plan=json.loads((a.residency/'report.json').read_text())
    fields,solver=solve(plan,a.window_master_clocks,a.packet_setup_master_clocks,a.palette_allowance_master_clocks,a.seconds)
    identity=False
    if fields is not None:
        maps={n:[] for n in ('high','low')}
        offset=plan['allocation']['high_chr'][0]//64
        for n in maps:
            for i in range(len(plan['source_frame_start_fields'])):
                m=np.fromfile(a.residency/('%02d-%s.map'%(i,n)),dtype='<u2').reshape(32,32)[:28]&0x3ff
                if n=='high':m=m-offset
                maps[n].append(m)
        identity=replay(fields,plan,maps,plan['source_frame_start_fields'])
    report=dict(schema='BYOR_VBLANK_MILP_DEADLINES_V1',
        status='OFFLINE_DEADLINE_CANDIDATE' if identity else 'BOUNDED_SOLVER_NO_CANDIDATE',
        solver=solver,fields=fields or [],source_frame_start_fields=plan['source_frame_start_fields'],
        resident_identity_replay=identity,window_master_clocks=a.window_master_clocks,
        packet_setup_master_clocks=a.packet_setup_master_clocks,palette_allowance_master_clocks=a.palette_allowance_master_clocks,
        no_color_reduction=True,native_admitted=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='fields'}))


if __name__=='__main__':main()
