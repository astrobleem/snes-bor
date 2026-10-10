# Direct IRQ routing without bank-zero growth

The private direct-fetch emitter moves only the VM budget/fetch loop outside
bank zero. It calls the actual `Vm_FetchSource` and returns with JML to the
existing dispatch, yield or fault continuation. The six-byte loop prefix is
replaced in place. The existing four-byte `Vm_Fetch` JSL storage becomes a direct
IRQ JML, while its RTS remains. ROM size and bank-zero allocation do not grow.
The sole ordinary fetch caller is bypassed by the relocated loop.

A native production-ROM fixture passes original BOR cold boot, selector and
first-stage bootstrap, then a bounded script with calls, branches, parameters,
returns, NULL and installed local variants. The hand-derived script result is
97, both VM memory guards remain intact and fetch uses the actual source provider.
Its IRQ target is only an RTI placeholder: this proves VM routing, not raster
transfer or a production presentation lease.

Separate synthetic transfer trials exercise the old I-bit classifier gateway
and the direct IRQ instruction shape while an ordinary far-call loop runs.
The classifier trials drift: the general seven-control trial emits 405 rather
than 447 packets, and the positive-window trial emits 441. The positive trial
restores each completed interrupt's A/X/Y/D/DBR/SP and hardware return status.

The direct seven-control trial emits all 447 packets with exact destinations
and RGB555 words, exact OAM and restored interrupt contexts. It still fails:
168 high commits fall outside the safe CGRAM interval and pixels mismatch.
First-commit phase varies too much for its fixed timer. Handler time peaks at
1,220 master clocks before RTI, excluding hardware entry, vector jump and RTI.

An additional experimental compact handler removes the duplicate cursor end
bound and tests VBlank with BMI. It fails with 450 packets: VBlank admission alone
permits the extra row 224. This option is not admitted; the default handler
retains the explicit end bound. Its 1,176-clock result does not establish a valid
replacement for that ownership check.

The [receipt](receipts/byor-motu-direct-fetch-routing-trials.json) retains bounded
hashes, results and nonclaims. Full source-frame scheduling and production
IRQ/presentation ownership remain open. These handler trials do not reject
other raster mechanisms. No color reduction or PCM copies.
