"""Semantic pass + codegen: openborscript AST -> revision-1 module IR
(plan_vm.md §8, FORMAT.md). Produces plain Python structures; module.py packs
them into the actual binary per FORMAT.md.

Scope: the FIRST FuncDecl in the program compiles as the module's
entry_main, treating it as a root program -- no CALL/PARAM frame is
synthesized for the function's own parameters. A standalone test harness
(vm_gate6.py) instead bakes fixed test values directly into those
parameter slots' *initial* values, the same pattern Gate 0-5's own fixtures
already use for CONSTINT-style preinitialized slots. This sidesteps
synthesizing a fake outer caller for a script that, in a real mod, would be
invoked by the engine with real arguments -- the compiled instruction
stream for the function body itself is unmodified/real either way.

Every OTHER FuncDecl in the program compiles as a real, in-script-callable
function: a PARAM prologue reads its declared parameters out of the active
call frame (vm_call.pasm's Vm_Op_Param -- faults with VMERR_NO_CALL_FRAME
if FrameTop==0, which is exactly why entry_main itself is exempt), and
every `return` desugars to a JUMPR-to-epilogue (value-carrying) or an
unconditional branch-to-epilogue (value-less) followed by a single trailing
RET -- see compile_return. A call to another script-declared function
resolves BEFORE native-specialization lookup (compile_call) and emits a
TARGET_KIND_SCRIPT callsite; the CALL instruction's own operand A (the
callee's entry IP) can only be known once the callee itself has been
compiled, so it is left 0 and backpatched in a final pass exactly like
compile_if's own forward-branch patches (see compile_program's tail).

Each function's local variables (params + VarDecls) live in their OWN
`slot_names` scope -- module.slots stays one flat, physically shared array
(matches the real WRAM-backed VmSlots_Wram, one bank for the whole loaded
script), but the NAME namespace is reset per function so two functions can
each declare a local called e.g. `i` without colliding. See
compile_program's save/restore of self.m.slot_names around each function.

Scope boundary, stated plainly: this makes script-to-script CALL/PARAM/
RET/JUMPR reachable from real compiled openborscript source for the first
time. It does NOT make any real extracted pak script compile -- BOR/TMNT
have zero script content and DDM's real scripts also need `for` loops and
~30 more natives (openbor_script_coverage_gap_data project memory). This
is compiler/runtime plumbing, proven with a small synthetic fixture, not a
claim that real mod scripts now run.

`for`/`break`/`continue` (compile_for, and break/continue support added to
compile_while) are the next real gap closed here -- 8/21 (38%) of Double
Dragon Moto's real scripts use `for` loops (openbor_script_coverage_gap_data
project memory), the single most common missing construct after
script-to-script CALL. `for`'s `continue` target is the post-expression
(real C semantics -- NOT the condition check, which is `while`'s own
`continue` target), tracked per-loop via a `loop_stack` of pending
break/continue patch lists so nested loops target the correct innermost
loop. No new opcodes needed -- both desugar entirely into the same
BRANCH_FALSE-on-constant-false "unconditional jump" idiom every other
control-flow construct here already uses.

Slot type tags (FORMAT.md, Q16.16 profile): 0 EMPTY, 1 INTEGER, 2 DECIMAL,
5 PTR, 6 STR. Entity handles (self/vSpawn) are represented as VT_INTEGER,
not VT_PTR -- see natives.py's module docstring for why.
"""
import struct
from . import ast_nodes as ast
from .natives import NATIVES, BY_NAME as NATIVE_BY_NAME, CALL_SPECIALIZATIONS

VT_EMPTY = 0
VT_INTEGER = 1
VT_DECIMAL = 2
VT_PTR = 5
VT_STR = 6

TARGET_KIND_SCRIPT = 0
TARGET_KIND_IMPORTED = 1
TARGET_KIND_NATIVE = 2

# Opcode values (opcode_manifest.csv / bor_vm_opcodes.pasm) -- duplicated
# here as plain ints rather than re-parsing the .pasm at export time; kept
# in exact sync with tools/verify/vm_fixtures/opcode_manifest.csv by hand,
# same convention as that file's own "define all of the rest, ready to
# paste" approach for constants not in the vendored package.
OP_CALL = 8
OP_SAVE = 4
OP_NEG = 10
OP_NOT = 11
OP_MUL = 12
OP_DIV = 13
OP_MOD = 14
OP_ADD = 16
OP_SUB = 17
OP_SHL = 18
OP_SHR = 19
OP_GE = 22
OP_LE = 23
OP_LT = 24
OP_GT = 25
OP_EQ = 26
OP_NE = 27
OP_OR = 28
OP_AND = 29
OP_BIT_OR = 30
OP_XOR = 31
OP_BIT_AND = 32
OP_BRANCH_FALSE = 36
OP_BRANCH_TRUE = 37
OP_PARAM = 40
OP_RET = 43
OP_JUMPR = 46

