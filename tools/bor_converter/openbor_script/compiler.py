"""Semantic pass + codegen: openborscript AST -> revision-1 module IR
(plan_vm.md §8, FORMAT.md). Produces plain Python structures; module.py packs
them into the actual binary per FORMAT.md.

Scope: compiles exactly one function (the first FuncDecl in the program) as
the module's entry_main, treating it as a root program -- no CALL/PARAM
frame is synthesized for the function's own parameters. A standalone test
harness (vm_gate6.py) instead bakes fixed test values directly into those
parameter slots' *initial* values, the same pattern Gate 0-5's own fixtures
already use for CONSTINT-style preinitialized slots. This sidesteps
synthesizing a fake outer caller for a script that, in a real mod, would be
invoked by the engine with real arguments -- the compiled instruction
stream for the function body itself is unmodified/real either way.

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
OP_RET = 43

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
        fn = program.functions[0]
        self.m.entry_main = 0
        for ptype, pname in fn.params:
            slot = self.new_slot(vtype=self._default_type_for(ptype), name=pname)
            self.m.param_names.append((pname, slot, ptype))
        self.compile_block(fn.body)
        if not self.m.instructions or self.m.instructions[-1].op != OP_RET:
            self.emit(OP_RET)
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
            if node.value is not None:
                self.compile_expr(node.value, dest=None)
            self.emit(OP_RET)
        elif isinstance(node, ast.If):
            self.compile_if(node)
        elif isinstance(node, ast.While):
            self.compile_while(node)
        else:
            raise CompileError(f'unsupported statement {type(node).__name__}')

    def compile_vardecl(self, node):
        home = self.new_slot(vtype=self._default_type_for(node.var_type), name=node.name)
        if node.init is not None:
            self.compile_expr(node.init, dest=home)

    def compile_assign(self, node):
        home = self.lookup(node.target.name)
        if node.op == '=':
            self.compile_expr(node.value, dest=home)
        else:
            op_char = node.op[0]
            synthetic = ast.BinOp(op=op_char, left=node.target, right=node.value)
            self.compile_expr(synthetic, dest=home)

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
        if getattr(self, '_false_slot_cache', None) is None:
            self._false_slot_cache = self.new_slot(vtype=VT_INTEGER, value=0)
        return self._false_slot_cache

    def compile_while(self, node):
        loop_start = len(self.m.instructions)
        cond_slot = self.compile_expr(node.cond, dest=None)
        branch_idx = self.emit(OP_BRANCH_FALSE, a=0, b=cond_slot)
        self.compile_stmt(node.body)
        # unconditional back-edge: Branch_FALSE on the constant-false slot
        self.emit(OP_BRANCH_FALSE, a=loop_start, b=self._false_slot())
        self.m.instructions[branch_idx].a = len(self.m.instructions)

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
                result = self.compile_expr(node.value, dest=home)
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

    def _arg_slot_flat(self):
        flat = []
        for cs in self.m.callsites:
            flat.extend(cs.arg_slot_ids)
        return flat


def compile_module(program):
    c = Compiler()
    return c.compile_program(program)
