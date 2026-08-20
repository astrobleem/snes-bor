"""Host oracle interpreter (plan_vm.md §8.2, dump_bor4086_oracle).

Interprets a compiler.Module directly (not the packed bytes -- packing is
proven separately by module.py's own round-trip, and the oracle's job is to
be ground truth for VM *semantics*, independent of the byte format). Uses
the exact Q16.16 arithmetic already validated against the real engine across
Gate 5's 29 checks (q16_* helpers, copied from tools/verify/vm_gate5.py
rather than re-derived -- advisor's own recommendation, so a hand-rolled
decimal model can't produce a trace diff that looks like an interpreter bug
but is actually oracle drift).

The six real natives (natives.py) are given a small stand-in "world": a
dict of per-entity CHAR_POS_X/CHAR_POS_Y/CHAR_FACING_LEFT/CHAR_HP, mirroring
the real engine's EntityN_Base struct fields (main.pasm). vm_gate6.py pokes
the identical starting values into real SA-1 WRAM before running the actual
ROM, and diffs both the native-call trace and the world's final state
against this oracle -- not just final VM slot values -- since the natives'
whole point is externally visible side effects.
"""
from .compiler import (
    VT_EMPTY, VT_INTEGER, VT_DECIMAL, VT_STR,
    OP_CALL, OP_SAVE, OP_NEG, OP_NOT, OP_MUL, OP_DIV, OP_MOD, OP_ADD, OP_SUB,
    OP_SHL, OP_SHR, OP_GE, OP_LE, OP_LT, OP_GT, OP_EQ, OP_NE, OP_OR, OP_AND,
    OP_BIT_OR, OP_XOR, OP_BIT_AND, OP_BRANCH_FALSE, OP_BRANCH_TRUE, OP_RET,
)
from .natives import BY_ID as NATIVE_BY_ID

Q16_SCALE = 1 << 16
CHAR_HP_MAX = 64


def s32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


def u32(v):
    return v & 0xFFFFFFFF


def q16_to_int(raw):
    return s32(raw) // Q16_SCALE if s32(raw) >= 0 else -((-s32(raw) + Q16_SCALE - 1) // Q16_SCALE)


def q16_add(a, b):
    return u32(s32(a) + s32(b))


def q16_truthy(vtype, value):
    if vtype == VT_EMPTY:
        return False
    if vtype in (VT_INTEGER, VT_DECIMAL):
        return s32(value) != 0
    return True  # STR/PTR: presence is truthy


