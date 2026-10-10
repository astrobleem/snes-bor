"""Optimistic necessary CGRAM bandwidth bound across arbitrary row intervals.

Banks/geometry are relaxed into a pool only for this impossibility lower bound.
It cannot establish feasibility. One preloaded low byte per HBlank is allowed.
"""
import math

def transfer_interval(commits,hblanks,window_master_clocks=356,clocks_per_byte=8):
 """Optimistic commit-point capacity, granting one low preload per HBlank.

 First-to-last points occupy (N-1) gaps, rather than N byte durations.
 Address writes and every other user of the transfer window are omitted.
 """
 if commits<0 or hblanks<1 or window_master_clocks<=0 or clocks_per_byte<=0:raise ValueError('PALETTE_INTERVAL_BUDGET')
 peak=math.ceil(commits/hblanks)
 capacity=1+(window_master_clocks-1)//(2*clocks_per_byte)
 needed=2*commits-min(commits,hblanks)
 available=(1+(window_master_clocks-1)//clocks_per_byte)*hblanks
 return dict(minimum_new_color_commits=commits,hblanks=hblanks,
  minimum_window_cgram_data_bytes=needed,maximum_window_data_bytes=available,
  byte_deficit=max(0,needed-available),minimum_peak_data_bytes=math.ceil(needed/hblanks),
  minimum_peak_data_master_clocks=math.ceil(needed/hblanks)*clocks_per_byte,
  minimum_peak_color_commits=peak,minimum_peak_commit_span_master_clocks=max(0,2*(peak-1)*clocks_per_byte),
  maximum_color_commits_per_hblank=capacity,commit_deficit=commits-capacity*hblanks)

def interval_bound(line_colors,slots=120,window_master_clocks=356,clocks_per_byte=8):
 if slots<=0 or window_master_clocks<=0 or clocks_per_byte<=0:raise ValueError('PALETTE_INTERVAL_BUDGET')
 worst=None;peak=0;best_deficit=-math.inf
 for start in range(len(line_colors)):
  union=set(line_colors[start])
  for end in range(start+1,len(line_colors)):
   union.update(line_colors[end]);required=max(0,len(union)-slots);hblanks=end-start;budget=transfer_interval(required,hblanks,window_master_clocks,clocks_per_byte);deficit=budget['commit_deficit'];average_ceiling=budget['minimum_peak_color_commits']
   if deficit>best_deficit or deficit==best_deficit and average_ceiling>peak:
    peak=average_ceiling;best_deficit=deficit;worst=dict(first_line=start,last_line=end,distinct_colors=len(union),resident_capacity=slots,**budget)
 return dict(status='CGRAM_DATA_WINDOW_INFEASIBLE'if best_deficit>0 else'LOWER_BOUND_DOES_NOT_REJECT',worst_interval=worst,available_master_clocks_per_line=window_master_clocks,minimum_master_clocks_per_byte=clocks_per_byte,preloaded_low_byte_latch_allowed=True,low_preload_per_hblank_allowed=True,window_budget_is_first_to_last_commit_span=True,addresses_setup_and_contention_excluded=True,bank_assignment_relaxed_for_lower_bound=True,feasibility_proven=False)
