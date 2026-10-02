#!/usr/bin/env python3
"""Independent address-layout verifier for main.pasm — predicts where Poppy's
forward address-estimation pass gets a label's address WRONG, without
consulting main.sym for the answer.

Why this tool exists (and why audit_jumps.py/audit_ownership.py can't do
this): both of those tools check the *compiled binary* against main.sym.
main.sym is not independent ground truth — it is literally Poppy's own
pass-1 estimation output, produced by the exact estimator that has the
documented label-resolves-wrong bugs. When a label's real byte position
disagrees with main.sym, main.sym is doing the disagreeing, and any tool
that treats main.sym as truth cannot catch it (this was confirmed by
deliberate reproduction in the previous session -- see audit_ownership.py's
docstring and this project's poppy_assembler_bugs.md memory bug #8/#7).
This tool instead independently *recomputes* what each label's true byte
address should be, from Poppy's actual source-level estimation behavior
(read directly from E:\\gh\\SNES-CrimePatrol\\tools\\poppy-src), and reports
where that computed truth disagrees with what main.sym says Poppy believes.

============================================================================
THE MECHANISM (read Poppy.Core/Semantics/SemanticAnalyzer.cs and
Poppy.Core/CodeGen/CodeGenerator.cs yourself before doubting this — this
isn't inferred from symptoms, it's read directly from the two-pass
assembler's source)
============================================================================

Poppy is a two-pass assembler. Pass 1 (SemanticAnalyzer.Analyze, first
`program.Accept(this)` call) walks the AST once, and this is the ONLY pass
where label addresses are ever fixed: `VisitLabel` only calls
`SymbolTable.Define(...)` `if (_pass == 1)`. Pass 2 re-walks the AST to
resolve references (and fully expand macros) but never redefines a label's
address. `main.sym` is a dump of exactly these pass-1-frozen values.

Code generation (CodeGenerator.Generate) is a separate, later, single real
pass over the AST that actually emits bytes and tracks its OWN independent
`_currentAddress` counter. Its job is to advance that counter by the true
byte size of everything (real .incbin length, fully-expanded macros, etc.)
— it does NOT re-fix any label's stored address. So: whatever pass 1 (badly)
computed for a label's address is what every reference to that label uses
forever, even though the REAL byte stream (built by codegen) can legitimately
be laid out differently.

Three confirmed places pass 1 and codegen disagree on how many bytes
something occupies (found by reading the source, not just observing bugs):

  M1 — Unhandled directives cost 0 bytes in pass 1, real bytes in codegen.
       SemanticAnalyzer.VisitDirective's switch has NO case for "incbin"
       (also none for "asset"/"asset_manifest"/"align"/"pad" — CodeGenerator
       DOES handle all of these). Anything not in that switch falls to
       `default:` which only visits sub-expressions for symbol references —
       CurrentAddress is untouched. CodeGenerator.HandleIncbinDirective, by
       contrast, reads the real file and emits every byte, correctly
       advancing its own counter. Net effect: every label defined after an
       `.incbin` (or `.asset`/`.align`/`.pad`, though this project uses none
       of those) in the same `.org` region is frozen, in pass 1, at the
       address the incbin *started* at — the incbin's real length never
       gets added. This is exactly bug #8 (AnimRalfIdleFrames/WalkFrames/
       AttackFrames all reporting the identical address in main.sym).

  M2 — Macro invocations cost 0 bytes in pass 1, full expansion in codegen.
       `VisitMacroInvocation` in SemanticAnalyzer only expands the macro's
       body `if (_pass == 2)` — in pass 1 (where labels get fixed) a macro
       call contributes nothing. CodeGenerator always expands fully. This is
       bug #3, already fully avoided in this codebase (grep confirms zero
       live macro invocations anywhere in the shipping path — every
       `@Core_Error_Trigger` mention is a comment; every real call site
       inlines the macro's body by hand instead, specifically for this
       reason). Kept in this tool for defensive coverage if that ever
       changes.

  M3 — `Base + N` operand expressions silently skip the Absolute-to-
       AbsoluteLong size upgrade in pass 1, but get it in codegen.
       `SemanticAnalyzer.VisitInstruction` only widens an instruction's
       *effective* addressing mode (which affects its operand's byte size)
       when `TryGetConstantOperandValue(operand)` returns a value — and
       that helper explicitly only understands a bare `NumberLiteralNode`
       or a bare `IdentifierNode` of `SymbolType.Constant` (its own comment:
       "Does not resolve labels or anonymous references"). It has NO case
       for `BinaryExpressionNode` at all — so `Symbol + N` always returns
       null, and pass-1 sizing falls back to whatever the parser assigned by
       default: plain `Absolute` (2-byte operand), full stop, regardless of
       suffix. CodeGenerator, however, calls `_analyzer.EvaluateExpression`
       on the *whole* expression — which DOES evaluate `BinaryExpressionNode`
       — and if that resolves to a value > 0xFFFF, `ResolveAddressingMode`
       upgrades `Absolute` to `AbsoluteLong` (3-byte operand) for any
       mnemonic that has that encoding (LDA/STA/ADC/SBC/CMP/AND/ORA/EOR —
       *not* LSR/ROR, which have no long-addressing form to upgrade to,
       matching the memory's own "not LSR/ROR" note exactly). Net: pass 1
       sizes the instruction 1 byte short. This requires ALL of: (a) an
       offset expression, not a bare identifier (a bare EQU constant IS
       resolved correctly, since EQU symbols are `SymbolType.Constant`); (b)
       no explicit `.b`/`.w`/`.l` size suffix (an explicit suffix makes
       `GetOperandSize` return immediately, before the addressing-mode
       switch is even consulted — checked in both passes identically, so
       forcing a suffix always fixes this, matching poppy_assembler_bugs.md
       bug #1's documented fix); (c) the resolved value actually exceeding
       0xFFFF (true for any bank-$7E WRAM `symbol + N` reference, since a
       bank-$7E address is already > 0xFFFF before adding anything).

============================================================================
WHY A FULL PASS-1 REIMPLEMENTATION ISN'T NEEDED (and why this tool doesn't
attempt one — a from-scratch full estimator was the previous handoff's
original, larger, riskier idea)
============================================================================

`.org` sets `CurrentAddress` to an absolute value in BOTH the analyzer and
codegen. Drift from M1/M2/M3 can never cross an `.org` boundary — it always
resets to 0 there. And since `main.sym` already IS pass 1's frozen output,
this tool does not need to independently recompute every label's absolute
pass-1 address at all (that would mean re-simulating Poppy's entire sizing
behavior for every instruction type, and risking exactly the kind of
unmodeled-divergence bug this project's own tools have hit before). It only
needs the much smaller quantity: the running BYTE DRIFT (real bytes emitted
so far minus pass-1-counted bytes so far) since the last `.org`, which is
zero except immediately after an M1/M2/M3 event. A label's true address is
then simply `main.sym's reported address for that label + drift accumulated
so far in this .org region`. If drift is 0 at that point, main.sym is
already correct and this tool has nothing to add. If it's nonzero, main.sym
is provably wrong by exactly that amount, and this tool computed the
correction independently of main.sym.

============================================================================
SCOPED OUT — read before trusting a clean run
============================================================================

- Bug #2 (`.w` indexed access to a bank-$7E symbol drops the bank byte):
  both passes agree on the *size* (an explicit size suffix short-circuits
  `GetOperandSize` before addressing-mode resolution even runs), so there is
  no address-layout drift to detect — it corrupts the emitted VALUE, not the
  layout. Out of scope for a layout tool; still a real bug, still needs the
  `grep stz\.l` / never-use-`.w`-on-banked-symbols discipline documented in
  poppy_assembler_bugs.md.
- Bugs #5 and #6 (indexed long addressing to a data label computing a wrong
  base; a standalone `.dw` table resolving to garbage) have no identified
  Poppy-side mechanism even after reading this source — they are NOT known
  to be M1/M2/M3 and are NOT modeled here. A clean report from this tool
  says nothing about them.
- Indexed forms of M3 (`Base+N,x`) are deliberately not checked — only
  LDA/STA have a `long,X` encoding at all on 65816 and this tool does not
  have Poppy's own encoding table to confirm per-mnemonic availability, so
  guessing would risk a false negative that looks like a clean pass. Every
  real M3 case in this codebase's history (`LoadAudioData`'s
  `lda.l Tad_DataTable+3,x`) already uses an explicit `.l` anyway.
- Bare (no `+N`) references to a real code/data `Label:` are not checked for
  M3: those only matter if the label's own value exceeds 0xFFFF, which does
  not happen for any ROM label in this single-bank-0 project (all < $10000)
  — only bank-$7E *equates* (`Name = $7Ennnn`, `SymbolType.Constant`, always
  correctly resolved by `TryGetConstantOperandValue` even bare) reach that
  range, and those ARE handled correctly by Poppy even without `+N`.
- Bug #4 (a branch-target label resolving 1-2 bytes early) is a SEPARATE,
  unmodeled mechanism — it is NOT M3, and do not assume M3's "not LSR/ROR"
  coverage extends to it. This was checked, not just assumed: the one
  raw-byte-confirmed instance of bug #4 in this codebase (the `nop` guard
  immediately before `Anim_Play:`, main.pasm — removing it was proven, by
  rebuilding for real, to make `JSR Anim_Play` land 1 byte early on the
  previous routine's trailing RTS) is immediately preceded only by a long
  block of `EQU`-style constant definitions (the `ANIM_*` equates), which
  cost zero bytes in BOTH passes — there is no `Base+N` operand anywhere
  nearby for M3 to have mis-sized. The ~40 other `nop`-before-label guards
  scattered through this file are blanket prophylaxis, not per-site
  confirmations (the team adding them could not predict which sites were
  affected, so it pads all of them) — their density says nothing about
  where bug #4's real mechanism lives, and is not evidence it correlates
  with M1/M2/M3 sites either. Bug #4's actual mechanism remains
  unidentified after reading both SemanticAnalyzer.cs and
  CodeGenerator.cs, and this tool does NOT detect it.
- This tool's "0 drift" is stronger evidence than audit_ownership.py's
  "0 violations" specifically because it never asks main.sym for the
  answer — but it is still only as complete as M1/M2/M3 being the full list
  of estimation-vs-codegen divergences, and bug #4 above is proof that list
  is not exhaustive. A drift class this tool doesn't model (bug #4; or
  whatever actually produced the abandoned TAD-gap attempt's 13-byte JSR
  drift, which was never root-caused down to a specific mechanism since
  that code was reverted before this tool existed — plausibly bug #4 itself,
  but not confirmed) would not be caught. Do not treat a clean run here as
  blanket clearance for the TAD gap — only as clearance against these three
  specific, confirmed mechanisms. See "TAD gap reuse rule" below for the
  actual actionable takeaway.

============================================================================
TAD gap reuse rule (the actual reason this tool was built) — READ THIS
BEFORE REUSING THE TAD GAP, IT IS NARROWER THAN IT SOUNDS
============================================================================

Every `.incbin` in the CURRENT, working `main.pasm` is already the very
last content-producing statement in its `.org` region (verified below by
this tool finding zero referenced-and-drifted labels in the real build).
That discipline — large blobs go at the END of an `.org` region, with NO
label or code after them — is exactly what keeps M1 from ever mattering:
the only labels that ever drift are the blob labels themselves, and this
codebase already never references the drifted ones directly (it computes
their address as `first_blob_label + known_compile_time_offset` instead,
which is unaffected by where Poppy thinks the label is). Any new code
placed in the TAD gap ($8800-$AC00) should follow the identical rule:
put new data blobs last, with nothing after them, and re-run this tool
against the new layout before trusting it — it will directly show whether
any label ends up on the wrong side of an M1/M2/M3 drift-inducing statement.

IMPORTANT — what following this rule does NOT buy you: it makes the TAD
gap safe from M1 specifically. It does not make the TAD gap safe, full
stop. Bug #4 (see "SCOPED OUT" above) is a real, confirmed, unmodeled
mechanism this tool cannot see, and the abandoned TAD-gap attempt's
original 13-byte `JSR` drift was never root-caused to M1/M2/M3 or to
anything else — it is exactly as likely to be bug #4 as anything this
tool checks. A clean run from this tool against a new TAD-gap layout is
necessary but NOT sufficient before trusting it: also verify the actual
new call/branch targets by raw-byte disassembly (audit_jumps.py /
audit_ownership.py) and real Mesen2 behavioral testing, the same standing
rule this project applies everywhere else. Treating "this tool is clean"
as "the TAD gap is safe to reuse" would be repeating the previous
session's mistake of over-trusting a single checker — don't.

Usage:
    python verify_layout.py <main.pasm> <main.sym>
"""
import os
import re
import sys

