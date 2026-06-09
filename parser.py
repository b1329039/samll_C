"""
Small-C Parser
遞迴下降解析器，將 token 串建成 AST（抽象語法樹）。

運算子優先順序（低 → 高）：
  13: = += -= *= /= %=   (右結合)
  12: ||
  11: &&
  10: |
   9: ^
   8: &
   7: == !=
   6: < <= > >=
   5: << >>
   4: + -
   3: * / %
   2: 前綴一元 - ! ~ * &  (右結合)
   1: 後綴 () [] (最高)
"""

from lexer import TokenType as T, Token

# ─────────────────────────── AST 節點 ───────────────────────────

class Node:
    """所有 AST 節點的基底類別"""
    pass

# ── 表達式 ──
class IntLit(Node):
    def __init__(self, value, line=0):
        self.value = value
        self.line  = line

class CharLit(Node):
    def __init__(self, value, line=0):
        self.value = value   # int (ASCII)
        self.line  = line

class StrLit(Node):
    def __init__(self, value, line=0):
        self.value = value   # Python str
        self.line  = line

class Ident(Node):
    def __init__(self, name, line=0):
        self.name = name
        self.line = line

class BinOp(Node):
    def __init__(self, op, left, right, line=0):
        self.op    = op
        self.left  = left
        self.right = right
        self.line  = line

class UnaryOp(Node):
    def __init__(self, op, operand, line=0):
        self.op      = op
        self.operand = operand
        self.line    = line

class Assign(Node):
    def __init__(self, target, value, op='=', line=0):
        self.target = target
        self.value  = value
        self.op     = op      # '=' '+=' '-=' '*=' '/=' '%='
        self.line   = line

class ArrayIndex(Node):
    def __init__(self, array, index, line=0):
        self.array = array
        self.index = index
        self.line  = line

class FuncCall(Node):
    def __init__(self, name, args, line=0):
        self.name = name
        self.args = args
        self.line = line

# ── 陳述句 ──
class ExprStmt(Node):
    def __init__(self, expr, line=0):
        self.expr = expr
        self.line = line

class VarDecl(Node):
    def __init__(self, dtype, name, init=None, size=None, is_ptr=False, line=0):
        self.dtype  = dtype    # 'int' | 'char'
        self.name   = name
        self.init   = init     # 初始值表達式 (optional)
        self.size   = size     # 陣列大小 (optional)
        self.is_ptr = is_ptr   # 是否為指標
        self.line   = line

class Block(Node):
    def __init__(self, stmts, line=0):
        self.stmts = stmts
        self.line  = line

class IfStmt(Node):
    def __init__(self, cond, then_branch, else_branch=None, line=0):
        self.cond        = cond
        self.then_branch = then_branch
        self.else_branch = else_branch
        self.line        = line

class WhileStmt(Node):
    def __init__(self, cond, body, line=0):
        self.cond = cond
        self.body = body
        self.line = line

class ForStmt(Node):
    def __init__(self, init, cond, update, body, line=0):
        self.init   = init
        self.cond   = cond
        self.update = update
        self.body   = body
        self.line   = line

class DoWhileStmt(Node):
    def __init__(self, body, cond, line=0):
        self.body = body
        self.cond = cond
        self.line = line

class BreakStmt(Node):
    def __init__(self, line=0): self.line = line

class ContinueStmt(Node):
    def __init__(self, line=0): self.line = line

class ReturnStmt(Node):
    def __init__(self, value=None, line=0):
        self.value = value
        self.line  = line

# ── 頂層 ──
class FuncDef(Node):
    def __init__(self, rtype, name, params, body, line=0):
        self.rtype  = rtype    # 'int' | 'char' | 'void'
        self.name   = name
        self.params = params   # list of (dtype, is_ptr, name)
        self.body   = body     # Block
        self.line   = line

class Define(Node):
    def __init__(self, name, value_str, line=0):
        self.name      = name
        self.value_str = value_str
        self.line      = line

class Program(Node):
    def __init__(self, decls):
        self.decls = decls   # list of FuncDef | VarDecl | Define


# ─────────────────────────── 例外 ───────────────────────────

class ParseError(Exception):
    def __init__(self, msg, line=0):
        super().__init__(msg)
        self.line = line


# ─────────────────────────── Parser ───────────────────────────

