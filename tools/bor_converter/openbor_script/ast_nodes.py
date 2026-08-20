"""AST node types for the openborscript C-subset parser."""


class Node:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __repr__(self):
        cls = type(self).__name__
        fields = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'{cls}({fields})'


class Program(Node):
    pass  # functions: list[FuncDecl]


class FuncDecl(Node):
    pass  # ret_type, name, params: list[(type,name)], body: Block


class Block(Node):
    pass  # stmts: list[Node]


class VarDecl(Node):
    pass  # var_type, name, init: Node|None


class If(Node):
    pass  # cond, then, els


class While(Node):
    pass  # cond, body


class Return(Node):
    pass  # value: Node|None


class ExprStmt(Node):
    pass  # expr


class Assign(Node):
    pass  # target (Ident), op ('=' or desugared), value


class BinOp(Node):
    pass  # op, left, right


class UnaryOp(Node):
    pass  # op, operand


class Call(Node):
    pass  # name, args: list[Node]


class Ident(Node):
    pass  # name


class IntLit(Node):
    pass  # value


class FloatLit(Node):
    pass  # value


class StringLit(Node):
    pass  # value
