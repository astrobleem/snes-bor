# Ordinary actor raster palettes

Lossless ordinary actor raster reuse is now demonstrated on the native SNES
fixture. He_ManB freespecial4 frame 6 retains its source canvas, opaque black,
transparency and visible RGB555 identities in one fixed OBJ bank. Every piece
keeps that bank through its entire rectangle. The generic literal compiler
rejects nonzero alpha and checks combined demand when actors share a bank.

The native run uses 33 OAM entries, five sprites and ten tile slivers at peak.
Physical scheduling preloads the initial palette and writes at most two words
per later row, four bytes, with a 16-master-clock commit span. All four complete
observed fields match the compiled descriptors. There are 56 complete CGRAM
shadow checks with zero byte faults, zero unsafe commits, zero viewport pixel
mismatches and no OBJ overflow. The actual production NMI service executes with
a 2814-byte queue; its VRAM contents and saved context match, and it completes
within VBlank. Foreground waits for each IRQ; source VM and SA1 workers are not
executed. This is an isolated pose on a black matte, not gameplay admission.

All seven player frames, twelve KnightBot attack1 frames and twelve ShockBall
idle frames independently admit exact offline one-bank schedules. Their logical
peak writes are eight, one and five respectively. These heuristic write counts
are not minima. A whole-frame ShockBall palette can fit statically; raster is
not a required capability for that actor merely because this experiment uses it.

The critical authored KnightBot/ShockBall/player/effect context has a validated
relaxed bound of 17 writes when ordinary colors are required only on their
visible rows, rather than statically pinned across the entire effect interval.
The measured interval is 125 through 139. This bound pools banks within their
eligibility classes and relaxes integer controls and geometry; it is not a
combined schedule or hardware feasibility proof.

The critical 15-row interval also has an integer two-class cache witness at
21 writes. Compiling its two color-window descriptors and selected math modes
replays 2064 visible source pixels exactly. Banks remain pooled within classes;
fixed OAM banks and physical transfers are still unproven. The full-frame
integer search is a separate experiment.

Further fixed-piece, source-word-mask and interval-residency searches remain
bounded UNKNOWN. They do not establish universal raster infeasibility. Full
authored peak HBreath raster timing, production ownership, animation binding,
concurrent scene reachability and MOTU Demo completion remain unresolved.
No color reduction or source resizing has been applied. Production presentation
and bank zero are unchanged. The width guard remains clean at 9825 labels.
