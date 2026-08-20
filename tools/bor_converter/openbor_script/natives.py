"""Stable native IDs for Gate 6 (plan_vm.md §8).

Real OpenBOR natives like getentityproperty/changeentityproperty dispatch at
runtime on a string argument ("x", "position", ...). Since this project's
exporter controls codegen for a script it compiles ahead of time, each
(function name, compile-time-constant property-string) pair the target
script (SPAWN000.C) actually uses is specialized into its own stable native
ID here -- the string literal is consumed by the compiler and dropped from
the emitted call's argument list, rather than carried at runtime and
re-dispatched on the SA-1 side. This keeps native dispatch on the SA-1 side
a flat, fixed compare-and-branch chain (matching the existing Gate 3
abs/min/max/log dispatcher in vm_call.pasm) instead of a generic string
comparator. The host oracle (oracle.py) applies the identical specialization
so trace comparison stays meaningful.

`self` always resolves to the player (entity 0) -- this project has no
per-entity script attachment (oop.pasm's own "don't build a general
entity-lookup system for a single-player game" constraint), so GETLOCALVAR
is scoped to exactly the one caller identity a level-trigger-style script
like SPAWN000.C actually has.

Entity handles (self, vSpawn) are represented as plain VT_INTEGER slot
values (the entity index, 0-3) rather than a distinct VT_PTR encoding --
nothing in this script or in the current interpreter (vm_run.pasm/
vm_slots.pasm) gives VT_PTR (type 5) any behavior LOAD/SAVE doesn't already
give a plain integer, so a dedicated pointer representation would be
unused machinery. Documented here as the deliberate scope decision it is.

argc is fixed (min==max) for every native below -- OpenBOR's real natives
are often variadic, but every callsite in the one script this exporter
targets uses a fixed arity per specialized native, so the module's declared
native-table arity contract (FORMAT.md's natives table, min/max per entry)
is exact rather than a range.
"""

# (stable_id, name, argc) -- argc excludes any specialized-away string literal.
NATIVES = [
    (100, 'GETLOCALVAR_SELF', 0),        # getlocalvar("self") -> INTEGER entity index (player, 0)
    (101, 'GETENTITYPROP_X', 1),         # getentityproperty(e, "x")
    (102, 'GETENTITYPROP_A', 1),         # getentityproperty(e, "a") -- no altitude axis, returns 0
    (103, 'GETENTITYPROP_Z', 1),         # getentityproperty(e, "z") -- mapped to this project's screen Y
    (104, 'GETENTITYPROP_DIRECTION', 1), # getentityproperty(e, "direction") -- CHAR_FACING_LEFT
    (105, 'CLEARSPAWNENTRY', 0),
    (106, 'SETSPAWNENTRY_NAME', 1),      # setspawnentry("name", vName) -- vName kept, ignored (roster fixed per slot)
    (107, 'SPAWN', 0),                   # spawn() -> INTEGER entity index of the AI slot filled, or EMPTY if none free
    (108, 'CHANGEENTITYPROP_POSITION', 4),  # changeentityproperty(e, "position", x, z, y)
]

BY_NAME = {n: (sid, argc) for sid, n, argc in NATIVES}
BY_ID = {sid: (n, argc) for sid, n, argc in NATIVES}

# Each entry: openborscript call name -> (specialized native name, indices of
# args that must be a specific string literal (checked, then dropped), list
# of remaining arg indices to pass through in order). Hardcoded per the one
# script this exporter targets (SPAWN000.C) rather than a generic runtime
# string-dispatch table -- see module docstring.
CALL_SPECIALIZATIONS = {
    'getlocalvar': [
        ({0: 'self'}, 'GETLOCALVAR_SELF', []),
    ],
    'getentityproperty': [
        ({1: 'x'}, 'GETENTITYPROP_X', [0]),
        ({1: 'a'}, 'GETENTITYPROP_A', [0]),
        ({1: 'z'}, 'GETENTITYPROP_Z', [0]),
        ({1: 'direction'}, 'GETENTITYPROP_DIRECTION', [0]),
    ],
    'clearspawnentry': [
        ({}, 'CLEARSPAWNENTRY', []),
    ],
    'setspawnentry': [
        ({0: 'name'}, 'SETSPAWNENTRY_NAME', [1]),
    ],
    'spawn': [
        ({}, 'SPAWN', []),
    ],
    'changeentityproperty': [
        ({1: 'position'}, 'CHANGEENTITYPROP_POSITION', [0, 2, 3, 4]),
    ],
}
