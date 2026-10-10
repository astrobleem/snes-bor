# Native set_rise animation and flags

The generic set_rise selector shares the checked typed-animation fallback
mechanism with set_fall: signed/out-of-range damage types fall back to type zero,
and an absent typed animation retries the default. The selector uses the source
rise array and a separate owner identity. Existing set_fall code is unchanged.
The real animation initializer and frame owner preserve incoming velocity until
the source set_rise flags execute after ent_set_anim completes.

The final join passes 84 cases after actual mutable model/cache transitions,
including full-width damage types, stale-generation rejection, exactly one
animation/frame issue under retry and actual native frame acknowledgement.
The flags owner sets common_rise and clears drop, falling, projectile and
nograb. It clears target X and original global self Z/Y separately, preserving
target Z/Y when self differs. It resets the existing juggle-current row to the
source-derived zero maximum. No duplicate juggle storage is allocated.

Every case also executes four rejected flag calls: stale generation, damaged
effect marker, invalid self pointer and missing juggle lease. All 336 calls
return failure while preserving complete actor rows and CPU context. A fresh
fixture retry follows each rejection; no observer acknowledges source work.

Palette and hit owners use the reduced 25,024-byte CHR boundary. An earlier
fixture changed only the hit declaration and correctly failed in the preceding
model palette service. Its FAIL report remains. Constructor and graphics
producers still require a production installation of the same boundary.

The available-animation branch and distinct-self behavior are proven. Missing
default rise, self equal to target, actual yielded resumption, complete
common_lie dispatch and production gameplay are not admitted by these cases.
Bank 0 remains byte-identical with two bytes free; all 17 protected hashes and
the zero-violation width audit remain intact. No color reduction or PCM copies
are applied. [Bounded receipt](receipts/byor-motu-set-rise-native.json).