LONG_CAPABLE = {'lda', 'sta', 'adc', 'sbc', 'cmp', 'and', 'ora', 'eor'}

LABEL_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*$')
EQU_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$')
ORG_RE = re.compile(r'^\.org\s+(\S+)', re.IGNORECASE)
BANK_RE = re.compile(r'^\.bank\b', re.IGNORECASE)
INCBIN_RE = re.compile(r'^\.incbin\s+"([^"]+)"', re.IGNORECASE)
INCLUDE_RE = re.compile(r'^\.include\s+"([^"]+)"', re.IGNORECASE)
ENUM_RE = re.compile(r'^\.enum\b', re.IGNORECASE)
ENDE_RE = re.compile(r'^\.ende\b', re.IGNORECASE)
MACRO_DEF_RE = re.compile(r'^\.macro\s+([A-Za-z_][A-Za-z0-9_]*)', re.IGNORECASE)
ENDMACRO_RE = re.compile(r'^\.endmacro\b', re.IGNORECASE)
MACRO_INVOKE_RE = re.compile(r'^@([A-Za-z_][A-Za-z0-9_]*)\b(.*)$')
INSN_RE = re.compile(r'^([A-Za-z]{2,4})(\.[bwl])?\s+(.+)$', re.IGNORECASE)
BASE_OFFSET_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*([+\-])\s*(.+)$')
INDEXED_SUFFIX_RE = re.compile(r'^(.*?)\s*,\s*[xXyYsS]\s*$')


