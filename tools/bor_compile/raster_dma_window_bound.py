"""Necessary DMA-only high-byte commit bounds for the SNES CGRAM window.

The window and alignment are explicit inputs, grounded separately in native
observers and pinned PPU/DMA source. These are upper bounds, not executable
transport budgets. CPU-assisted transfers are outside this mechanism family.
"""


def minimum_commit_span(opaque_words):
    if type(opaque_words)is not int or not 0<=opaque_words<=120:raise ValueError('DMA_WINDOW_WORD_DOMAIN')
    if not opaque_words:return 0
    # Fifteen opaque entries per bank. Crossing a bank either transfers its
    # transparent entry (16 clocks) or starts a new range (24 clocks).
    return 16*(opaque_words+(opaque_words-1)//15)-16


def aligned_window(line_clocks=1364,late_start=1096,early_end=88,alignment=8):
    if not 0<early_end<late_start<line_clocks or alignment<1:raise ValueError('DMA_WINDOW_CLOCK_DOMAIN')
    rows=[]
    for phase in range(alignment):
        first=late_start+(phase-late_start)%alignment
        maximum_span=((line_clocks+early_end-1-first)//alignment)*alignment
        maximum_words=max(n for n in range(121)if minimum_commit_span(n)<=maximum_span)
        rows.append(dict(local_high_byte_phase=phase,earliest_safe_high_byte=first,
                         maximum_aligned_commit_span=maximum_span,maximum_opaque_writes=maximum_words))
    return dict(schema='BYOR_DMA_ONLY_CGRAM_ALIGNMENT_NECESSARY_BOUND_V1',scanline_master_clocks=line_clocks,
        safe_late_high_byte_start=late_start,safe_early_high_byte_end_exclusive=early_end,
        dma_alignment_master_clocks=alignment,phases=rows,
        phase_advance_per_scanline=(-line_clocks)%alignment,
        native_transport_admitted=False,cpu_assisted_writes_not_modeled=True,
        setup_irq_and_control_contention_relaxed=True,universal_raster_rejected=False)


if __name__=='__main__':
    import json
    print(json.dumps(aligned_window(),indent=2))
