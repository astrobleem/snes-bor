from source_queue_concurrency import explore


def record(kind,at=0,group=(0,0)):
    return dict(kind=kind,at=at,group=list(group))


def test_wait_does_not_break_source_dispatch():
    r=explore([record('spawn'),record('wait'),record('spawn')])
    assert r['peak_enemy_count']==2
    assert any(c['queue_indices']==[0,2]for c in r['combinations'])
    assert r['queue_completion_admitted']


def test_wait_blocks_camera_arrival_until_enemy_retirement():
    r=explore([record('spawn'),record('wait'),record('spawn',10)])
    assert r['peak_enemy_count']==1
    assert not any(c['queue_indices']==[0,2]for c in r['combinations'])


def test_group_throttles_before_following_wait():
    r=explore([record('group',group=(1,3)),*[record('spawn')for _ in range(5)],record('wait')])
    assert r['peak_enemy_count']==3
    assert r['queue_completion_admitted']
    assert any(c['queue_indices']==[1,2,3]for c in r['combinations'])
    # A witness must include the actual births, even if its peak was inside
    # a dispatch call rather than at the following foreground boundary.
    w=next(w for w in r['peak_witnesses']if w['queue_indices']==[1,2,3])
    assert w['steps'][-1]['consumed_queue_indices']==[0,1,2,3]


def test_empty_at_is_consumed_without_an_enemy():
    r=explore([record('empty'),record('spawn')])
    assert r['peak_enemy_count']==1
    assert r['queue_completion_admitted']