# ============================================================================
# MECHANISM SWITCHES -- READ BEFORE TRUSTING A CLEAN RUN
# ============================================================================
# Everything above describes the assembler as it behaved through 2026-08-17.
# On 2026-08-18 all three mechanisms were fixed in the astrobleem/poppy fork,
# so all three contribute 0 bytes of drift now and this tool passes trivially:
#
#   M1 -- SemanticAnalyzer.VisitDirective now has an "incbin" case that stats
#         the file (honouring the optional offset/length args) and advances
#         CurrentAddress, mirroring CodeGenerator.HandleIncbinDirective
#         (poppy#384).
#   M2 -- macro expansion now runs in BOTH analyzer passes, not just pass 2,
#         so an invocation is sized in pass 1. (This codebase has no live
#         invocations either way.)
#   M3 -- TryGetConstantOperandValue gained a BinaryExpressionNode case, so
#         "Base + N" resolves and gets the Absolute->AbsoluteLong upgrade in
#         pass 1 (poppy#376).
#
# The surviving ground-truth layout check is check_label_drift.py, which reads
# the emitted bytes rather than modelling the analyzer: it asserts the byte at
# each label is the opcode the source puts there. Prefer it.
#
# Set any switch below back to True to re-arm this tool if a regression puts
# the corresponding mechanism back. The detection code is all still here and
# still reports the statements it saw; only the drift accumulation is gated.
# NOTE: with all three False this tool compares main.sym to main.sym and
# reports "0 drifted" unconditionally. Its PASS line inside audit_all.py's
# ALL CHECKS PASS is therefore NOT evidence of anything -- it is a parked
# detector, kept for its documentation and for one-edit re-arming.
M1_INCBIN_SIZED_ZERO = False
M2_MACRO_SIZED_ZERO = False
M3_BASE_OFFSET_NOT_WIDENED = False


