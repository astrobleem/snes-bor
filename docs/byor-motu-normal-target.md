# Source ranged target selection

The generic target reference now exposes `normal_find`, covering the actual
normal_find_target animation-range filter, signed detection adjustment, full
pool order, active prefix, facing preference and previous-target vulnerability
or invincibility preference. Calls from a retained self pointer after retirement
are permitted, as in the pinned source. Signed detection overflow rejects
explicitly. The existing `find` interface retains its prior live-self policy.

The authority proof compiles unchanged normal_find_target and diff bodies plus
the literal check_range macro from BOR 4086 commit
af23dc9c2316bb7853bb266ccf40986aa9765aeb. It exercises all 80 source animation
ranges, four coordinate axes, both boundaries, fractional offsets, detection,
filter failures, order permutations, active prefixes and retired self calls.
All 5,766 integral cases agree across 9,610 total comparisons. Two fractional
unbounded cases at 9,999 units differ under the established Q16.16 adaptation:
source binary32 rounds the extra 1/65,536 unit away; Q16 retains it and excludes
that candidate. Both result differences are retained in the receipt. This is
not a claim of arbitrary float exactness. All five prior unbounded-target
tests pass unchanged.

The generic native provider now passes 653 isolated cases: 640 queries across
all 80 authored animation ranges and both directions, plus 13 rejected leases,
roles, handles and coordinate tags. Actual check_ai requests player_think;
the provider does not manufacture a common_think owner. It reads canonical
actor metadata and the current mutable role-to-animation mapping, preserves
the caller's CPU context and VM result scratch, and permits retired-self
queries. It allocates no new state bytes. This proof instruments input actor
rows and does not claim an authored combat scene.

The attack-chain continuation is still external. Production combat and M4
certification remain open. No color reduction is applied.

Reproduce with `source_normal_target_authority.py --source <PAK> --output
out/byor-motu-normal-target-authority`. The bounded receipt is
`docs/receipts/byor-motu-normal-target-authority.json`.
The native proof is `m4_normal_target_native.py --rom <baseline> --source <PAK>
--output out/byor-motu-normal-target-native`; its bounded receipt is
`docs/receipts/byor-motu-normal-target-native.json`.
