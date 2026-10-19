"""Pinned 4086 phase-9 oracle checks and ownership contract boundaries."""
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
sys.path.insert(0, str(ROOT / "tools" / "verify"))
from source_live_health_native import (HealthFault, ROW_FIELDS, authored_model_inputs,
                                       NATIVE_ROW_OFFSETS, NATIVE_WORK_BYTES, bootstrap_row,
                                       update_health)


class HealthLeafVM:
    """Run the emitter's actual 65816 instruction stream with byte memory."""
    C, Z, V, N, M, X = 1, 2, 0x40, 0x80, 0x20, 0x10

    def __init__(self, asm, symbols):
        self.labels, self.ops = {}, []
        for raw in asm.splitlines():
            line = raw.split(";", 1)[0].strip().lower()
            if not line or line.startswith("."):
                continue
            if line.endswith(":"):
                self.labels[line[:-1]] = len(self.ops)
            else:
                self.ops.append(line)
        self.symbols = symbols
        self.mem = {}
        self.a, self.x, self.y = 0x1234, 0x4567, 0x89AB
        self.dp, self.dbr, self.sp = 0x2345, 0x42, 0x1FF0
        self.p = 0xDF
        self.pc = self.labels["livehealth_run"]
        self.stack = []
        self.writes = []
        self.dp_trace = []
        self.external = symbols["SourceForeignWork_Check"]

    @staticmethod
    def num(x):
        x = x.strip()
        if x.startswith("#"): x = x[1:]
        return int(x[1:], 16) if x.startswith("$") else int(x)

    def addr(self, x):
        return sum(self.num(v) if v.startswith("$") or v[0].isdigit() else 0
                   for v in x.split("+")) & 0xFFFFFF

    def read8(self, a): return self.mem.get(a & 0xFFFFFF, 0)
    def write8(self, a, v):
        a &= 0xFFFFFF; self.mem[a] = v & 255; self.writes.append(a)
    def read16(self, a): return self.read8(a) | self.read8(a + 1) << 8
    def write16(self, a, v): self.write8(a, v); self.write8(a + 1, v >> 8)
    def read32(self, a): return self.read16(a) | self.read16(a + 2) << 16
    def write32(self, a, v): self.write16(a, v); self.write16(a + 2, v >> 16)
    def dpaddr(self, x): return (self.dp + self.num(x)) & 0xFFFF
    def nz(self, v):
        self.p = (self.p & ~(self.N | self.Z)) | (self.N if v & 0x8000 else 0) | (self.Z if not v else 0)
    def push(self, value, size):
        self.stack.append((value, size))
        for i in range(size): self.write8(0x100 | ((self.sp - i) & 0xFFFF), value >> (8 * (size - i - 1)))
        self.sp = (self.sp - size) & 0xFFFF
    def pop(self):
        value, size = self.stack.pop(); self.sp = (self.sp + size) & 0xFFFF
        return value
    def run(self):
        for _ in range(20000):
            op = self.ops[self.pc]; self.pc += 1
            ss = op.split(None, 1); ins = ss[0]; arg = ss[1] if len(ss) > 1 else ""
            if ins in ("php", "phb", "phd", "phx", "phy"):
                self.push({"php":self.p,"phb":self.dbr,"phd":self.dp,"phx":self.x,"phy":self.y}[ins], 1 if ins in ("php","phb") else 2)
            elif ins in ("plp", "plb", "pld", "plx", "ply"):
                v=self.pop(); setattr(self,{"plp":"p","plb":"dbr","pld":"dp","plx":"x","ply":"y"}[ins],v)
            elif ins == "rep": self.p &= ~self.num(arg)
            elif ins == "phb": pass
            elif ins == "tsc": self.a=self.sp; self.nz(self.a)
            elif ins == "tcs": self.sp=self.a
            elif ins == "tcd": self.dp=self.a; self.nz(self.dp)
            elif ins == "stx": self.write16(self.dpaddr(arg),self.x)
            elif ins == "sty": self.write16(self.dpaddr(arg),self.y)
            elif ins == "stz": self.write16(self.dpaddr(arg),0)
            elif ins.startswith("lda"):
                if arg.startswith("#"): self.a=self.num(arg[1:])
                elif ins.endswith(".l"): self.a=self.read16(self.addr(arg))
                else: self.a=self.read16(self.dpaddr(arg))
                self.nz(self.a)
            elif ins.startswith("sta"):
                if not ins.endswith(".l") and self.num(arg) in (8,10,12,14,16,18,20,22,24,26,28,30): self.dp_trace.append((op,self.dp,self.a))
                if ins.endswith(".l"): self.write16(self.addr(arg),self.a)
                else: self.write16(self.dpaddr(arg),self.a)
            elif ins == "cmp":
                b=self.num(arg[1:]) if arg.startswith("#") else self.read16(self.dpaddr(arg))
                d=(self.a-b)&0xFFFF; self.p=(self.p&~(self.C|self.Z|self.N)) | (self.C if self.a>=b else 0) | (self.Z if d==0 else 0) | (self.N if d&0x8000 else 0)
            elif ins == "cmp.l":
                b=self.read16(self.addr(arg)); d=(self.a-b)&0xffff
                self.p=(self.p&~(self.C|self.Z|self.N)) | (self.C if self.a>=b else 0) | (self.Z if d==0 else 0) | (self.N if d&0x8000 else 0)
            elif ins in ("and", "ora", "eor", "and.l", "ora.l", "eor.l"):
                base=ins.split(".")[0]
                b=self.num(arg[1:]) if arg.startswith("#") else self.read16(self.addr(arg))
                self.a=({"and":self.a&b,"ora":self.a|b,"eor":self.a^b}[base])&0xffff; self.nz(self.a)
            elif ins in ("adc", "sbc"):
                b=self.num(arg[1:]) if arg.startswith("#") else self.read16(self.dpaddr(arg)); carry=int(bool(self.p&self.C))
                raw=self.a+b+carry if ins=="adc" else self.a-b-(1-carry)
                result=raw&0xffff; self.p=(self.p&~(self.C|self.V)) | (self.C if (raw>0xffff if ins=="adc" else raw>=0) else 0)
                if ins=="adc" and (~(self.a^b)&(self.a^result)&0x8000): self.p|=self.V
                if ins=="sbc" and ((self.a^b)&(self.a^result)&0x8000): self.p|=self.V
                self.a=result; self.nz(self.a)
            elif ins=="inc": self.a=(self.a+1)&0xffff; self.nz(self.a)
            elif ins=="dec": self.a=(self.a-1)&0xffff; self.nz(self.a)
            elif ins=="clc": self.p&=~self.C
            elif ins=="sec": self.p|=self.C
            elif ins in ("beq","bne","bcc","bcs","bmi","bpl","bvs","bvc"):
                tests={"beq":bool(self.p&self.Z),"bne":not self.p&self.Z,"bcc":not self.p&self.C,"bcs":bool(self.p&self.C),"bmi":bool(self.p&self.N),"bpl":not self.p&self.N,"bvs":bool(self.p&self.V),"bvc":not self.p&self.V}
                if tests[ins]: self.pc=self.labels[arg]
            elif ins=="jmp": self.pc=self.labels[arg]
            elif ins=="jsl":
                if self.addr(arg)==self.external: self.a=0; self.p&=~self.C
                else: raise AssertionError("unexpected JSL "+arg)
            elif ins=="tay": self.y=self.a
            elif ins=="tya": self.a=self.y; self.nz(self.a)
            elif ins=="rtl": return self.a, bool(self.p&self.C)
            else: raise AssertionError("unsupported emitted opcode: "+op)
        raise AssertionError("health leaf instruction bound")