def strip_comment(line):
    in_quotes = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ';' and not in_quotes:
            return line[:i]
    return line


def parse_int(tok):
    tok = tok.strip()
    if tok.startswith('$'):
        return int(tok[1:], 16)
    if tok.lower().startswith('0x'):
        return int(tok, 16)
    try:
        return int(tok, 10)
    except ValueError:
        return int(tok, 16)


class SafeEval:
    """Tiny, deliberately conservative expression evaluator for offset
    expressions in M3 detection. Only +, -, *, parens, $hex/decimal
    literals, and identifiers already known to `symtab`. Returns None
    (never raises, never guesses) on anything it doesn't recognize --
    an unresolvable offset is reported as "not statically checked", not
    silently treated as 0."""

    def __init__(self, symtab):
        self.symtab = symtab

    def eval(self, expr):
        expr = expr.strip()
        try:
            return self._eval_sum(expr, 0)[0]
        except (ValueError, KeyError, IndexError):
            return None

    def _eval_sum(self, s, i):
        val, i = self._eval_term(s, i)
        while i < len(s) and s[i] in '+-':
            op = s[i]
            rhs, i = self._eval_term(s, i + 1)
            val = val + rhs if op == '+' else val - rhs
        return val, i

    def _eval_term(self, s, i):
        val, i = self._eval_atom(s, i)
        while i < len(s) and s[i] == '*':
            rhs, i = self._eval_atom(s, i + 1)
            val = val * rhs
        return val, i

    def _eval_atom(self, s, i):
        while i < len(s) and s[i] == ' ':
            i += 1
        if i < len(s) and s[i] == '(':
            val, i = self._eval_sum(s, i + 1)
            while i < len(s) and s[i] == ' ':
                i += 1
            if i >= len(s) or s[i] != ')':
                raise ValueError('unbalanced parens')
            return val, i + 1
        m = re.match(r'\$[0-9A-Fa-f]+', s[i:])
        if m:
            return int(m.group(0)[1:], 16), i + m.end()
        m = re.match(r'\d+', s[i:])
        if m:
            return int(m.group(0)), i + m.end()
        m = re.match(r'[A-Za-z_][A-Za-z0-9_]*', s[i:])
        if m:
            name = m.group(0)
            if name not in self.symtab:
                raise KeyError(name)
            return self.symtab[name], i + m.end()
        raise ValueError(f'unrecognized token at {s[i:]!r}')


