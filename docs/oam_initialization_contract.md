# OBJ initialization and wrap-safe hiding prerequisite

The pre-fix live S5 trace observed OBSEL base 0 / mode 0 despite the `$C2`
shadow. Reset's indexed PPU clearing writes zero to `$2101`; the production
NMI does not consume `Nmi_ObjSel`. The source-only search for literal `$2101`
therefore did not mean hardware was never written at all. What was missing
was committing the intended configuration after reset's zero writes.

`Core_Oam_Init`, after `Core_Nmi_Init` and under forced blank, now writes
the same A8 `$C2` value to the shadow and explicit bank-zero `$002101` once.
Mode 6 selects 16x32 SMALL / 32x64 LARGE; base field 2 selects VRAM word
`$4000` (byte `$8000`). Name-select field 0 gives a `$1000`-word alternate
table displacement. Existing four-column, eight-row OBJ allocation matches
the LARGE footprint; authored 32x48 raster occupies six rows plus padding.

Hidden state is X=-64 (low `$C0`, X-high=1), Y=224 (`$E0`), SMALL (size=0).
Expanded high byte is 1; four hidden sprites pack as `$55`.
SMALL spans Y224..255 without wrap into the 224-line image. X=-64 additionally
excludes even 64-wide objects from evaluation, unlike X=-256's PPU special
case. Active writers overwrite both high bits. A single request helper covers
death/blink, player-out and missing-portrait paths without changing actors.

Three defects contributed to retired ghosts: `$F0`+64 wraps 48 rows; expanded
high clearing used packed-byte counts rather than sprite counts; active-only
DMA omitted retired slots (including entirely empty frames). ClearAll now
writes exact low/high extents without the old overlapping word stores. The
existing queued DMA transfers the high-water extent so retired slots reach
hardware. Full upload remains 512 bytes at OAM word0 +32 at word`$100`, using
the unchanged channel7 consumer. No queue/DMA architecture was replaced.

Focused evidence: `out/oam_contract_opxkg_m1/proof.json`, screenshots phases
19 (ordinary accepted player),21 (LARGE),23 (hidden),31 (SMALL),33/36 (hidden).
The fixture redirects a normal bank0 call into the real ClearAll and suppresses
normal sprite emission using a verified RTS; it never writes hardware OBSEL
or OAM. Test subjects alone are staged in WRAM. Both transitions, all544
hardware bytes, adjacent scratch sentinel and clear Range/Time flags pass.
The full high-water stress fixture is not a throughput/cadence certificate.

Validation: production build PASS; width2343labels/0new; label drift0;
py_compile and diff check PASS. Build was from the preserved S5 worktree;
this prerequisite commit intentionally excludes S5 code and its combined
generated binaries. No actor policy/content was changed by this prerequisite.

Combined candidate ROM SHA256:
`4f0314db7a03c196a7de0c772d77df924cfc956d111457c63a411f3b6bdf30be`

Unchanged MSU SHA256:
`b1c4e499d611445e83a67f80f5be88dc2c5c0e2d91ebc14901e7891b8bcd89fc`