def run(row=None, **overrides):
    values = dict(now=100, game_speed=60, ready=True, world_state=1,
                  phase=9, pending=1, world_time=100, slot=3, live=True,
                  birth=99, lifetime_end=None)
    values.update(overrides)
    return update_health(row or bootstrap_row(health=40, mp=5, maxmp=10), **values)


class LiveHealthTests(unittest.TestCase):
    def _native_vm(self, *, now=49, magictime=49, mp=-5, oldhealth=39,
                   oldmp=-4, dot=0, charging=0, model=3, phase=9,
                   state=1, pending=1, tick_time=None):
        from source_live_health_native import emit_normal_zero_mp
        from actor_s5_entity_fixture import symbols as read_symbols
        sy = read_symbols(ROOT / "src/main.sym")
        names = ("SourceForeignWork_Check", "SourceForeignWork_Generation",
                 "SourceWorldTick4086_Ready", "SourceWorldTick4086_State",
                 "SourceWorldTick4086_Phase", "SourceWorldTick4086_Pending",
                 "SourceWorldTick4086_Fault", "SourceWorldTick4086_TimeLo",
                 "SourceWorldTick4086_Slot", "VmSourceWorld_Ready",
                 "VmSourceWorld_Count", "VmSourceWorld_Time",
                 "SourceLifecycle4086_Ready")
        symbols = {name: sy[name] for name in names}
        work, charge_address = 0x7F8000, 0x43EB14
        asm = emit_normal_zero_mp(work, symbols, charging_address=charge_address,
                                  model_id=3)
        vm = HealthLeafVM(asm, symbols)
        m = vm.mem
        def w16(a, v): vm.write16(a, v & 0xffff)
        def w32(a, v): vm.write32(a, v & 0xffffffff)
        w16(work, 0xB6D1); w32(work+4, 1); w32(work+8, 0x00414000)
        w16(work+12, 0); w16(work+14, 0); w32(work+16, oldhealth)
        w32(work+20, oldmp); w32(work+24, dot)
        w16(sy["SourceForeignWork_Generation"], 1)
        for name, val in (("SourceWorldTick4086_Ready",0xB4D5),
                          ("SourceWorldTick4086_State",state),
                          ("SourceWorldTick4086_Phase",phase),
                          ("SourceWorldTick4086_Pending",pending),
                          ("SourceWorldTick4086_Fault",0),
                          ("SourceWorldTick4086_Slot",0),
                          ("VmSourceWorld_Ready",0xB4A3),
                          ("VmSourceWorld_Count",1),
                          ("SourceLifecycle4086_Ready",0xB4FB)):
            w16(sy[name],val)
        for off in (0,2):
            w16(sy["SourceWorldTick4086_TimeLo"]+off, (now if tick_time is None else tick_time) >> (8*off))
            w16(sy["VmSourceWorld_Time"]+off, now >> (8*off))
        w16(0x439048,3); w16(0x43904A,0xB4FB)
        w16(0x414000,0x4000); w16(0x414002,0x0041)
        w16(0x416800,model)
        w32(0x414024,40); w32(0x40C04C,mp); w32(0x40C040,0)
        w32(0x42E010,magictime); w32(charge_address,charging)
        before = (vm.x,vm.y,vm.dp,vm.dbr,vm.sp,vm.p)
        write_mark = len(vm.writes)
        result = vm.run()
        vm.runtime_writes = vm.writes[write_mark:]
        after = (vm.x,vm.y,vm.dp,vm.dbr,vm.sp,vm.p & ~1)
        self.assertEqual(after, (before[0],before[1],before[2],before[3],before[4],before[5]&~1))
        return vm, result, work

    def test_pinned_authority_and_row_capacity(self):
        source = (ROOT / "out/byor-motu-live-world-v1/update_health.c").read_bytes()
        pinned = (ROOT / "out/byor-motu-live-world-v1/pinned-openbor.c").read_bytes()
        self.assertIn(b"void update_health()", source)
        self.assertIn(source.strip(), pinned)
        self.assertEqual(len(ROW_FIELDS), 21)
        self.assertEqual(NATIVE_WORK_BYTES, 128)
        self.assertEqual(NATIVE_ROW_OFFSETS["oldhealth_i32"], 16)
        self.assertEqual(NATIVE_ROW_OFFSETS["oldmp_i32"], 20)

    def test_authored_he_man_fields_are_distinguished_from_loader_defaults(self):
        from compiler import Source
        source = Source(str(ROOT / "Masters of the Universe [v.3.0 Build 4086].pak"))
        inputs = authored_model_inputs(source)
        self.assertEqual(inputs["identity"], "He_Man")
        self.assertEqual(inputs["model_id"], 3)
        self.assertEqual(inputs["source_path"], "DATA\\CHARS\\HE-MAN\\HE-MAN.TXT")
        self.assertEqual(inputs["authored_health"], 150)
        self.assertEqual(inputs["authored_maxmp"], 0)
        self.assertEqual(inputs["authored_guard_max"], 0)
        self.assertEqual(inputs["loader_defaults"]["mprate"], 2)
        self.assertNotEqual(inputs["source_sha256"], "")

    def test_guards_reject_before_writes(self):
        for kwargs in (dict(ready=False), dict(world_state=0), dict(phase=8),
                       dict(pending=0), dict(world_time=99), dict(live=False),
                       dict(birth=100), dict(lifetime_end=100)):
            row = bootstrap_row(health=40, mp=5, maxmp=10, guard_max=20)
            before = dict(row)
            with self.assertRaises(HealthFault):
                run(row, **kwargs)
            self.assertEqual(row, before)

    def test_dot_active_is_pending_and_atomic(self):
        row = bootstrap_row(health=40, mp=5, maxmp=10, guard_max=20)
        row["dot_active"] = 1
        before = dict(row)
        result = run(row)
        self.assertEqual(result.status, "pending")
        self.assertEqual(result.reason, "COMMON_DOT_NATIVE_PROVIDER_REQUIRED")
        self.assertEqual(row, before)

    def test_motu_normal_branch_regenerates_and_updates_display(self):
        row = bootstrap_row(health=40, mp=5, maxmp=10, now=40, guard_max=6)
        row.update(guard_current=3, guardrate=2, guardtime=99,
                   mpstable=0, mprate=2, magictime=99, oldhealth=38, oldmp=4)
        result = run(row)
        self.assertEqual(result.status, "complete")
        self.assertEqual(row["guard_current"], 5)
        self.assertEqual(row["guardtime"], 160)
        self.assertEqual(row["mp"], 7)
        self.assertEqual(row["magictime"], 160)
        self.assertEqual(row["oldhealth"], 39)
        self.assertEqual(row["oldmp"], 5)

    def test_blocking_guard_rate_uses_c_integer_division(self):
        row = bootstrap_row(health=10, mp=4, maxmp=10, guard_max=8)
        row.update(guard_current=1, guardrate=3, blocking=1, guardtime=0)
        run(row, now=0, world_time=0, game_speed=60)
        self.assertEqual(row["guard_current"], 2)

    def test_stable_modes_and_cap(self):
        cases = ((0, 9, 0, 10), (1, 2, 5, 4), (1, 8, 5, 10),
                 (2, 8, 5, 6), (3, 2, 5, 4), (3, 8, 5, 6),
                 (4, 2, 5, 4), (4, 9, 5, 9))
        for stable, mp, pivot, expected in cases:
            row = bootstrap_row(health=5, mp=mp, maxmp=10)
            row.update(mpstable=stable, mpstableval=pivot, mprate=2,
                       mpdroprate=2, magictime=0)
            run(row, now=0, world_time=0)
            self.assertEqual(row["mp"], expected, (stable, mp))

    def test_charge_cap_and_timer_wrap(self):
        row = bootstrap_row(health=5, mp=9, maxmp=10, now=0xFFFFFFF8)
        row.update(charging=1, chargerate=2, mpchargetime=0xFFFFFFF8,
                   oldmp=0, mpstable=0)
        run(row, now=0xFFFFFFF8, world_time=0xFFFFFFF8, game_speed=60)
        self.assertEqual(row["mp"], 10)
        self.assertEqual(row["mpchargetime"], 7)
        self.assertEqual(row["oldmp"], 1)

    def test_timer_not_due_still_caps_and_converges_without_timer_write(self):
        row = bootstrap_row(health=7, mp=4, maxmp=10, now=0)
        row.update(magictime=2, mpstable=0, oldhealth=8, oldmp=3)
        result = run(row, now=1, world_time=1, game_speed=60)
        self.assertEqual(row["mp"], 4)
        self.assertEqual(row["magictime"], 2)
        self.assertEqual(row["oldhealth"], 7)
        self.assertEqual(row["oldmp"], 4)
        self.assertNotIn("magictime", result.writes)

    def test_negative_mp_and_overflow_are_source_signed(self):
        row = bootstrap_row(health=0, mp=-5, maxmp=0)
        row.update(mprate=2, oldmp=-4, magictime=0)
        run(row, now=0, world_time=0)
        self.assertEqual(row["mp"], -3)
        self.assertEqual(row["oldmp"], -3)

        row = bootstrap_row(health=0, mp=0x7FFFFFFF, maxmp=0)
        row.update(mprate=2, magictime=0)
        before = dict(row)
        with self.assertRaises(HealthFault):
            run(row, now=0, world_time=0)
        self.assertEqual(row, before)

    def test_charging_mode_updates_mp_and_charge_timer(self):
        row = bootstrap_row(health=1, mp=2, maxmp=10)
        row.update(charging=1, chargerate=2, mpchargetime=99, oldmp=2)
        result = run(row)
        self.assertEqual(result.status, "complete")
        self.assertEqual(row["mp"], 4)
        self.assertEqual(row["mpchargetime"], 115)
        self.assertEqual(row["magictime"], 0)

    def test_emitted_leaf_contains_strict_contract_and_single_commit(self):
        from source_live_health_native import emit_normal_zero_mp
        from actor_s5_entity_fixture import symbols as read_symbols
        sy = read_symbols(ROOT / "src/main.sym")
        names = ("SourceForeignWork_Check", "SourceForeignWork_Generation",
                 "SourceWorldTick4086_Ready", "SourceWorldTick4086_State",
                 "SourceWorldTick4086_Phase", "SourceWorldTick4086_Pending",
                 "SourceWorldTick4086_Fault", "SourceWorldTick4086_TimeLo",
                 "SourceWorldTick4086_Slot", "VmSourceWorld_Ready",
                 "VmSourceWorld_Count", "VmSourceWorld_Time",
                 "SourceLifecycle4086_Ready")
        asm = emit_normal_zero_mp(0x7F8000, {name: sy[name] for name in names},
                                  charging_address=0x43EB14)
        self.assertIn("LiveHealth_Pending:", asm)
        self.assertIn("LiveHealth_Fault:", asm)
        self.assertIn("LiveHealth_Commit:", asm)
        self.assertIn("lda.l $416800", asm)
        self.assertIn("sta.l $42E010", asm)
        self.assertIn("sta.l $40C04C", asm)
        self.assertNotIn("sta.l $414024", asm)
        self.assertIn("pld", asm)
        self.assertIn("plb", asm)

    def test_emitted_65816_stream_matches_normal_oracle_and_rejects_atomically(self):
        # This executes emitted 65816 operations against byte-addressed memory;
        # it is distinct from the source-level Python semantics tests above.
        vm, (a, carry), work = self._native_vm()
        self.assertEqual((a, carry), (0, False))
        expected = bootstrap_row(health=40, mp=-5, maxmp=0, now=49)
        expected.update(oldhealth=39, oldmp=-4, magictime=49)
        update_health(expected, now=49, game_speed=200, ready=True,
                      world_state=1, phase=9, pending=1, world_time=49,
                      slot=0, live=True, birth=0)
        self.assertEqual(vm.read32(0x40C04C), expected["mp"] & 0xffffffff)
        self.assertEqual(vm.read32(0x42E010), expected["magictime"])
        self.assertEqual(vm.read32(work+16), expected["oldhealth"] & 0xffffffff)
        self.assertEqual(vm.read32(work+20), expected["oldmp"] & 0xffffffff)
        vm, (a, carry), work = self._native_vm(mp=4, oldmp=3, magictime=50)
        self.assertEqual((a, carry), (0, False))
        expected = bootstrap_row(health=40, mp=4, maxmp=0, now=49)
        expected.update(oldhealth=39, oldmp=3, magictime=50)
        update_health(expected, now=49, game_speed=200, ready=True,
                      world_state=1, phase=9, pending=1, world_time=49,
                      slot=0, live=True, birth=0)
        self.assertEqual(vm.read32(0x40C04C), expected["mp"] & 0xffffffff)
        self.assertEqual(vm.read32(work+20), expected["oldmp"] & 0xffffffff)
        for overrides in (dict(dot=1), dict(charging=256), dict(model=4)):
            vm, (a, carry), work = self._native_vm(**overrides)
            self.assertEqual((a, carry), (1, False), overrides)
            changed = set(vm.runtime_writes)
            forbidden = (set(range(0x40C04C, 0x40C050)) |
                         set(range(0x42E010, 0x42E014)) |
                         set(range(work+16, work+24)))
            self.assertFalse(changed & forbidden, overrides)
            self.assertEqual(vm.read32(0x40C04C), -5 & 0xffffffff, overrides)
            self.assertEqual(vm.read32(0x42E010), 49, overrides)
            self.assertEqual(vm.read32(work+16), 39, overrides)
        vm, (a, carry), _ = self._native_vm(mp=0x7fffffff)
        self.assertEqual((a, carry), (0, True))
        self.assertFalse(set(vm.runtime_writes) & set(range(0x40C04C, 0x40C050)))
        self.assertEqual(vm.read32(0x40C04C), 0x7fffffff)
        vm, (a, carry), _ = self._native_vm(tick_time=48)
        self.assertEqual((a, carry), (0, True))

    def test_invalid_domain_fault_does_not_partially_commit(self):
        row = bootstrap_row(health=5, mp=4, maxmp=10, guard_max=8)
        row.update(guard_current=1, guardtime=0, mpstable=9)
        before = dict(row)
        with self.assertRaises(HealthFault):
            run(row, now=1, world_time=1)
        self.assertEqual(row, before)


if __name__ == "__main__":
    unittest.main()