BINOP_OPCODE = {
    '+': OP_ADD, '-': OP_SUB, '*': OP_MUL, '/': OP_DIV, '%': OP_MOD,
    '==': OP_EQ, '!=': OP_NE, '<': OP_LT, '<=': OP_LE, '>': OP_GT, '>=': OP_GE,
    '&&': OP_AND, '||': OP_OR, '&': OP_BIT_AND, '|': OP_BIT_OR, '^': OP_XOR,
    '<<': OP_SHL, '>>': OP_SHR,
}
UNARY_OPCODE = {'-': OP_NEG, '!': OP_NOT}  # '+' (POS) is a real no-op; skip emitting it

Q16_SCALE = 1 << 16


def q16_from_float(f):
    raw = int(round(f * Q16_SCALE))
    return raw & 0xFFFFFFFF


class CompileError(Exception):
    pass


class Instr:
    __slots__ = ('op', 'flags', 'a', 'b', 'c')

    def __init__(self, op, a=0, b=0, c=0, flags=0):
        self.op = op
        self.flags = flags
        self.a = a & 0xFFFF
        self.b = b & 0xFFFF
        self.c = c & 0xFFFF


class Callsite:
    __slots__ = ('target_kind', 'argc', 'target_id', 'result_slot', 'arg_slot_ids',
                 'arg_list_index', 'flags', 'debug_name_id')

    def __init__(self, target_kind, argc, target_id, result_slot, arg_slot_ids,
                 arg_list_index, flags=0, debug_name_id=0xFFFF):
        self.target_kind = target_kind
        self.argc = argc
        self.target_id = target_id
        self.result_slot = result_slot
        self.arg_slot_ids = arg_slot_ids
        self.arg_list_index = arg_list_index
        self.flags = flags
        self.debug_name_id = debug_name_id


class Module:
    """Compiled-module IR, pre-packing. See module.py for the binary form."""

    def __init__(self):
        self.instructions = []          # list[Instr]
        self.slots = []                 # list[(type, flags, aux, value)]
        self.slot_names = {}            # name -> slot index (params + locals)
        self.callsites = []             # list[Callsite]
        self.strings = []               # list[bytes] -- interned pool
        self.string_handles = {}        # bytes -> handle (index into self.strings)
        self.natives_used = set()       # set of stable_native_id
        self.entry_main = 0
        self.param_names = []           # ordered list of this function's own params


