"""Recursive-descent parser for the openborscript C-subset (plan_vm.md §8).

Grammar (subset chosen to cover real Build-4400+ mod scripts without
reimplementing full C -- no structs, no arrays, no pointers-as-arithmetic,
no switch, no ternary, no bitwise-NOT since BIT_NOT is outside the Build
4086-era ABI per SOURCES.md):

    program    := funcdecl*
    funcdecl   := type IDENT '(' (param (',' param)*)? ')' block
    param      := type IDENT
    block      := '{' stmt* '}'
    stmt       := vardecl ';' | if_stmt | while_stmt | return_stmt ';'
                | expr_stmt ';' | block | ';'
    vardecl    := type IDENT ('=' expr)? (',' IDENT ('=' expr)?)*
    if_stmt    := 'if' '(' expr ')' stmt ('else' stmt)?
    while_stmt := 'while' '(' expr ')' stmt
    return_stmt:= 'return' expr?
    expr_stmt  := expr
    expr       := assignment
    assignment := logical_or (('='|'+='|'-='|'*='|'/=') assignment)?
    ... standard C precedence chain down to primary
    primary    := INT | FLOAT | STRING | IDENT ('(' args? ')')?
                | '(' expr ')' | ('++'|'--') IDENT | IDENT ('++'|'--')
"""
from . import ast_nodes as ast
from .lexer import tokenize, LexError