def load_sym(sym_path):
    symtab = {}
    dupes = []
    pattern = re.compile(r'([0-9A-Fa-f]{2}):([0-9A-Fa-f]+)\s+(\S+)')
    with open(sym_path, encoding='utf-8-sig') as f:
        for line in f:
            m = pattern.match(line.strip())
            if not m:
                continue
            _bank, addr_s, name = m.groups()
            addr = int(addr_s, 16)
            if name in symtab and symtab[name] != addr:
                dupes.append((name, symtab[name], addr))
            symtab.setdefault(name, addr)
    return symtab, dupes


def flatten_source(main_path):
    """Splice .include directives inline. Returns a list of
    (stripped_line, source_file, lineno) in final source order, matching
    Poppy's own .incbin path resolution (relative to the file the
    directive actually appears in, not the top-level file)."""
    out = []

    def process(path, stack):
        path = os.path.abspath(path)
        if path in stack:
            raise RuntimeError(f'circular .include: {path}')
        with open(path, encoding='utf-8-sig') as f:
            for lineno, raw in enumerate(f, 1):
                line = strip_comment(raw).rstrip()
                stripped = line.strip()
                if not stripped:
                    continue
                m = INCLUDE_RE.match(stripped)
                if m:
                    inc_path = os.path.join(os.path.dirname(path), m.group(1))
                    process(inc_path, stack + [path])
                    continue
                out.append((stripped, path, lineno))

    process(main_path, [])
    return out


SIMPLE_SIZES = {
    'nop': 1, 'rts': 1, 'rtl': 1, 'rti': 1, 'php': 1, 'plp': 1, 'pha': 1,
    'pla': 1, 'phx': 1, 'plx': 1, 'phy': 1, 'ply': 1, 'phb': 1, 'plb': 1,
    'phd': 1, 'pld': 1, 'phk': 1, 'tax': 1, 'tay': 1, 'txa': 1, 'tya': 1,
    'tsx': 1, 'txs': 1, 'tcd': 1, 'tdc': 1, 'tcs': 1, 'tsc': 1, 'txy': 1,
    'tyx': 1, 'xba': 1, 'xce': 1, 'clc': 1, 'sec': 1, 'cli': 1, 'sei': 1,
    'clv': 1, 'cld': 1, 'sed': 1, 'stp': 1, 'wai': 1, 'brk': 2,
    'pea': 3, 'per': 3, 'jsr': 3, 'jmp': 3, 'jsl': 4, 'jml': 4,
    'rep': 2, 'sep': 2,
    'bcc': 2, 'bcs': 2, 'beq': 2, 'bne': 2, 'bpl': 2, 'bmi': 2,
    'bvc': 2, 'bvs': 2, 'bra': 2, 'brl': 3,
}