class Parser:
    def __init__(self, tokens, defines=None):
        self.tokens  = tokens
        self.pos     = 0
        self.defines = defines or {}   # name → int 值（前處理結果）

    # ── 工具方法 ──

    def peek(self, offset=0):
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def advance(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def check(self, *types):
        return self.peek().type in types

    def match(self, *types):
        if self.check(*types):
            return self.advance()
        return None

    def expect(self, ttype, msg=None):
        tok = self.peek()
        if tok.type != ttype:
            raise ParseError(
                msg or f"expected {ttype.name}, got {tok.type.name} ({tok.value!r})",
                tok.line
            )
        return self.advance()

    def current_line(self):
        return self.peek().line

    # ── 型別解析輔助 ──

    def _is_type(self):
        return self.check(T.INT, T.CHAR, T.VOID)

    def _parse_type(self):
        tok = self.advance()
        return tok.value   # 'int' | 'char' | 'void'

    # ─────────────────────────── 頂層 ───────────────────────────

    def parse_program(self):
        decls = []
        while not self.check(T.EOF):
            decls.extend(self._parse_top_level())
        return Program(decls)

    def _parse_top_level(self):
        """解析一個頂層宣告（函式定義或全域變數宣告或 #define）"""
        tok = self.peek()

        # #define
        if tok.type == T.DEFINE:
            self.advance()
            name, val_str = tok.value
            # 嘗試將 val_str 解析為整數
            val = self._eval_define_value(val_str)
            self.defines[name] = val
            return [Define(name, val_str, tok.line)]

        # 型別開頭 → 可能是函式或全域變數
        if self._is_type():
            return [self._parse_func_or_global_var()]

        raise ParseError(
            f"unexpected token at top level: {tok.type.name} ({tok.value!r})",
            tok.line
        )

    def _eval_define_value(self, s):
        """把 #define 的值字串轉成整數（支援十六進位）"""
        s = s.strip()
        try:
            if s.startswith('0x') or s.startswith('0X'):
                return int(s, 16)
            return int(s)
        except ValueError:
            return 0

    def _parse_func_or_global_var(self):
        line = self.current_line()
        rtype = self._parse_type()

        # 指標回傳型別 void * / int *（不常用，但允許）
        is_ret_ptr = bool(self.match(T.STAR))

        name_tok = self.expect(T.IDENT)
        name = name_tok.value

        # 如果下一個是 '('，就是函式定義
        if self.check(T.LPAREN):
            return self._parse_func_def(rtype, name, line)

        # 否則是全域變數宣告
        return self._parse_var_decl_tail(rtype, name, is_ret_ptr, line)

    def _parse_func_def(self, rtype, name, line):
        self.expect(T.LPAREN)
        params = []
        if not self.check(T.RPAREN):
            params = self._parse_param_list()
        self.expect(T.RPAREN)
        body = self._parse_block()
        return FuncDef(rtype, name, params, body, line)

    def _parse_param_list(self):
        params = []
        while True:
            dtype = self._parse_type()
            is_ptr = bool(self.match(T.STAR))
            pname = self.expect(T.IDENT).value
            params.append((dtype, is_ptr, pname))
            if not self.match(T.COMMA):
                break
        return params

    # ─────────────────────────── 陳述句 ───────────────────────────

    def _parse_block(self):
        line = self.current_line()
        self.expect(T.LBRACE)
        stmts = []
        while not self.check(T.RBRACE) and not self.check(T.EOF):
            stmts.append(self._parse_stmt())
        self.expect(T.RBRACE)
        return Block(stmts, line)

    def _parse_stmt(self):
        tok = self.peek()

        if tok.type == T.LBRACE:
            return self._parse_block()

        if tok.type == T.IF:
            return self._parse_if()

        if tok.type == T.WHILE:
            return self._parse_while()

        if tok.type == T.FOR:
            return self._parse_for()

        if tok.type == T.DO:
            return self._parse_do_while()

        if tok.type == T.BREAK:
            self.advance()
            self.expect(T.SEMICOLON)
            return BreakStmt(tok.line)

        if tok.type == T.CONTINUE:
            self.advance()
            self.expect(T.SEMICOLON)
            return ContinueStmt(tok.line)

        if tok.type == T.RETURN:
            return self._parse_return()

        if tok.type == T.DEFINE:
            self.advance()
            name, val_str = tok.value
            val = self._eval_define_value(val_str)
            self.defines[name] = val
            return Define(name, val_str, tok.line)

        # 變數宣告：int / char 開頭
        if tok.type in (T.INT, T.CHAR):
            return self._parse_local_var_decl()

        # void 開頭（幾乎不會在陳述句出現，但防禦一下）
        if tok.type == T.VOID:
            raise ParseError("void 不可作為區域變數型別", tok.line)

        # 表達式陳述句
        expr = self._parse_expr()
        self.expect(T.SEMICOLON, f"expected ';' after expression statement")
        return ExprStmt(expr, tok.line)

    def _parse_local_var_decl(self):
        line = self.current_line()
        dtype = self._parse_type()   # 'int' or 'char'
        is_ptr = bool(self.match(T.STAR))
        name = self.expect(T.IDENT).value
        return self._parse_var_decl_tail(dtype, name, is_ptr, line)

    def _parse_var_decl_tail(self, dtype, name, is_ptr, line):
        """解析變數宣告的尾端：可能是陣列、初始值或直接分號"""
        # 陣列 int arr[N];
        if self.match(T.LBRACKET):
            size_expr = self._parse_expr()
            self.expect(T.RBRACKET)
            self.expect(T.SEMICOLON)
            return VarDecl(dtype, name, size=size_expr, line=line)

        # 有初始值
        init = None
        if self.match(T.ASSIGN):
            init = self._parse_expr()

        self.expect(T.SEMICOLON)
        return VarDecl(dtype, name, init=init, is_ptr=is_ptr, line=line)

    def _parse_if(self):
        line = self.current_line()
        self.expect(T.IF)
        self.expect(T.LPAREN)
        cond = self._parse_expr()
        self.expect(T.RPAREN)
        then_branch = self._parse_stmt()
        else_branch = None
        if self.match(T.ELSE):
            else_branch = self._parse_stmt()
        return IfStmt(cond, then_branch, else_branch, line)

    def _parse_while(self):
        line = self.current_line()
        self.expect(T.WHILE)
        self.expect(T.LPAREN)
        cond = self._parse_expr()
        self.expect(T.RPAREN)
        body = self._parse_stmt()
        return WhileStmt(cond, body, line)

    def _parse_for(self):
        line = self.current_line()
        self.expect(T.FOR)
        self.expect(T.LPAREN)

        # init：可以是變數宣告或表達式
        init = None
        if not self.check(T.SEMICOLON):
            if self.check(T.INT, T.CHAR):
                init = self._parse_local_var_decl()  # 已含分號
            else:
                init = ExprStmt(self._parse_expr(), line)
                self.expect(T.SEMICOLON)
        else:
            self.expect(T.SEMICOLON)

        # cond
        cond = None
        if not self.check(T.SEMICOLON):
            cond = self._parse_expr()
        self.expect(T.SEMICOLON)

        # update
        update = None
        if not self.check(T.RPAREN):
            update = self._parse_expr()
        self.expect(T.RPAREN)

        body = self._parse_stmt()
        return ForStmt(init, cond, update, body, line)

    def _parse_do_while(self):
        line = self.current_line()
        self.expect(T.DO)
        body = self._parse_stmt()
        self.expect(T.WHILE)
        self.expect(T.LPAREN)
        cond = self._parse_expr()
        self.expect(T.RPAREN)
        self.expect(T.SEMICOLON)
        return DoWhileStmt(body, cond, line)

    def _parse_return(self):
        line = self.current_line()
        self.expect(T.RETURN)
        value = None
        if not self.check(T.SEMICOLON):
            value = self._parse_expr()
        self.expect(T.SEMICOLON)
        return ReturnStmt(value, line)

    # ─────────────────────────── 表達式（優先序爬升） ───────────────────────────

    def _parse_expr(self):
        return self._parse_assign()

    def _parse_assign(self):
        """優先序 13（最低，右結合）：= += -= *= /= %="""
        left = self._parse_or()
        line = self.current_line()

        assign_ops = {
            T.ASSIGN:     '=',
            T.PLUS_EQ:    '+=',
            T.MINUS_EQ:   '-=',
            T.STAR_EQ:    '*=',
            T.SLASH_EQ:   '/=',
            T.PERCENT_EQ: '%=',
        }
        tok = self.peek()
        if tok.type in assign_ops:
            op = assign_ops[tok.type]
            self.advance()
            right = self._parse_assign()   # 右結合
            return Assign(left, right, op, line)
        return left

    def _parse_or(self):
        """優先序 12：||"""
        left = self._parse_and()
        while self.check(T.OR):
            op = self.advance().value
            right = self._parse_and()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_and(self):
        """優先序 11：&&"""
        left = self._parse_bitor()
        while self.check(T.AND):
            op = self.advance().value
            right = self._parse_bitor()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_bitor(self):
        """優先序 10：|"""
        left = self._parse_bitxor()
        while self.check(T.PIPE):
            op = self.advance().value
            right = self._parse_bitxor()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_bitxor(self):
        """優先序 9：^"""
        left = self._parse_bitand()
        while self.check(T.CARET):
            op = self.advance().value
            right = self._parse_bitand()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_bitand(self):
        """優先序 8：&"""
        left = self._parse_equality()
        while self.check(T.AMP):
            op = self.advance().value
            right = self._parse_equality()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_equality(self):
        """優先序 7：== !="""
        left = self._parse_relational()
        while self.check(T.EQ, T.NEQ):
            op = self.advance().value
            right = self._parse_relational()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_relational(self):
        """優先序 6：< <= > >="""
        left = self._parse_shift()
        while self.check(T.LT, T.LE, T.GT, T.GE):
            op = self.advance().value
            right = self._parse_shift()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_shift(self):
        """優先序 5：<< >>"""
        left = self._parse_additive()
        while self.check(T.LSHIFT, T.RSHIFT):
            op = self.advance().value
            right = self._parse_additive()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_additive(self):
        """優先序 4：+ -"""
        left = self._parse_multiplicative()
        while self.check(T.PLUS, T.MINUS):
            op = self.advance().value
            right = self._parse_multiplicative()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_multiplicative(self):
        """優先序 3：* / %"""
        left = self._parse_unary()
        while self.check(T.STAR, T.SLASH, T.PERCENT):
            op = self.advance().value
            right = self._parse_unary()
            left = BinOp(op, left, right, left.line)
        return left

    def _parse_unary(self):
        """優先序 2：前綴一元（右結合）"""
        tok = self.peek()
        line = tok.line

        if tok.type == T.MINUS:
            self.advance()
            return UnaryOp('-', self._parse_unary(), line)

        if tok.type == T.BANG:
            self.advance()
            return UnaryOp('!', self._parse_unary(), line)

        if tok.type == T.TILDE:
            self.advance()
            return UnaryOp('~', self._parse_unary(), line)

        if tok.type == T.STAR:
            self.advance()
            return UnaryOp('*', self._parse_unary(), line)   # 取值

        if tok.type == T.AMP:
            self.advance()
            return UnaryOp('&', self._parse_unary(), line)   # 取址

        if tok.type == T.INC:
            self.advance()
            return UnaryOp('++pre', self._parse_unary(), line)

        if tok.type == T.DEC:
            self.advance()
            return UnaryOp('--pre', self._parse_unary(), line)

        return self._parse_postfix()

    def _parse_postfix(self):
        """優先序 1：後綴（函式呼叫、陣列索引）"""
        node = self._parse_primary()
        while True:
            line = self.current_line()
            if self.match(T.LBRACKET):
                idx = self._parse_expr()
                self.expect(T.RBRACKET)
                node = ArrayIndex(node, idx, line)
            elif self.check(T.LPAREN):
                # 函式呼叫（primary 已處理識別字函式呼叫）
                # 這裡處理函式指標呼叫等邊緣情況
                break
            else:
                break
        return node

    def _parse_primary(self):
        """最高優先序：字面值、識別字、括號、函式呼叫"""
        tok = self.peek()
        line = tok.line

        # 整數字面值
        if tok.type == T.INT_LIT:
            self.advance()
            return IntLit(tok.value, line)

        # 字元字面值
        if tok.type == T.CHAR_LIT:
            self.advance()
            return CharLit(tok.value, line)

        # 字串字面值
        if tok.type == T.STR_LIT:
            self.advance()
            return StrLit(tok.value, line)

        # 識別字：可能是變數、#define 常數、或函式呼叫
        if tok.type == T.IDENT:
            self.advance()
            name = tok.value

            # 函式呼叫
            if self.check(T.LPAREN):
                self.advance()
                args = []
                if not self.check(T.RPAREN):
                    args.append(self._parse_expr())
                    while self.match(T.COMMA):
                        args.append(self._parse_expr())
                self.expect(T.RPAREN)
                return FuncCall(name, args, line)

            # #define 常數展開
            if name in self.defines:
                return IntLit(self.defines[name], line)

            return Ident(name, line)

        # 括號表達式
        if tok.type == T.LPAREN:
            self.advance()
            expr = self._parse_expr()
            self.expect(T.RPAREN)
            return expr

        raise ParseError(
            f"unexpected token in expression: {tok.type.name} ({tok.value!r})",
            tok.line
        )


# ─────────────────────────── 公開介面 ───────────────────────────

def parse(tokens, defines=None):
    """解析完整程式，回傳 Program 節點"""
    p = Parser(tokens, defines)
    return p.parse_program()

def parse_stmts(tokens, defines=None):
    """解析一系列陳述句（互動模式用）"""
    p = Parser(tokens, defines)
    stmts = []
    while not p.check(T.EOF):
        stmts.append(p._parse_stmt())
    return stmts

def parse_expr(tokens, defines=None):
    """解析單一表達式（測試用）"""
    p = Parser(tokens, defines)
    return p._parse_expr()
