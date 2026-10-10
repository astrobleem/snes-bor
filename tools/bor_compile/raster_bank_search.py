"""Bounded fixed-bank CSP candidate search with exact row-set verification."""
import time

def assign(pieces,banks,time_limit=20,node_limit=100000,adjacent_write_budget=None):
 banks=tuple(banks)
 if not banks or len(set(banks))!=len(banks)or any(b not in range(8)for b in banks):raise ValueError('INVALID_BANKS')
 colors=sorted({c for p in pieces for cs in p['rows'].values()for c in cs});ids={c:i for i,c in enumerate(colors)}
 rows=[[(y,sum(1<<ids[c]for c in set(cs)))for y,cs in p['rows'].items()if cs]for p in pieces];allowed=[set(p.get('allowed_banks',banks))for p in pieces]
 if any(not a or not a.issubset(set(banks))for a in allowed):raise ValueError('INVALID_PIECE_BANKS')
 heights=sorted({y for p in rows for y,_ in p});state={b:{y:0 for y in heights}for b in banks};lower={y:0 for y in range(1,max(heights,default=0)+2)};usage={b:0 for b in banks};assignment=[None]*len(pieces);start=time.monotonic();nodes=0;limited=False;symmetric=all(a==set(banks)for a in allowed)
 def options(i):
  result=[];first_unused=False
  for b in banks:
   if b not in allowed[i]:continue
   if symmetric and usage[b]==0:
    if first_unused:continue
    first_unused=True
   changes=[];new=0;peak=0
   for y,mask in rows[i]:
    before=state[b][y];after=before|mask;n=after.bit_count()
    if n>15:break
    changes.append((y,before,after));new+=n-before.bit_count();peak=max(peak,n)
   else:
    changed={y:after for y,_,after in changes};adjust=[]
    for y in sorted({yy for yy in changed for yy in (yy,yy+1)if yy>0}):
     old=max(0,(state[b].get(y-1,0)|state[b].get(y,0)).bit_count()-15)
     now=max(0,(changed.get(y-1,state[b].get(y-1,0))|changed.get(y,state[b].get(y,0))).bit_count()-15)
     total=lower[y]+now-old
     if adjacent_write_budget is not None and total>adjacent_write_budget:break
     adjust.append((y,lower[y],total))
    else:result.append((new,peak,b,changes,adjust,max((v[2]for v in adjust),default=0),sum(v[2]-v[1]for v in adjust)))
  return sorted(result,key=lambda v:(v[5],v[6],v[0],v[1],v[2]))
 def visit(remaining):
  nonlocal nodes,limited
  nodes+=1
  if nodes>node_limit or time.monotonic()-start>time_limit:limited=True;return False
  if not remaining:return True
  selected=None;choices=None;priority=None
  for i in remaining:
   candidates=options(i)
   if not candidates:return False
   rank=(len(candidates),-max((mask.bit_count()for _,mask in rows[i]),default=0),-len(rows[i]))
   if priority is None or rank<priority:selected,choices,priority=i,candidates,rank
  rest=[i for i in remaining if i!=selected]
  for _,_,b,changes,adjust,_,_ in choices:
   assignment[selected]=b;usage[b]+=1
   for y,_,after in changes:state[b][y]=after
   for y,_,after in adjust:lower[y]=after
   if visit(rest):return True
   for y,before,_ in changes:state[b][y]=before
   for y,before,_ in adjust:lower[y]=before
   usage[b]-=1;assignment[selected]=None
   if limited:return False
  return False
 found=visit(list(range(len(pieces))));elapsed=time.monotonic()-start
 if not found:return dict(status='BOUNDED_BANK_SEARCH_LIMIT',search_nodes=nodes,search_seconds=elapsed,search_limit_reached=limited,scope='No candidate found by bounded search. This is not hardware infeasibility.')
 for y in heights:
  for bank in banks:
   actual={c for p,b in zip(pieces,assignment)if b==bank for c in p['rows'].get(y,[])}
   if len(actual)>15:raise AssertionError('BANK_SEARCH_INVALID_ROW_UNION')
 if any(b not in a for b,a in zip(assignment,allowed)):raise AssertionError('BANK_SEARCH_INVALID_ELIGIBILITY')
 return dict(status='FIXED_BANK_ASSIGNMENT_PROVEN',assignment=assignment,search_nodes=nodes,search_seconds=elapsed,adjacent_write_budget=adjacent_write_budget,peak_adjacent_bank_write_lower_bound=max(lower.values(),default=0),method='bounded CSP with exact integer row unions')