def size_macro_body(body_lines, macro_name):
    """Best-effort real-emitted-size estimate for a macro body, for M2
    drift math if a live invocation is ever found. Deliberately refuses to
    guess: returns None (with a reason) for anything not in SIMPLE_SIZES,
    rather than silently under/over-counting."""
    total = 0
    for line in body_lines:
        m = INSN_RE.match(line)
        if not m:
            continue
        mnem = m.group(1).lower()
        if mnem in SIMPLE_SIZES:
            total += SIMPLE_SIZES[mnem]
        else:
            return None, f'macro {macro_name}: cannot statically size {mnem!r} (no suffix/immediate-width table) -- manual audit needed'
    return total, None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    main_pasm, sym_path = sys.argv[1], sys.argv[2]

    symtab, dupes = load_sym(sym_path)
    evaluator = SafeEval(symtab)
    lines = flatten_source(main_pasm)

    # Pre-scan: collect .macro/.endmacro body text so a later @invocation
    # (M2) can be sized. No live invocations exist in this codebase today;
    # this is defensive coverage for if that ever changes.
    macro_bodies = {}
    i = 0
    while i < len(lines):
        stripped, _f, _ln = lines[i]
        m = MACRO_DEF_RE.match(stripped)
        if m:
            name = m.group(1)
            body = []
            i += 1
            while i < len(lines) and not ENDMACRO_RE.match(lines[i][0]):
                body.append(lines[i][0])
                i += 1
            macro_bodies[name] = body
        i += 1

    org_base = None
    drift = 0
    in_enum = False
    in_macro_def = False
    region_labels = []   # (name, sym_addr, predicted_real, drift_here, file, lineno)
    all_regions = []     # (org_base, region_labels)
    m3_hits = []
    m2_hits = []
    unsizable_macros = set()
    sym_used = {}  # name -> count of textual references outside its own def line

    full_text_lines = [l for l, _f, _ln in lines]

    def note_region_end():
        if org_base is not None:
            all_regions.append((org_base, region_labels[:]))

    for stripped, srcfile, lineno in lines:
        if ENUM_RE.match(stripped):
            in_enum = True
            continue
        if ENDE_RE.match(stripped):
            in_enum = False
            continue
        if in_enum:
            continue

        if MACRO_DEF_RE.match(stripped):
            in_macro_def = True
            continue
        if ENDMACRO_RE.match(stripped):
            in_macro_def = False
            continue
        if in_macro_def:
            continue

        m = ORG_RE.match(stripped)
        if m:
            note_region_end()
            org_base = parse_int(m.group(1))
            drift = 0
            region_labels = []
            continue

        if BANK_RE.match(stripped):
            continue

        m = LABEL_RE.match(stripped)
        if m:
            name = m.group(1)
            sym_addr = symtab.get(name)
            if sym_addr is not None and org_base is not None:
                predicted_real = sym_addr + drift
                region_labels.append((name, sym_addr, predicted_real, drift, srcfile, lineno))
            continue

        if INCBIN_RE.match(stripped):
            m = INCBIN_RE.match(stripped)
            inc_path = os.path.join(os.path.dirname(srcfile), m.group(1))
            try:
                real_len = os.path.getsize(inc_path)
            except OSError as e:
                print(f'WARNING: {srcfile}:{lineno}: cannot stat incbin {inc_path}: {e}', file=sys.stderr)
                continue
            if M1_INCBIN_SIZED_ZERO:
                drift += real_len  # pass1 counted 0, codegen emits real_len
            continue

        m = MACRO_INVOKE_RE.match(stripped)
        if m:
            name = m.group(1)
            if name in macro_bodies:
                size, reason = size_macro_body(macro_bodies[name], name)
                if size is None:
                    unsizable_macros.add(reason)
                else:
                    if M2_MACRO_SIZED_ZERO:
                        drift += size  # pass1 counted 0, codegen expands fully
                    m2_hits.append((name, size, srcfile, lineno))
            continue

        m = EQU_RE.match(stripped)
        if m:
            continue  # 0 bytes in both passes, nothing to track

        # M3 check: Base +/- Offset feeding a long-capable mnemonic with no
        # explicit size suffix.
        m = INSN_RE.match(stripped)
        if m:
            mnem = m.group(1).lower()
            suffix = m.group(2)
            operand = m.group(3).strip()
            im = INDEXED_SUFFIX_RE.match(operand)
            if im:
                operand = None  # indexed forms out of scope, see docstring
            if operand and not suffix and mnem in LONG_CAPABLE:
                bm = BASE_OFFSET_RE.match(operand)
                if bm:
                    base, sign, off_expr = bm.groups()
                    base_val = symtab.get(base)
                    off_val = evaluator.eval(off_expr)
                    if base_val is not None and off_val is not None:
                        combined = base_val + off_val if sign == '+' else base_val - off_val
                        if combined > 0xFFFF:
                            if M3_BASE_OFFSET_NOT_WIDENED:
                                drift += 1  # pass1 sized Absolute(2), codegen AbsoluteLong(3)
                            m3_hits.append((mnem, operand, combined, srcfile, lineno))

    note_region_end()

    # Cross-reference: is a drifted label actually referenced elsewhere?
    word_re_cache = {}

    def count_refs(name):
        if name in word_re_cache:
            pat = word_re_cache[name]
        else:
            pat = re.compile(r'\b' + re.escape(name) + r'\b')
            word_re_cache[name] = pat
        count = 0
        for text in full_text_lines:
            for _ in pat.finditer(text):
                count += 1
        return count  # includes the label's own definition line (1)

    print(f'{len(symtab)} symbols loaded from {sym_path}')
    if dupes:
        print(f'NOTE: {len(dupes)} symbol name(s) redefined with different values while loading sym (last wins in lookup) -- unexpected, check {sym_path} manually:')
        for name, old, new in dupes[:10]:
            print(f'  {name}: {hex(old)} vs {hex(new)}')
    print()

    total_labels = 0
    total_drifted = 0
    total_live_bugs = 0
    for org_base, region_labels in all_regions:
        if not region_labels:
            continue
        drifted = [r for r in region_labels if r[3] != 0]
        print(f'.org {hex(org_base)}  ({len(region_labels)} labels, {len(drifted)} drifted)')
        for name, sym_addr, predicted_real, drift_here, srcfile, lineno in region_labels:
            total_labels += 1
            if drift_here == 0:
                continue
            total_drifted += 1
            refs = count_refs(name)
            live = refs > 1
            if live:
                total_live_bugs += 1
            status = 'REFERENCED ELSEWHERE -- LIKELY LIVE BUG' if live else 'not referenced elsewhere (benign, matches offset-from-first-label workaround pattern)'
            print(f'  {name}: main.sym says {hex(sym_addr)}, predicted real address {hex(predicted_real)} '
                  f'(drift {drift_here:+d}) -- {status}')
            print(f'    defined at {os.path.basename(srcfile)}:{lineno}')
        print()

    if m3_hits:
        print(f'{len(m3_hits)} M3 (Absolute->AbsoluteLong pass1/codegen size mismatch) hit(s):')
        for mnem, operand, combined, srcfile, lineno in m3_hits:
            print(f'  {mnem} {operand} (resolves to {hex(combined)}) at {os.path.basename(srcfile)}:{lineno} -- missing .l suffix')
        print()

    if m2_hits:
        print(f'{len(m2_hits)} macro invocation(s) sized for M2 drift:')
        for name, size, srcfile, lineno in m2_hits:
            print(f'  @{name} ({size} real bytes) at {os.path.basename(srcfile)}:{lineno}')
        print()

    if unsizable_macros:
        print('Macro invocations found that this tool could not size (manual audit needed):')
        for reason in sorted(unsizable_macros):
            print(f'  {reason}')
        print()

    print(f'SUMMARY: {total_labels} labels checked, {total_drifted} drifted from main.sym, '
          f'{total_live_bugs} referenced elsewhere (live bugs), '
          f'{total_drifted - total_live_bugs} unreferenced (benign).')
    if total_live_bugs:
        print('UNSAFE: at least one drifted label is directly referenced -- main.sym is '
              'wrong for it and every reference embeds the wrong address. Fix before shipping.')
        raise SystemExit(1)
    print('No drifted-and-referenced labels found under the M1/M2/M3 model '
          '(see docstring for what this does and does not cover).')


if __name__ == '__main__':
    main()