TYPE_KEYWORDS = {'void', 'int', 'float', 'char', 'long', 'double'}


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens, filename='<script>'):
        self.toks = tokens
        self.i = 0
        self.filename = filename

    def peek(self, off=0):
        return self.toks[min(self.i + off, len(self.toks) - 1)]

    def at(self, kind):
        return self.peek().kind == kind

    def at_type_kw(self):
        t = self.peek()
        if t.kind in TYPE_KEYWORDS:
            return True
        return False

    def advance(self):
        t = self.toks[self.i]
        if self.i < len(self.toks) - 1:
            self.i += 1
        return t

    def expect(self, kind):
        t = self.peek()
        if t.kind != kind:
            raise ParseError(f'{self.filename}:{t.line}: expected {kind!r}, got {t.kind!r} ({t.text!r})')
        return self.advance()

    def is_char_star_type(self):
        # 'char' '*' IDENT  -- treat char* as a single type token pair.
        return self.at('char') and self.peek(1).text == '*'

    def parse_type(self):
        if self.is_char_star_type():
            self.advance()
            self.advance()
            return 'char*'
        t = self.advance()
        return t.kind

    def parse_program(self):
        funcs = []
        while not self.at('EOF'):
            funcs.append(self.parse_funcdecl())
        return ast.Program(functions=funcs)

    def parse_funcdecl(self):
        ret_type = self.parse_type()
        name = self.expect('IDENT').text
        self.expect('(')
        params = []
        if not self.at(')'):
            params.append(self.parse_param())
            while self.at(','):
                self.advance()
                params.append(self.parse_param())
        self.expect(')')
        body = self.parse_block()
        return ast.FuncDecl(ret_type=ret_type, name=name, params=params, body=body)

    def parse_param(self):
        t = self.parse_type()
        name = self.expect('IDENT').text
        return (t, name)

    def parse_block(self):
        self.expect('{')
        stmts = []
        while not self.at('}'):
            stmts.append(self.parse_stmt())
        self.expect('}')
        return ast.Block(stmts=stmts)

    def parse_stmt(self):
        t = self.peek()
        if t.kind == '{':
            return self.parse_block()
        if t.kind == ';':
            self.advance()
            return ast.Block(stmts=[])
        if t.kind == 'if':
            return self.parse_if()
        if t.kind == 'while':
            return self.parse_while()
        if t.kind == 'return':
            self.advance()
            value = None
            if not self.at(';'):
                value = self.parse_expr()
            self.expect(';')
            return ast.Return(value=value)
        if self.at_type_kw():
            decls = self.parse_vardecl()
            self.expect(';')
            return decls
        expr = self.parse_expr()
        self.expect(';')
        return ast.ExprStmt(expr=expr)

    def parse_vardecl(self):
        var_type = self.parse_type()
        items = []
        name = self.expect('IDENT').text
        init = None
        if self.at('='):
            self.advance()
            init = self.parse_expr()
        items.append(ast.VarDecl(var_type=var_type, name=name, init=init))
        while self.at(','):
            self.advance()
            name = self.expect('IDENT').text
            init = None
            if self.at('='):
                self.advance()
                init = self.parse_expr()
            items.append(ast.VarDecl(var_type=var_type, name=name, init=init))
        if len(items) == 1:
            return items[0]
        return ast.Block(stmts=items)

    def parse_if(self):
        self.expect('if')
        self.expect('(')
        cond = self.parse_expr()
        self.expect(')')
        then = self.parse_stmt()
        els = None
        if self.at('else'):
            self.advance()
            els = self.parse_stmt()
        return ast.If(cond=cond, then=then, els=els)

    def parse_while(self):
        self.expect('while')
        self.expect('(')
        cond = self.parse_expr()
        self.expect(')')
        body = self.parse_stmt()
        return ast.While(cond=cond, body=body)

    def parse_expr(self):
        return self.parse_assignment()

    ASSIGN_OPS = {'=', '+=', '-=', '*=', '/='}

    def parse_assignment(self):
        left = self.parse_logical_or()
        if self.peek().kind in self.ASSIGN_OPS:
            op = self.advance().text
            value = self.parse_assignment()
            if not isinstance(left, ast.Ident):
                raise ParseError(f'{self.filename}:{self.peek().line}: assignment target must be an identifier')
            return ast.Assign(target=left, op=op, value=value)
        return left

    def _binop_level(self, next_level, ops):
        left = next_level()
        while self.peek().kind in ops:
            op = self.advance().text
            right = next_level()
            left = ast.BinOp(op=op, left=left, right=right)
        return left

    def parse_logical_or(self):
        return self._binop_level(self.parse_logical_and, {'||'})

    def parse_logical_and(self):
        return self._binop_level(self.parse_bitor, {'&&'})

    def parse_bitor(self):
        return self._binop_level(self.parse_bitxor, {'|'})

    def parse_bitxor(self):
        return self._binop_level(self.parse_bitand, {'^'})

    def parse_bitand(self):
        return self._binop_level(self.parse_equality, {'&'})

    def parse_equality(self):
        return self._binop_level(self.parse_relational, {'==', '!='})

    def parse_relational(self):
        return self._binop_level(self.parse_shift, {'<', '<=', '>', '>='})

    def parse_shift(self):
        return self._binop_level(self.parse_additive, {'<<', '>>'})

    def parse_additive(self):
        return self._binop_level(self.parse_multiplicative, {'+', '-'})

    def parse_multiplicative(self):
        return self._binop_level(self.parse_unary, {'*', '/', '%'})

    def parse_unary(self):
        t = self.peek()
        if t.kind in ('-', '+', '!'):
            self.advance()
            operand = self.parse_unary()
            return ast.UnaryOp(op=t.text, operand=operand)
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        # ++/-- as statement-level sugar: desugar to Assign(x, '+=', 1)
        if self.peek().kind in ('++', '--') and isinstance(node, ast.Ident):
            op = self.advance().text
            return ast.Assign(target=node, op='+=' if op == '++' else '-=', value=ast.IntLit(value=1))
        return node

    def parse_primary(self):
        t = self.peek()
        if t.kind == 'INT':
            self.advance()
            return ast.IntLit(value=int(t.text))
        if t.kind == 'FLOAT':
            self.advance()
            return ast.FloatLit(value=float(t.text))
        if t.kind == 'STRING':
            self.advance()
            return ast.StringLit(value=_unescape(t.text[1:-1]))
        if t.kind == 'IDENT':
            self.advance()
            if self.at('('):
                self.advance()
                args = []
                if not self.at(')'):
                    args.append(self.parse_expr())
                    while self.at(','):
                        self.advance()
                        args.append(self.parse_expr())
                self.expect(')')
                return ast.Call(name=t.text, args=args)
            return ast.Ident(name=t.text)
        if t.kind == '(':
            self.advance()
            e = self.parse_expr()
            self.expect(')')
            return e
        raise ParseError(f'{self.filename}:{t.line}: unexpected token {t.kind!r} ({t.text!r})')


def _unescape(s):
    return s.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')


def parse_source(src, filename='<script>'):
    tokens = tokenize(src, filename)
    p = Parser(tokens, filename)
    return p.parse_program()
