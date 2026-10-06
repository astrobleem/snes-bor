from source_transfer_milp import solve
from bg_component_deadlines import cost
from source_residency_permutation import order_slots
import numpy as np


def fixture():
    return dict(source_frame_start_fields=[0,1,2],transitions=[],jobs=[
        dict(address=4096,bytes=64,release=1,deadline=2),
        dict(address=4160,bytes=64,release=1,deadline=2)])


def test_contiguous_jobs_share_one_setup():
    fields,result=solve(fixture(),budget=1240,setup=216,allowance=0,seconds=5)
    assert fields is not None
    assert sum(len(f['jobs']) for f in fields)==2
    assert any(len(f['jobs'])==2 for f in fields)
    assert all(cost(f['jobs'],216)<=1240 for f in fields)
    assert all(1<=f['field']<=2 for f in fields if f['jobs'])


def test_single_packet_cannot_fit():
    fields,result=solve(fixture(),budget=727,setup=216,allowance=0,seconds=5)
    assert fields is None and result['status']==2


def test_map_publication_is_required_after_failed_greedy_prefix():
    plan=fixture();plan['fields']=[dict(field=0,mandatory=[])]
    plan['transitions']=[dict(to_frame=2,tilemap_transfers=[dict(vram_byte_address=61440,bytes=1024)])]
    fields,result=solve(plan,budget=1240,setup=216,allowance=0,seconds=5)
    assert fields is None and result['status']==2


def test_permutation_clusters_matching_refill_lifetimes():
    slots=[0,1,2,3];masks={0:[0,1,0],1:[0,0,1],2:[0,1,0],3:[0,0,1]}
    order=order_slots(slots,masks,np.ones(3))
    assert sorted(order)==slots
    assert abs(order.index(0)-order.index(2))==1
    assert abs(order.index(1)-order.index(3))==1


def test_long_dma_refresh_is_charged_without_changing_default_cost():
    packet=[dict(address=4096,bytes=5120)]
    assert cost(packet,192)==41152
    assert cost(packet,192,40)==42390
