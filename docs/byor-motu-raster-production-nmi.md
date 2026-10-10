# Raster OBJ with production NMI services

The controlled HBreath peak frame passes with the original production
`nmi_handler`, `StageWater_Nmi` and `Core_Nmi_Play` instructions executing
inside the private native fixture. The SA-1 cartridge header and MMC mapping
remain intact. The foreground runs the bounded WRAM/stack/width stress loop.
The real DMA queue service transfers 2,814 bytes to VRAM through channel 7;
the raster executor subsequently restores that channel's CGRAM configuration.
Each NMI restores only the 256-byte OBJ half of CGRAM, preserving BG words.

Four complete fields preserve all 57,344 RGB555 viewport pixels, all palette
packet words and destinations, and all OAM bytes. No OBJ overflow or unsafe
CGRAM high-byte commit occurs. First commits range from master clocks 1104
through 1144; the maximum first-to-last span is 216 clocks. Four paired NMI
context checks and 937 IRQ checks have zero faults. The maximum NMI
entry-to-return cost is 37,940 master clocks and every observed NMI returns
within VBlank.

Queue verification runs at each completed NMI return: it checks every uploaded
VRAM byte against the deterministic payload and checks the descriptor's active
flag has cleared. Pausing at a frame boundary can interrupt NMI while the next
descriptor is active; that transient state must not substitute for the
completion observation. The observer retains those completion checks, timing
and DMA requests alongside the CGRAM trace.

The original `Core_Dma_CheckLength` rejects a cumulative size greater than or
equal to `$0B00` (2,816 bytes). The 2,814-byte fixture is below that cap, but
injects its descriptor directly and does not prove registration. The earlier
4,096-byte transfer is explicitly **SERVICE-PATH STRESS PROOF**: it bypasses
the registration cap and must not be reported as production upload admission.

This fixture initializes private WRAM and PPU shadows. Water, streaming and
frontpanel services have no pending work, and active audio, the SA-1 gameplay
worker, the source VM and production cold boot are not proven. It establishes
one real NMI/queue contention case, not a gameplay resource lease. The source
SCREEN alpha result remains exact only on the controlled constant black
underlay. Authored backgrounds and concurrent actor palette schedules remain
open. No color reduction is applied.

The 3,424-byte peak-frame CHR image exceeds the ordinary single-field queue
cap. Animated admission therefore needs measured prefetch/chunking and VRAM
lifecycle handling; this proof does not silently admit a late frame upload.

Evidence: `docs/receipts/byor-motu-raster-production-nmi.json` and the bounded
native observer/screenshot under
`out/byor-motu-controlled-black-real-nmi-2814-native/`.
