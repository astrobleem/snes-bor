# CPU window descriptors after prepared palette DMA

The every-line window HDMA failure leaves CPU window writes outside the CGRAM
commit window open. A bounded native experiment now runs prepared two-range
CGRAM DMA, followed by the compiled seven-byte window/mode descriptor. Two
16-bit stores publish four bounds; three byte stores publish selection, logic
and math mode. Handler and descriptor reads use FastROM aliases. Palette DMA
owns channels 5..7 and the 73-row dummy APU HDMA pattern owns channel 0.

Timer 155 fails with 669 unsafe high commits; timer 161 still fails with two.
At timer **162**, all **447 packets / 8,493 high-byte commits** on lines 75..223
are safe over three fields. The high-commit span is **320 master clocks**.
All destination/range traces match and final owned CGRAM words are exactly
`0x1111`. There are 111 low-byte writes during the active window; the measured
high-commit rule and the independent final CGRAM comparison are decisive here.

All **672** CPU descriptors are observed. Their last write occurs no later than
**H=442** of the next line. This does not yet prove they precede the first
affected source pixel. The descriptor row cursor and CPU registers belong to
this isolated fixture; production interrupt context preservation, row ownership,
source pixels, alpha and gameplay leases are not bound. Early rows with active
audio HDMA are outside the palette packet admission interval.

This proves an isolated transfer mechanism survives the earlier HDMA conflict;
it does not certify a HBreath palette schedule. Fixed-bank physical allocation,
first affected-pixel deadlines and the actual production interrupt/NMI costs
remain required. The [receipt](receipts/byor-motu-cpu-window-packet-timing.json)
retains every bounded trial and its exact scope. No color reduction or PCM copies.

## Fixed positive-window controls

With both noninverted windows enabled and their OR logic fixed at boot, the
dynamic descriptor needs only four bounds and one math-mode byte. Empty windows
use left=255, right=0. At timer 162 this five-byte route again observes 447
packets, 8,493 safe high commits, a 320-clock commit span and exact final owned
CGRAM words. All 672 descriptors finish by H=334, improving the measured
deadline by 108 clocks. This is a restricted mask family; the same source-pixel
deadline and production interrupt-context nonclaims still apply.

The stronger shared-mode solver now includes mode-subset cover inequalities.
These prevent fractional mode mixtures from obtaining incompatible operands
without sufficient resident coverage. Both the strengthened LP and the
23-write integral-control solve reached their 180-second limits without a
candidate. Neither result supplies an infeasibility verdict or a lower bound.
The general 600-second solve and restricted positive-window 180-second solve
also timed out. They remain open, rather than hardware rejections.
