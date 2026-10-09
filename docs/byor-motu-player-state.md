The source API permits arbitrary signed integers in charging, turning and
getting. These fields retain full DWORD values, alongside rush current/max and
its unsigned time field. They are not packed as booleans.

The checked B48R module has 616 live eight-byte slots at 7FC000..7FD33F. Its
unused tail is 7FD340..7FDFFF: 3,264 bytes. Six DWORDs for each of 128 actors
consume 3,072 bytes, ending at 7FDF3F, leaving 192 bytes. The existing VM slot
loader copies only its loaded count and is called only from the boot wrapper.
The compiler rejects modules whose tail cannot contain the complete state.

The native lease rejects initialization while a script/call frame is active.
Every row access checks the loaded slot count, captured extent, nonzero matching
generation, source pool/count and physical slot. Birth clears one complete row;
reads copy all six words; writes preserve signed/raw 32-bit identities. Module
replacement must release the lease first, even when the replacement count is
the same. Count checking does not substitute for that lifetime contract.

The 921-case native proof includes all fields and all 128 slots, signed extremes,
birth clearing, initialization/release and 22 guards. It checks every byte of
the entire 8 KiB slot reservation and high guard against the expected changes,
including all active slots and every sibling state row. CPU/stack and decimal
flags are retained. The compiled count is supplied by the isolated observer;
the production full-module loader, birth hook and property handlers still need
binding. Caller controls require 64 bytes in the explicit controller arena.

This is not a MOTU gameplay/completion certificate. No color reduction or PCM
copies are applied.

An isolated actual-constructor proof now enables the native lease and an opt-in
bridge at SourceAIState4086_InitializeBirth. It seeds the new row with stale
bytes after lease initialization, then verifies that the real constructor clears
all six fields before exists publication, preserves a distant sibling, and
completes real authored SELECT initialization/scripts/effects. The original AI
birth prologue is byte-checked before the private fixture patch. Ready=0 delegates
to that original birth path; an active lease must validate before clearing.
This bridge has not yet been installed in the production foreign loader.
