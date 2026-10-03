; Include in bank0; explicit long-call bridges preserve native return flags.
StageFp_HostMul:
    jsr Core_Math_Mul
    rtl
StageFp_HostCacheInit:
    jsr Core_StreamCacheFp_Init
    rtl
StageFp_HostHasFree:
    jsr Core_Dma_HasFreeSlot
    rtl
StageFp_HostEnqueue:
    jsr Core_Dma_Enqueue
    rtl