class Compiler:
    def __init__(self):
        self.m = Module()
        self.local_functions = {}       # name -> FuncDecl (declared, all funcs)
        self.func_entry_ip = {}         # name -> entry IP (filled as each compiles)
        self.pending_script_calls = []  # [(instr_idx, callee_name)] -- CALL.a backpatch
        self.is_entry_function = True   # False while compiling a non-entry function
        self.epilogue_patches = []      # pending JUMPR/branch targets for current fn
        self.loop_stack = []            # stack of {'break_patches':[...], 'continue_patches':[...]}

    def new_slot(self, vtype=VT_EMPTY, value=0, aux=0, flags=0, name=None):
        idx = len(self.m.slots)
        self.m.slots.append([vtype, flags, aux, value])
        if name is not None:
            self.m.slot_names[name] = idx
        return idx

    def set_slot(self, idx, vtype, value, aux=0, flags=0):
        self.m.slots[idx] = [vtype, flags, aux, value]

    def lookup(self, name):
        if name not in self.m.slot_names:
            raise CompileError(f'undeclared identifier {name!r}')
        return self.m.slot_names[name]

    def intern_string(self, s):
        b = s.encode('utf-8')
        if b in self.m.string_handles:
            return self.m.string_handles[b]
        handle = len(self.m.strings)
        self.m.strings.append(b)
        self.m.string_handles[b] = handle
        return handle

    def emit(self, op, a=0, b=0, c=0, flags=0):
        self.m.instructions.append(Instr(op, a, b, c, flags))
        return len(self.m.instructions) - 1

    # --- top level -----------------------------------------------------

    def compile_program(self, program):
        if not program.functions:
            raise CompileError('no functions in source')
        # Declare pass: every function's name+params known before ANY body
        # compiles, so forward references (a func calling one declared
        # later in the file) resolve -- same reason compile_if/compile_while
        # patch branch targets after the fact rather than requiring them
        # known up front.
        for fn in program.functions:
            if fn.name in self.local_functions:
                raise CompileError(f'duplicate function {fn.name!r}')
            self.local_functions[fn.name] = fn

        entry_fn = program.functions[0]
        self.m.entry_main = 0
        self.is_entry_function = True
        for ptype, pname in entry_fn.params:
            slot = self.new_slot(vtype=self._default_type_for(ptype), name=pname)
            self.m.param_names.append((pname, slot, ptype))
        self.func_entry_ip[entry_fn.name] = 0
        self.compile_block(entry_fn.body)
        if not self.m.instructions or self.m.instructions[-1].op != OP_RET:
            self.emit(OP_RET)

        # Every other function: real PARAM prologue (needs an active call
        # frame -- entry_main above is exempt, see module docstring), a
        # fresh local-name scope, and a single epilogue all early returns
        # funnel through.
        for fn in program.functions[1:]:
            self.is_entry_function = False
            self.func_entry_ip[fn.name] = len(self.m.instructions)
            saved_slot_names = self.m.slot_names
            self.m.slot_names = {}
            self.epilogue_patches = []
            self.loop_stack = []
            for ptype, pname in fn.params:
                pslot = self.new_slot(vtype=self._default_type_for(ptype), name=pname)
                self.emit(OP_PARAM, a=pslot)
            self.compile_block(fn.body)
            epilogue_ip = len(self.m.instructions)
            for idx in self.epilogue_patches:
                self.m.instructions[idx].a = epilogue_ip
            self.emit(OP_RET)
            self.m.slot_names = saved_slot_names
        self.is_entry_function = True

        # Backpatch every script callsite now that all entry IPs are known;
        # keep callsite.target_id in agreement with CALL's own operand A,
        # matching vm_call.pasm's own documented exporter convention (the
        # runtime only ever trusts the instruction, but a real exporter
        # keeps both fields consistent).
        for instr_idx, callee_name in self.pending_script_calls:
            entry_ip = self.func_entry_ip[callee_name]
            instr = self.m.instructions[instr_idx]
            instr.a = entry_ip
            self.m.callsites[instr.c].target_id = entry_ip
        return self.m

    @staticmethod
    def _default_type_for(type_name):
        if type_name == 'float' or type_name == 'double':
            return VT_DECIMAL
        if type_name == 'int' or type_name == 'long':
            return VT_INTEGER
        return VT_EMPTY  # void / char* -- runtime-typed, starts EMPTY

    # --- statements ------------------------------------------------------

    def compile_block(self, block):
        for stmt in block.stmts:
            self.compile_stmt(stmt)

    def compile_stmt(self, node):
        if isinstance(node, ast.Block):
            self.compile_block(node)
        elif isinstance(node, ast.VarDecl):
            self.compile_vardecl(node)
        elif isinstance(node, ast.ExprStmt):
            self.compile_expr(node.expr, dest=None)
        elif isinstance(node, ast.Assign):
            self.compile_assign(node)
        elif isinstance(node, ast.Return):
            self.compile_return(node)
        elif isinstance(node, ast.If):
            self.compile_if(node)
        elif isinstance(node, ast.While):
            self.compile_while(node)
        elif isinstance(node, ast.For):
            self.compile_for(node)
        elif isinstance(node, ast.Break):
            if not self.loop_stack:
                raise CompileError('break outside a loop')
            idx = self.emit(OP_BRANCH_FALSE, a=0, b=self._false_slot())
            self.loop_stack[-1]['break_patches'].append(idx)
        elif isinstance(node, ast.Continue):
            if not self.loop_stack:
                raise CompileError('continue outside a loop')
            idx = self.emit(OP_BRANCH_FALSE, a=0, b=self._false_slot())
            self.loop_stack[-1]['continue_patches'].append(idx)
        else:
            raise CompileError(f'unsupported statement {type(node).__name__}')

    def compile_return(self, node):
        if self.is_entry_function:
            # Root return: nothing outside the VM reads a "return value"
            # from entry_main, so this stays exactly the pre-existing
            # behavior (Gate 0-7 already depend on it byte-for-byte).
            if node.value is not None:
                self.compile_expr(node.value, dest=None)
            self.emit(OP_RET)
            return
        # Non-entry function: every return -- early or trailing -- funnels
        # through ONE epilogue (patched to the real IP once the whole body
        # is compiled, in compile_program), which then falls into a single
        # trailing RET. A value-carrying return stages it via JUMPR
        # (vm_call.pasm's only path that sets VMFRAME_RETURN_SRC); a
        # value-less return reuses the same unconditional-branch idiom
        # compile_while already uses for its back-edge (BRANCH_FALSE on
        # the constant-false slot always taken).
        if node.value is not None:
            vslot = self.compile_expr(node.value, dest=None)
            idx = self.emit(OP_JUMPR, a=0, b=vslot)
        else:
            idx = self.emit(OP_BRANCH_FALSE, a=0, b=self._false_slot())
        self.epilogue_patches.append(idx)

    def compile_vardecl(self, node):
        home = self.new_slot(vtype=self._default_type_for(node.var_type), name=node.name)
        if node.init is not None:
            self.compile_expr(node.init, dest=home)

    def compile_assign(self, node):
        home = self.lookup(node.target.name)
        if node.op == '=':
            self.compile_assign_value(node.value, home)
        else:
            op_char = node.op[0]
            synthetic = ast.BinOp(op=op_char, left=node.target, right=node.value)
            self.compile_expr(synthetic, dest=home)

    def compile_assign_value(self, value_node, home):
        """Assign an expression's value into an EXISTING, already-declared
        slot (`home`) -- as opposed to compile_vardecl, where `home` is a
        brand-new slot nothing has touched yet.

        A literal (IntLit/FloatLit/StringLit) is a real bug trap here:
        compile_expr's own dest-threading for literals BAKES the constant
        into the destination slot's *compile-time initial value* (matching
        CONSTINT's real "link/no-op, materialized by the host linker"
        semantics -- see opcode_manifest.csv) rather than emitting any
        runtime instruction. That is correct ONLY the first time a slot is
        ever written (compile_vardecl's init, which still calls
        compile_expr directly, unchanged) -- for a REASSIGNMENT to a slot
        that may already hold a real runtime value (a param, a previous
        loop iteration, ...), baking a compile-time constant into "initial
        state" has NO runtime effect at all: the statement silently
        no-ops. Found via vm_script_call.py's fixture (`i = 0;` reassigning
        a PARAM'd value) -- confirmed on real hardware AND the oracle
        before this fix, both showing the reset simply didn't happen.
        Fix: route literals through a dedicated, freshly-allocated constant
        slot (compile_expr's own dest=None path, always safe -- a new slot
        is by definition never touched before this) and copy it in with a
        REAL runtime SAVE, exactly the same pattern the Ident branch below
        already uses for `x = y;`. Non-literal expressions (BinOp/UnaryOp/
        Call/Ident/nested Assign) already emit a genuine runtime
        instruction when given an existing dest, so they're unaffected.
        """
        if isinstance(value_node, (ast.IntLit, ast.FloatLit, ast.StringLit)):
            const_slot = self.compile_expr(value_node, dest=None)
            self.emit(OP_SAVE, a=home, b=const_slot)
            return home
        return self.compile_expr(value_node, dest=home)

    def compile_if(self, node):
        cond_slot = self.compile_expr(node.cond, dest=None)
        branch_idx = self.emit(OP_BRANCH_FALSE, a=0, b=cond_slot)  # patched below
        self.compile_stmt(node.then)
        if node.els is not None:
            jump_idx = self.emit(OP_BRANCH_FALSE, a=0, b=cond_slot)  # placeholder, patched to unconditional below
            self.m.instructions[branch_idx].a = len(self.m.instructions)
            self.compile_stmt(node.els)
            self.m.instructions[jump_idx].a = len(self.m.instructions)
            self.m.instructions[jump_idx].b = self._false_slot()
        else:
            self.m.instructions[branch_idx].a = len(self.m.instructions)

    def _false_slot(self):
        # Deliberately module-global, NOT per-function-scoped like ordinary
        # locals: it's a constant-0 slot, never named (no slot_names entry,
        # so no cross-function lookup collision is possible) and never
        # written after creation, so every function sharing one physical
        # slot is safe.
        if getattr(self, '_false_slot_cache', None) is None:
            self._false_slot_cache = self.new_slot(vtype=VT_INTEGER, value=0)
        return self._false_slot_cache

    def compile_while(self, node):
        loop_start = len(self.m.instructions)
        cond_slot = self.compile_expr(node.cond, dest=None)
        branch_idx = self.emit(OP_BRANCH_FALSE, a=0, b=cond_slot)
        self.loop_stack.append({'break_patches': [], 'continue_patches': []})
        self.compile_stmt(node.body)
        loop_ctx = self.loop_stack.pop()
        # `continue` lands here -- one hop before the back-edge, which then
        # re-checks the condition. A harmless extra jump, not an extra
        # condition check; keeps while/for sharing one continue-target shape.
        continue_ip = len(self.m.instructions)
        for idx in loop_ctx['continue_patches']:
            self.m.instructions[idx].a = continue_ip
        # unconditional back-edge: Branch_FALSE on the constant-false slot
        self.emit(OP_BRANCH_FALSE, a=loop_start, b=self._false_slot())
        loop_end = len(self.m.instructions)
        self.m.instructions[branch_idx].a = loop_end
        for idx in loop_ctx['break_patches']:
            self.m.instructions[idx].a = loop_end

    def compile_for(self, node):
        if node.init is not None:
            self.compile_stmt(node.init)
        loop_start = len(self.m.instructions)
        branch_idx = None
        if node.cond is not None:
            cond_slot = self.compile_expr(node.cond, dest=None)
            branch_idx = self.emit(OP_BRANCH_FALSE, a=0, b=cond_slot)
        self.loop_stack.append({'break_patches': [], 'continue_patches': []})
        self.compile_stmt(node.body)
        loop_ctx = self.loop_stack.pop()
        # `continue` in a for-loop must still run the post-expression before
        # re-checking the condition (real C semantics) -- unlike while, this
        # target is NOT loop_start itself.
        post_ip = len(self.m.instructions)
        for idx in loop_ctx['continue_patches']:
            self.m.instructions[idx].a = post_ip
        if node.post is not None:
            self.compile_expr(node.post, dest=None)
        self.emit(OP_BRANCH_FALSE, a=loop_start, b=self._false_slot())
        loop_end = len(self.m.instructions)
        if branch_idx is not None:
            self.m.instructions[branch_idx].a = loop_end
        for idx in loop_ctx['break_patches']:
            self.m.instructions[idx].a = loop_end

    # --- expressions -----------------------------------------------------

    def compile_expr(self, node, dest):
        if isinstance(node, ast.IntLit):
            slot = dest if dest is not None else self.new_slot()
            self.set_slot(slot, VT_INTEGER, node.value & 0xFFFFFFFF)
            return slot
        if isinstance(node, ast.FloatLit):
            slot = dest if dest is not None else self.new_slot()
            self.set_slot(slot, VT_DECIMAL, q16_from_float(node.value))
            return slot
        if isinstance(node, ast.StringLit):
            slot = dest if dest is not None else self.new_slot()
            handle = self.intern_string(node.value)
            self.set_slot(slot, VT_STR, handle, aux=len(node.value.encode('utf-8')))
            return slot
        if isinstance(node, ast.Ident):
            home = self.lookup(node.name)
            if dest is not None and dest != home:
                self.emit(OP_SAVE, a=dest, b=home)
                return dest
            return home
        if isinstance(node, ast.BinOp):
            lslot = self.compile_expr(node.left, dest=None)
            rslot = self.compile_expr(node.right, dest=None)
            slot = dest if dest is not None else self.new_slot()
            if node.op not in BINOP_OPCODE:
                raise CompileError(f'unsupported operator {node.op!r}')
            self.emit(BINOP_OPCODE[node.op], a=slot, b=lslot, c=rslot)
            return slot
        if isinstance(node, ast.UnaryOp):
            operand_slot = self.compile_expr(node.operand, dest=None)
            if node.op == '+':
                if dest is not None and dest != operand_slot:
                    self.emit(OP_SAVE, a=dest, b=operand_slot)
                    return dest
                return operand_slot
            slot = dest if dest is not None else self.new_slot()
            if slot != operand_slot:
                self.emit(OP_SAVE, a=slot, b=operand_slot)
            self.emit(UNARY_OPCODE[node.op], a=slot)
            return slot
        if isinstance(node, ast.Call):
            return self.compile_call(node, dest)
        if isinstance(node, ast.Assign):
            home = self.lookup(node.target.name)
            if node.op == '=':
                result = self.compile_assign_value(node.value, home)
            else:
                op_char = node.op[0]
                synthetic = ast.BinOp(op=op_char, left=node.target, right=node.value)
                result = self.compile_expr(synthetic, dest=home)
            if dest is not None and dest != result:
                self.emit(OP_SAVE, a=dest, b=result)
                return dest
            return result
        raise CompileError(f'unsupported expression {type(node).__name__}')

    def compile_call(self, node, dest):
        if node.name == 'NULL' and len(node.args) == 0:
            # Real OpenBOR scripts use NULL() as a zero-arg sentinel compared
            # via ==/!= (DODGE.C, PLAYER.C) against entity-handle-typed
            # values. VT_EMPTY looks like the obvious encoding but is WRONG:
            # Vm_LoadAndCompare (vm_string.pasm) only accepts a numeric pair
            # or a STR pair for EQ/NE -- comparing EMPTY against anything
            # faults VMERR_BAD_TYPE on real hardware (found running this
            # gate; the Python oracle doesn't enforce the same type check,
            # so this diverged silently there). Real OpenBOR's NULL is a C
            # NULL pointer (== 0); this project already represents entity
            # handles as plain VT_INTEGER (natives.py's own documented
            # scope decision, no VT_PTR), so NULL() must match that: a
            # VT_INTEGER 0, not VT_EMPTY. Same compile-time link/materialize
            # as any other literal, no native ID, no runtime instruction.
            # Caveat: this makes NULL() == entity index 0 (the player,
            # "self") -- same integer-vs-pointer collision already flagged
            # as a deliberate scope limit in natives.py, not new here.
            slot = dest if dest is not None else self.new_slot()
            self.set_slot(slot, VT_INTEGER, 0)
            return slot
        if node.name in self.local_functions:
            return self.compile_script_call(node, dest)
        specs = CALL_SPECIALIZATIONS.get(node.name)
        if not specs:
            raise CompileError(f'no native specialization registered for {node.name}()')
        matched = None
        for str_positions, native_name, passthrough_idx in specs:
            ok = True
            for pos, expected in str_positions.items():
                if pos >= len(node.args) or not isinstance(node.args[pos], ast.StringLit) \
                        or node.args[pos].value != expected:
                    ok = False
                    break
            if ok and len(node.args) == len(str_positions) + len(passthrough_idx):
                matched = (native_name, passthrough_idx)
                break
        if matched is None:
            raise CompileError(f'no matching specialization for call {node.name}({node.args!r})')
        native_name, passthrough_idx = matched
        stable_id, argc = NATIVE_BY_NAME[native_name]
        arg_slots = [self.compile_expr(node.args[i], dest=None) for i in passthrough_idx]
        assert argc == len(arg_slots)
        result_slot = dest if dest is not None else self.new_slot()
        arg_list_index = len(self._arg_slot_flat())
        callsite = Callsite(TARGET_KIND_NATIVE, argc, stable_id, result_slot, arg_slots, arg_list_index)
        self.m.callsites.append(callsite)
        callsite_idx = len(self.m.callsites) - 1
        self.emit(OP_CALL, a=0, b=result_slot, c=callsite_idx)
        self.m.natives_used.add(stable_id)
        return result_slot

    def compile_script_call(self, node, dest):
        callee = self.local_functions[node.name]
        if len(node.args) != len(callee.params):
            raise CompileError(
                f'{node.name}() expects {len(callee.params)} arg(s), got {len(node.args)}')
        # Evaluated in the CALLER's own (already-active) scope, exactly
        # like a native call's args -- PARAM in the callee reads them back
        # out of the frame's arg-slot table, not by name.
        arg_slots = [self.compile_expr(a, dest=None) for a in node.args]
        result_slot = dest if dest is not None else self.new_slot()
        arg_list_index = len(self._arg_slot_flat())
        callsite = Callsite(TARGET_KIND_SCRIPT, len(arg_slots), 0, result_slot,
                             arg_slots, arg_list_index)
        self.m.callsites.append(callsite)
        callsite_idx = len(self.m.callsites) - 1
        # operand a (entry IP) is unknown until the callee itself compiles;
        # backpatched in compile_program's final pass.
        instr_idx = self.emit(OP_CALL, a=0, b=result_slot, c=callsite_idx)
        self.pending_script_calls.append((instr_idx, node.name))
        return result_slot

    def _arg_slot_flat(self):
        flat = []
        for cs in self.m.callsites:
            flat.extend(cs.arg_slot_ids)
        return flat


def compile_module(program):
    c = Compiler()
    return c.compile_program(program)
