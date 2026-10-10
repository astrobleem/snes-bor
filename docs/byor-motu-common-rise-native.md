# Native common_rise and idle child

The generic common_rise owner uses the derived recovery model policy and actual
generation-bound blink/time rows. An animating rise returns before reading effect
or recovery leases. A stopped rise clears its action and riseattack deadline,
applies signed riseinv to blink and uint32 invincibility time, sets invincible,
then retains an actual idle request. Zero riseinv preserves blink/time without
requiring their storage lease. Preflight failures mutate no actor rows.

The final named-table prefix passes 598 native cases: all 16 authored policies,
three slots, three animation states, four uint32 times, 18 faults and four lease
short-circuits. Real source model/cache services followed by check_ai and the
actual idle frame owner pass 12 further cases, with exactly one frame-zero issue
under two check_ai calls. Existing action IDs remain unchanged; common_rise is
appended as ID 27. The five preceding frame emitters remain byte-identical.

Integration exposed a Poppy long indexed label-expression bug. The high-word
read encoded bank zero for `Table+2,x`. Earlier prefix results accidentally read
zeros from bank zero, while frame integration read unrelated ROM data. Those
ROMs and reports are retained and are rejected by a separate loaded-address
audit. The final emitter uses independently named low/high word tables. The
audit decodes both long indexed operands from each final ROM and compares every
loaded model word with the source descriptor; both pass.

These proofs install recovery storage and scheduler leases as fixture inputs.
Actual ticket resumption, complete lie/set_rise flow, invincibility expiration,
production memory ownership and MOTU gameplay remain unbound. Bank 0 stays
byte-identical with two bytes free. All 17 protected hashes are unchanged and
the width audit has zero violations or baseline entries. No color reduction
or PCM copies are applied.

[Bounded receipt](receipts/byor-motu-common-rise-native.json).
