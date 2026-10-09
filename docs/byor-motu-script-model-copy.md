# Source model-switch script copying

The generic method-0 model-copy capability reuses the checked B5SC/B4CO
descriptors and script controls. It admits only shared animation programs
without init or clear methods. Other script kinds or lifecycle entries remain
explicit compilation failures under this capability.

The pinned BOR 4086 Script_Copy and Script_Clear bodies establish that method
0 preserves named variable values. Copying an absent source script returns
immediately, preserving the old instance; copying an initialized source
replaces the shared interpreter identity and initialized bit. A prior clear,
as requested by model flag 4, resets initialization while retaining variables.
The native representation retains that initialization state and resolves actual
animation programs from current/default model descriptors when execution
begins. It does not allocate or own a separate interpreter.

All 24 unchanged C cases pass, including optional prior clear, initialized
and absent source/destination instances, retained names, values and varlist
identity. The native proof checks all sixteen authored descriptors in slots
0, 1 and 127, old initialization states, paired program identities, guards,
unchanged foreign-instance values and CPU context. No new state is allocated.
The prior constructor method-1 C proof still passes its 24 cases.

This is a component proof. The complete ordered model-switch service, live
weapon-frame transition, combat and Demo completion remain open. No color
reduction or PCM copies are applied; production assembly and bank 0 are unchanged.

Reproduce with `source_script_clone_authority.py --model-copy` and
`m4_script_clone_native.py --model-copy`. Bounded receipts are
`docs/receipts/byor-motu-script-model-copy-authority.json` and
`docs/receipts/byor-motu-script-model-copy-native.json`.