class OracleFault(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(f'VM fault {code}')


class Oracle:
    def __init__(self, module, world, param_values):
        self.m = module
        self.world = world  # dict: entity_index -> {'x':int,'y':int,'facing':int,'hp':int}
        self.slots = [list(s) for s in module.slots]  # [type, flags, aux, value]
        for name, slot, _ptype in module.param_names:
            if name in param_values:
                vtype, value = param_values[name]
                self.slots[slot] = [vtype, 0, 0, u32(value)]
        self.trace = []  # list of dict(native, args=[...], result=(type,value))
        self.ip = module.entry_main

    def get(self, slot):
        return self.slots[slot][0], self.slots[slot][3]

    def set(self, slot, vtype, value, aux=0, flags=0):
        self.slots[slot] = [vtype, flags, aux, u32(value)]

    def run(self, max_steps=10000):
        steps = 0
        while True:
            steps += 1
            if steps > max_steps:
                raise OracleFault('TIMEOUT')
            if self.ip >= len(self.m.instructions):
                raise OracleFault('IP_OOB')
            ins = self.m.instructions[self.ip]
            nextip = self.ip + 1
            if ins.op == OP_RET:
                return
            elif ins.op == OP_SAVE:
                vt, v = self.get(ins.b)
                aux = self.slots[ins.b][2]
                self.set(ins.a, vt, v, aux=aux)
            elif ins.op in (OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD,
                             OP_GE, OP_LE, OP_LT, OP_GT, OP_EQ, OP_NE,
                             OP_OR, OP_AND, OP_BIT_OR, OP_XOR, OP_BIT_AND,
                             OP_SHL, OP_SHR):
                self._binop(ins)
            elif ins.op in (OP_NEG, OP_NOT):
                self._unop(ins)
            elif ins.op == OP_BRANCH_FALSE:
                vt, v = self.get(ins.b)
                if not q16_truthy(vt, v):
                    nextip = ins.a
            elif ins.op == OP_BRANCH_TRUE:
                vt, v = self.get(ins.b)
                if q16_truthy(vt, v):
                    nextip = ins.a
            elif ins.op == OP_CALL:
                self._call(ins)
            else:
                raise OracleFault(f'UNIMPLEMENTED_OP_{ins.op}')
            self.ip = nextip

    def _binop(self, ins):
        lt, lv = self.get(ins.b)
        rt, rv = self.get(ins.c)
        decimal = (lt == VT_DECIMAL or rt == VT_DECIMAL)
        op = ins.op
        if op == OP_ADD:
            if decimal:
                res = q16_add(lv if lt == VT_DECIMAL else lv * Q16_SCALE,
                               rv if rt == VT_DECIMAL else rv * Q16_SCALE)
                self.set(ins.a, VT_DECIMAL, res)
            else:
                self.set(ins.a, VT_INTEGER, u32(s32(lv) + s32(rv)))
            return
        if op == OP_SUB:
            lq = lv if lt == VT_DECIMAL else lv * Q16_SCALE
            rq = rv if rt == VT_DECIMAL else rv * Q16_SCALE
            if decimal:
                self.set(ins.a, VT_DECIMAL, u32(s32(lq) - s32(rq)))
            else:
                self.set(ins.a, VT_INTEGER, u32(s32(lv) - s32(rv)))
            return
        # Comparisons/logic: coerce decimals to a comparable common form.
        lcmp = s32(lv) if not decimal else (s32(lv) if lt == VT_DECIMAL else s32(lv) * Q16_SCALE)
        rcmp = s32(rv) if not decimal else (s32(rv) if rt == VT_DECIMAL else s32(rv) * Q16_SCALE)
        if op == OP_EQ:
            self.set(ins.a, VT_INTEGER, 1 if lcmp == rcmp else 0)
        elif op == OP_NE:
            self.set(ins.a, VT_INTEGER, 1 if lcmp != rcmp else 0)
        elif op == OP_LT:
            self.set(ins.a, VT_INTEGER, 1 if lcmp < rcmp else 0)
        elif op == OP_LE:
            self.set(ins.a, VT_INTEGER, 1 if lcmp <= rcmp else 0)
        elif op == OP_GT:
            self.set(ins.a, VT_INTEGER, 1 if lcmp > rcmp else 0)
        elif op == OP_GE:
            self.set(ins.a, VT_INTEGER, 1 if lcmp >= rcmp else 0)
        elif op == OP_AND:
            self.set(ins.a, VT_INTEGER, 1 if (q16_truthy(lt, lv) and q16_truthy(rt, rv)) else 0)
        elif op == OP_OR:
            self.set(ins.a, VT_INTEGER, 1 if (q16_truthy(lt, lv) or q16_truthy(rt, rv)) else 0)
        elif op == OP_MUL:
            self.set(ins.a, VT_INTEGER, u32(s32(lv) * s32(rv)))
        elif op == OP_DIV:
            rv_i = s32(rv)
            self.set(ins.a, VT_INTEGER, 0 if rv_i == 0 else u32(int(s32(lv) / rv_i)))
        elif op == OP_MOD:
            rv_i = s32(rv)
            if rv_i == 0:
                raise OracleFault('VMERR_DIV_ZERO')
            self.set(ins.a, VT_INTEGER, u32(int(__import__('math').fmod(s32(lv), rv_i))))
        elif op == OP_BIT_OR:
            self.set(ins.a, VT_INTEGER, u32(s32(lv) | s32(rv)))
        elif op == OP_XOR:
            self.set(ins.a, VT_INTEGER, u32(s32(lv) ^ s32(rv)))
        elif op == OP_BIT_AND:
            self.set(ins.a, VT_INTEGER, u32(s32(lv) & s32(rv)))
        elif op == OP_SHL:
            self.set(ins.a, VT_INTEGER, u32(s32(lv) << (s32(rv) & 31)))
        elif op == OP_SHR:
            self.set(ins.a, VT_INTEGER, u32((s32(lv) & 0xFFFFFFFF) >> (s32(rv) & 31)))

    def _unop(self, ins):
        vt, v = self.get(ins.a)
        if ins.op == OP_NEG:
            self.set(ins.a, vt, u32(-s32(v)))
        elif ins.op == OP_NOT:
            self.set(ins.a, VT_INTEGER, 0 if q16_truthy(vt, v) else 1)

    def _call(self, ins):
        cs = self.m.callsites[ins.c]
        name, argc = NATIVE_BY_ID[cs.target_id]
        args = [self.get(s) for s in cs.arg_slot_ids]
        result = self._native(name, args)
        self.trace.append({'native': name, 'args': [(t, u32(v)) for t, v in args], 'result': result})
        rtype, rvalue = result
        self.set(cs.result_slot, rtype, rvalue)

    def _native(self, name, args):
        if name == 'GETLOCALVAR_SELF':
            return (VT_INTEGER, 0)  # player, entity 0
        if name == 'GETENTITYPROP_X':
            e = s32(args[0][1])
            return (VT_INTEGER, u32(self.world[e]['x']))
        if name == 'GETENTITYPROP_A':
            return (VT_INTEGER, 0)  # no altitude axis
        if name == 'GETENTITYPROP_Z':
            e = s32(args[0][1])
            return (VT_INTEGER, u32(self.world[e]['y']))
        if name == 'GETENTITYPROP_DIRECTION':
            e = s32(args[0][1])
            return (VT_INTEGER, u32(self.world[e]['facing']))
        if name == 'CLEARSPAWNENTRY':
            return (VT_INTEGER, 0)  # real hardware's Vm_StoreIntResult always
        if name == 'SETSPAWNENTRY_NAME':          # tags the CALL result VT_INTEGER
            return (VT_INTEGER, 0)                # (see vm_native_engine.pasm header);
        if name == 'SPAWN':                        # oracle matches that constraint
            for e in (1, 2, 3):
                if self.world[e]['hp'] == 0:
                    self.world[e]['hp'] = CHAR_HP_MAX
                    self.world[e]['x'] = self.world[0]['x']
                    self.world[e]['y'] = self.world[0]['y']
                    self.world[e]['facing'] = self.world[0]['facing']
                    return (VT_INTEGER, e)
            return (VT_INTEGER, 0)  # no free slot -- deliberate simplification,
                                     # see vm_native_engine.pasm header; unused by
                                     # SPAWN000.C's own control flow either way
        if name == 'CHANGEENTITYPROP_POSITION':
            e = s32(args[0][1])
            fx_t, fx_v = args[1]
            fz_t, fz_v = args[2]
            x = q16_to_int(fx_v) if fx_t == VT_DECIMAL else s32(fx_v)
            z = q16_to_int(fz_v) if fz_t == VT_DECIMAL else s32(fz_v)
            self.world[e]['x'] = x
            self.world[e]['y'] = z
            return (VT_INTEGER, 0)
        raise OracleFault(f'UNKNOWN_NATIVE_{name}')


def run_oracle(module, world, param_values, max_steps=10000):
    o = Oracle(module, world, param_values)
    o.run(max_steps=max_steps)
    return {
        'slots': [tuple(s) for s in o.slots],
        'trace': o.trace,
        'world': o.world,
    }
