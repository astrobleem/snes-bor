# Actual constructor, recovery and default weapon child

The isolated native fixture joins the actual player constructor and authored
JUMP frame zero to checked recovery, then source spawn weapon selection and the
real model-transition owner. `SpawnWeapon_Begin` checks the foreign/global lease,
player role, current self, index, source view and idle model owner. It selects the
saved player weapon number when nonzero, otherwise installed stage `setweap`.
It invokes the native weapon resolver and model-transition Begin. Pending model
services remain pending; no acknowledgement is synthesized.

The fixture installs source-derived mutable weapon cache and immutable B4MW
metadata, and calls the real shallow metadata installer on the actual constructed
model. The pinned engine stage default is zero; GUILE2 has no setweap override.
Saved -1 and saved zero/stage zero both return actual default model 3 with sync
one. The native same-model early return reaches State 2 and Service 0. Both cases
pass byte comparisons across the actual view, side, core, four player weapon
numbers and entity weapon metadata. Child costs are 25910 and 26186 master clocks,
excluding construction/recovery and without production frame-budget admission.

ROM SHA256: `1125100aadfec3b594fa5a7c57aa1a33266ca192ee4382d694c94e0f39f05313`.
Weapon table SHA256: `22839440a1d508458b5ee08c9fd99882c289679f8af64aed5d041e2054d3c153`.
Weapon cache SHA256: `ed06825e306ba372130baf5190c22629c5927624f570e4f5b7146a7f72efe78b`.

Bank zero matches the baseline. The media alias was moved with an identity check;
no PCM files were copied. This proves the same-model weapon child after actual
construction, not model-changing weapon services, terrain placement, full
spawnplayer, MOTU registration, combat or Demo completion. No color reduction.
