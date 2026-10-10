"""Optimistic necessary CGRAM bandwidth bound across arbitrary row intervals.

Banks/geometry are relaxed into a pool only for this impossibility lower bound.
It cannot establish feasibility. One preloaded low-byte latch is allowed.
"""
import math

def interval_bound(line_colors,slots=120,window_master_clocks=356,clocks_per_byte=8):
 if slots<=0 or window_master_clocks<=0 or clocks_per_byte<=0:raise ValueError('PALETTE_INTERVAL_BUDGET')
 worst=None;peak=0;best_deficit=-1
 for start in range(len(line_colors)):
  union=set(line_colors[start])
  for end in range(start+1,len(line_colors)):
   union.update(line_colors[end]);required=max(0,len(union)-slots);hblanks=end-start;bytes_needed=max(0,required*2-1);available=(window_master_clocks//clocks_per_byte)*hblanks;deficit=bytes_needed-available;average_ceiling=math.ceil(bytes_needed/hblanks)
   if deficit>best_deficit or deficit==best_deficit and average_ceiling>peak:
    peak=average_ceiling;best_deficit=deficit;worst=dict(first_line=start,last_line=end,distinct_colors=len(union),resident_capacity=slots,minimum_new_color_commits=required,hblanks=hblanks,minimum_window_cgram_data_bytes=bytes_needed,maximum_window_data_bytes=available,byte_deficit=max(0,deficit),minimum_peak_data_bytes=average_ceiling,minimum_peak_data_master_clocks=average_ceiling*clocks_per_byte)
 return dict(status='CGRAM_DATA_WINDOW_INFEASIBLE'if best_deficit>0 else'LOWER_BOUND_DOES_NOT_REJECT',worst_interval=worst,available_master_clocks_per_line=window_master_clocks,minimum_master_clocks_per_byte=clocks_per_byte,preloaded_low_byte_latch_allowed=True,addresses_setup_and_contention_excluded=True,bank_assignment_relaxed_for_lower_bound=True,feasibility_proven=False)
