"""Lexer for the openborscript C-subset (plan_vm.md §8).

Handles exactly the token classes real Build-4400+-era mod scripts use:
identifiers/keywords, decimal int/float literals, double-quoted strings,
the operator/punctuation set the 48-opcode ABI can express, and // and /* */
comments. No preprocessor here (see preprocess.py) -- this lexes one already
-expanded translation unit.
"""
import re

KEYWORDS = {
    'void', 'int', 'float', 'char', 'long', 'double',
    'if', 'else', 'while', 'for', 'return', 'break', 'continue',
}

TOKEN_SPEC = [
    ('WS', r'[ \t\r\n]+'),
    ('LCOMMENT', r'//[^\n]*'),
    ('BCOMMENT', r'/\*.*?\*/'),
    ('FLOAT', r'\d+\.\d+([eE][+-]?\d+)?'),
    ('INT', r'\d+'),
    ('STRING', r'"(?:[^"\\]|\\.)*"'),
    ('IDENT', r'[A-Za-z_][A-Za-z0-9_]*'),
    ('OP', r'==|!=|<=|>=|&&|\|\||<<|>>|\+\+|--|\+=|-=|\*=|/=|[-+*/%=<>!&|^~,;(){}\[\].]'),
]
MASTER_RE = re.compile('|'.join(f'(?P<{n}>{p})' for n, p in TOKEN_SPEC), re.DOTALL)


class Token:
    __slots__ = ('kind', 'text', 'pos', 'line')

    def __init__(self, kind, text, pos, line):
        self.kind = kind
        self.text = text
        self.pos = pos
        self.line = line

    def __repr__(self):
        return f'Token({self.kind!r}, {self.text!r}, line={self.line})'


class LexError(Exception):
    pass


def tokenize(src, filename='<script>'):
    tokens = []
    line = 1
    i = 0
    n = len(src)
    while i < n:
        m = MASTER_RE.match(src, i)
        if not m:
            snippet = src[i:i + 20].splitlines()[0] if src[i:i + 20] else ''
            raise LexError(f'{filename}:{line}: unexpected character {src[i]!r} near {snippet!r}')
        kind = m.lastgroup
        text = m.group()
        if kind in ('WS', 'LCOMMENT', 'BCOMMENT'):
            line += text.count('\n')
            i = m.end()
            continue
        if kind == 'IDENT' and text in KEYWORDS:
            kind = text
        if kind == 'OP':
            kind = text
        tokens.append(Token(kind, text, i, line))
        line += text.count('\n')
        i = m.end()
    tokens.append(Token('EOF', '', n, line))
    return tokens
