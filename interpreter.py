"""
Small-C Interpreter
走訪 AST 節點並執行，整合 Memory、SymbolTable、Builtins。
"""

import sys
from memory import Memory, MemoryError
from symtable import SymbolTable, VarEntry, FuncEntry, SymbolError
from smallc_builtins import (register_builtins, call_builtin,
                              is_builtin, ExitCalled, BuiltinError)
from parser import (
    Program, FuncDef, VarDecl, Define, Block,
    IfStmt, WhileStmt, ForStmt, DoWhileStmt,
    BreakStmt, ContinueStmt, ReturnStmt, ExprStmt,
    BinOp, UnaryOp, Assign, Ident, ArrayIndex,
    FuncCall, IntLit, CharLit, StrLit,
)
from lexer import tokenize, LexerError, TokenType
from parser import parse, parse_stmts, ParseError, Parser


# ── 控制流例外 ──
class BreakSignal(Exception):    pass
class ContinueSignal(Exception): pass
class ReturnSignal(Exception):
    def __init__(self, value=0): self.value = value

class RuntimeError_(Exception):
    def __init__(self, msg, line=0):
        super().__init__(msg)
        self.line = line


class Interpreter:
    def __init__(self, trace=False, input_fn=None):
        self.mem      = Memory()
        self.sym      = SymbolTable()
        self.trace    = trace
        self.input_fn = input_fn
        register_builtins(self.sym)

    def reset(self):
        self.mem = Memory()
        self.sym.reset()
        register_builtins(self.sym)

    # ── 完整程式執行 ──

    def run_program(self, source: str):
        self.reset()
        try:
            tokens = tokenize(source)
        except LexerError as e:
            raise RuntimeError_(f"Lexer error: {e}", getattr(e, 'line', 0))
        try:
            ast = parse(tokens, self.sym.all_defines())
        except ParseError as e:
            raise RuntimeError_(f"Syntax error at line {getattr(e,'line',0)}: {e}", getattr(e,'line',0))

        for decl in ast.decls:
            self._register_top(decl)
        for decl in ast.decls:
            if isinstance(decl, VarDecl):
                self._init_global_var(decl)

        fe = self.sym.lookup_func_safe('main')
        if fe is None or fe.is_builtin:
            raise RuntimeError_("No main() function defined.")

        try:
            ret = self._call_user_func(fe, [])
            code = ret if ret is not None else 0
        except ReturnSignal as r:
            code = r.value
        except ExitCalled as e:
            print(f"Program exited with return value {e.code}.")
            return

        if fe.rtype == 'int':
            print(f"Program exited with return value {code}.")

    def _register_top(self, decl):
        if isinstance(decl, FuncDef):
            entry = FuncEntry(rtype=decl.rtype, params=decl.params,
                              node=decl, is_builtin=False)
            self.sym.declare_func(decl.name, entry, decl.line)
        elif isinstance(decl, VarDecl):
            entry = VarEntry(dtype=decl.dtype, is_ptr=decl.is_ptr,
                             is_arr=(decl.size is not None), size=1, addr=0)
            self.sym.declare_var(decl.name, entry, decl.line)
        elif isinstance(decl, Define):
            self.sym.define(decl.name, self._eval_define_str(decl.value_str))

    def _eval_define_str(self, s: str) -> int:
        s = s.strip()
        try:
            return int(s, 16) if s.startswith(('0x','0X')) else int(s)
        except ValueError:
            return 0

    def _init_global_var(self, decl: VarDecl):
        entry = self.sym.lookup_var(decl.name, decl.line)
        if decl.size is not None:
            size_val  = self._eval_expr(decl.size)
            elem_size = 1 if decl.dtype == 'char' else 4
            addr = self.mem.alloc(size_val * elem_size)
            entry.is_arr = True; entry.size = size_val
            entry.addr   = addr; entry.cell_size = elem_size
        else:
            cell = 1 if decl.dtype == 'char' else 4
            addr = self.mem.alloc(cell)
            entry.addr = addr
            if decl.init is not None:
                val = self._eval_expr(decl.init)
                self.mem.write(addr, int(val))

    # ── 互動模式 ──

    def exec_interactive(self, source: str):
        source = source.strip()
        if not source:
            return
        try:
            tokens = tokenize(source)
        except LexerError as e:
            raise RuntimeError_(f"Lexer error: {e}", getattr(e,'line',0))

        try:
            p = Parser(tokens, self.sym.all_defines())
            top_types = (TokenType.INT, TokenType.CHAR,
                         TokenType.VOID, TokenType.DEFINE)
            if p.check(*top_types):
                decls = []
                while not p.check(TokenType.EOF):
                    decls.extend(p._parse_top_level())
                for d in decls:
                    if isinstance(d, FuncDef):
                        self._register_top(d)
                    elif isinstance(d, VarDecl):
                        self._register_top(d)
                        self._init_global_var(d)
                    elif isinstance(d, Define):
                        self._register_top(d)
                return
            stmts = []
            while not p.check(TokenType.EOF):
                stmts.append(p._parse_stmt())
        except ParseError as e:
            raise RuntimeError_(f"Syntax error: {e}", getattr(e,'line',0))

        for stmt in stmts:
            self._exec_stmt(stmt)

    # ── 語法檢查 ──

    def check_syntax(self, source: str) -> list:
        errors = []
        try:
            tokens = tokenize(source)
        except LexerError as e:
            errors.append(f"Lexer error at line {getattr(e,'line',0)}: {e}")
            return errors
        try:
            parse(tokens, self.sym.all_defines())
        except ParseError as e:
            errors.append(f"Error at line {getattr(e,'line',0)}: {e}")
        return errors

    # ── 陳述句執行 ──

    def _exec_stmt(self, stmt):
        if self.trace and hasattr(stmt, 'line') and stmt.line:
            print(f"[line {stmt.line}] {self._stmt_src(stmt)}")

        if isinstance(stmt, ExprStmt):
            self._eval_expr(stmt.expr)

        elif isinstance(stmt, VarDecl):
            self._exec_var_decl(stmt)

        elif isinstance(stmt, Block):
            self.sym.push_scope()
            mark = self.mem.mark()
            try:
                for s in stmt.stmts:
                    self._exec_stmt(s)
            finally:
                self.sym.pop_scope()
                self.mem.free_after(mark)

        elif isinstance(stmt, IfStmt):
            if self._eval_expr(stmt.cond):
                self._exec_stmt(stmt.then_branch)
            elif stmt.else_branch:
                self._exec_stmt(stmt.else_branch)

        elif isinstance(stmt, WhileStmt):
            while self._eval_expr(stmt.cond):
                try:
                    self._exec_stmt(stmt.body)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue

        elif isinstance(stmt, ForStmt):
            in_scope = False
            mark = None
            if stmt.init:
                if isinstance(stmt.init, VarDecl):
                    self.sym.push_scope()
                    mark = self.mem.mark()
                    self._exec_var_decl(stmt.init)
                    in_scope = True
                else:
                    self._eval_expr(stmt.init.expr)
            try:
                while True:
                    if stmt.cond and not self._eval_expr(stmt.cond):
                        break
                    try:
                        self._exec_stmt(stmt.body)
                    except BreakSignal:
                        break
                    except ContinueSignal:
                        pass
                    if stmt.update:
                        self._eval_expr(stmt.update)
            finally:
                if in_scope:
                    self.sym.pop_scope()
                    self.mem.free_after(mark)

        elif isinstance(stmt, DoWhileStmt):
            while True:
                try:
                    self._exec_stmt(stmt.body)
                except BreakSignal:
                    break
                except ContinueSignal:
                    pass
                if not self._eval_expr(stmt.cond):
                    break

        elif isinstance(stmt, BreakStmt):
            raise BreakSignal()

        elif isinstance(stmt, ContinueStmt):
            raise ContinueSignal()

        elif isinstance(stmt, ReturnStmt):
            val = self._eval_expr(stmt.value) if stmt.value else 0
            raise ReturnSignal(val)

        elif isinstance(stmt, Define):
            self.sym.define(stmt.name, self._eval_define_str(stmt.value_str))

        else:
            raise RuntimeError_(f"Unknown stmt: {type(stmt).__name__}")

    def _exec_var_decl(self, decl: VarDecl):
        if decl.size is not None:
            size_val  = self._eval_expr(decl.size)
            elem_size = 1 if decl.dtype == 'char' else 4
            addr = self.mem.alloc(size_val * elem_size)
            entry = VarEntry(dtype=decl.dtype, is_arr=True, size=size_val,
                             addr=addr, cell_size=elem_size)
            self.sym.declare_var(decl.name, entry, decl.line)
            if decl.init is not None:
                val = self._eval_expr(decl.init)
                if isinstance(val, str):
                    self.mem.write_string(addr, val)
        else:
            cell = 1 if decl.dtype == 'char' else 4
            addr = self.mem.alloc(cell)
            entry = VarEntry(dtype=decl.dtype, is_ptr=decl.is_ptr,
                             addr=addr, cell_size=cell)
            self.sym.declare_var(decl.name, entry, decl.line)
            if decl.init is not None:
                val = self._eval_expr(decl.init)
                if isinstance(val, str):
                    self.mem.write_string(addr, val)
                else:
                    self.mem.write(addr, int(val))

    # ── 表達式求值 ──

    def _eval_expr(self, node):
        if isinstance(node, IntLit):  return node.value
        if isinstance(node, CharLit): return node.value
        if isinstance(node, StrLit):
            return self.mem.alloc_string_literal(node.value)

        if isinstance(node, Ident):
            entry = self.sym.lookup_var(node.name, node.line)
            if entry.is_arr:
                return entry.addr
            return self.mem.read(entry.addr)

        if isinstance(node, ArrayIndex):
            addr = self._eval_lvalue_addr(node)
            return self.mem.read(addr)

        if isinstance(node, UnaryOp):  return self._eval_unary(node)
        if isinstance(node, BinOp):    return self._eval_binop(node)
        if isinstance(node, Assign):   return self._eval_assign(node)
        if isinstance(node, FuncCall): return self._eval_func_call(node)

        raise RuntimeError_(f"Unknown expr: {type(node).__name__}")

    def _eval_unary(self, node):
        op = node.op
        if op == '-':     return -self._eval_expr(node.operand)
        if op == '!':     return 0 if self._eval_expr(node.operand) else 1
        if op == '~':     return ~self._eval_expr(node.operand)
        if op == '&':     return self._eval_lvalue_addr(node.operand)
        if op == '*':
            ptr = self._eval_expr(node.operand)
            return self.mem.read(int(ptr))
        if op == '++pre':
            addr = self._eval_lvalue_addr(node.operand)
            val  = self.mem.read(addr) + 1
            self.mem.write(addr, val); return val
        if op == '--pre':
            addr = self._eval_lvalue_addr(node.operand)
            val  = self.mem.read(addr) - 1
            self.mem.write(addr, val); return val
        raise RuntimeError_(f"Unknown unary: {op}")

    def _eval_binop(self, node):
        op = node.op
        if op == '&&':
            return 1 if (self._eval_expr(node.left) and self._eval_expr(node.right)) else 0
        if op == '||':
            return 1 if (self._eval_expr(node.left) or self._eval_expr(node.right)) else 0
        L = self._eval_expr(node.left)
        R = self._eval_expr(node.right)
        if op == '+':  return L + R
        if op == '-':  return L - R
        if op == '*':  return L * R
        if op == '/':
            if R == 0: raise RuntimeError_("Runtime error: division by zero", node.line)
            return int(L / R)
        if op == '%':
            if R == 0: raise RuntimeError_("Runtime error: division by zero", node.line)
            return int(L) % int(R)
        if op == '<':  return 1 if L <  R else 0
        if op == '<=': return 1 if L <= R else 0
        if op == '>':  return 1 if L >  R else 0
        if op == '>=': return 1 if L >= R else 0
        if op == '==': return 1 if L == R else 0
        if op == '!=': return 1 if L != R else 0
        if op == '&':  return int(L) & int(R)
        if op == '|':  return int(L) | int(R)
        if op == '^':  return int(L) ^ int(R)
        if op == '<<': return int(L) << int(R)
        if op == '>>': return int(L) >> int(R)
        raise RuntimeError_(f"Unknown binop: {op}")

    def _eval_assign(self, node):
        rval = self._eval_expr(node.value)
        addr = self._eval_lvalue_addr(node.target)
        if node.op != '=':
            old = self.mem.read(addr)
            op  = node.op[0]
            if op == '+': rval = old + rval
            elif op == '-': rval = old - rval
            elif op == '*': rval = old * rval
            elif op == '/':
                if rval == 0: raise RuntimeError_("Runtime error: division by zero")
                rval = int(old / rval)
            elif op == '%':
                if rval == 0: raise RuntimeError_("Runtime error: division by zero")
                rval = old % rval
        self.mem.write(addr, int(rval))
        return rval

    def _eval_func_call(self, node):
        args = [self._eval_expr(a) for a in node.args]
        name = node.name
        if is_builtin(name):
            try:
                return call_builtin(name, args, self.mem, self.input_fn)
            except BuiltinError as e:
                raise RuntimeError_(str(e), node.line)
        fe = self.sym.lookup_func(name, node.line)
        try:
            ret = self._call_user_func(fe, args)
            return ret if ret is not None else 0
        except ReturnSignal as r:
            return r.value

    def _call_user_func(self, fe, args):
        node = fe.node
        self.sym.push_scope()
        mark = self.mem.mark()
        try:
            for i, (dtype, is_ptr, pname) in enumerate(fe.params):
                cell = 1 if (dtype == 'char' and not is_ptr) else 4
                addr = self.mem.alloc(cell)
                val  = args[i] if i < len(args) else 0
                self.mem.write(addr, int(val))
                entry = VarEntry(dtype=dtype, is_ptr=is_ptr,
                                 addr=addr, cell_size=cell)
                self.sym.declare_var(pname, entry)
            for stmt in node.body.stmts:
                self._exec_stmt(stmt)
        except ReturnSignal as r:
            return r.value
        finally:
            self.sym.pop_scope()
            self.mem.free_after(mark)
        return 0

    # ── LValue 位址 ──

    def _eval_lvalue_addr(self, node) -> int:
        if isinstance(node, Ident):
            return self.sym.lookup_var(node.name, node.line).addr
        if isinstance(node, ArrayIndex):
            # _eval_expr handles both: array name → base addr, pointer → pointed addr
            base  = self._eval_expr(node.array)
            idx   = self._eval_expr(node.index)
            entry = self._get_arr_entry(node.array)
            elem  = 4  # default int size
            if entry:
                if entry.is_arr:
                    elem = entry.elem_size()
                    if idx < 0 or idx >= entry.size:
                        raise RuntimeError_(
                            f"Runtime error: array index out of bounds "
                            f"(index {idx}, size {entry.size})", node.line)
                elif entry.is_ptr:
                    elem = 4  # pointer to int → 4 bytes per element
                else:
                    elem = entry.elem_size()
            return base + idx * elem
        if isinstance(node, UnaryOp) and node.op == '*':
            return self._eval_expr(node.operand)
        raise RuntimeError_(f"Not an lvalue: {type(node).__name__}",
                            getattr(node,'line',0))

    def _get_arr_entry(self, node):
        if isinstance(node, Ident):
            return self.sym.lookup_var_safe(node.name)
        return None

    # ── VARS / FUNCS 輸出 ──

    def dump_vars(self) -> str:
        lines = []
        seen  = set()
        for scope in reversed(self.sym._scopes):
            for name, entry in scope.items():
                if name in seen: continue
                seen.add(name)
                lines.append(self._format_var(name, entry))
        return '\n'.join(lines) if lines else '(no variables)'

    def _format_var(self, name, entry):
        ptr = '*' if entry.is_ptr else ''
        if entry.is_arr:
            vals = []
            for i in range(min(entry.size, 10)):
                try:    vals.append(str(self.mem.read(entry.addr + i * entry.elem_size())))
                except: vals.append('?')
            ell = ', ...' if entry.size > 10 else ''
            return f"  {entry.dtype} {ptr}{name}[{entry.size}] = {{{', '.join(vals)}{ell}}}"
        else:
            try:
                val = self.mem.read(entry.addr)
                if entry.dtype == 'char' and not entry.is_ptr:
                    c = chr(val & 0xFF) if 32 <= (val & 0xFF) <= 126 else '?'
                    return f"  {entry.dtype} {ptr}{name} = {val} ('{c}')"
                return f"  {entry.dtype} {ptr}{name} = {val}"
            except:
                return f"  {entry.dtype} {ptr}{name} = (uninitialized)"

    def dump_funcs(self) -> str:
        lines = []
        for name, fe in self.sym.all_funcs().items():
            if not fe.is_builtin:
                p = self._fmt_params(fe.params)
                ln = fe.node.line if fe.node else '?'
                lines.append(f"  {fe.rtype:<6} {name}({p})  line {ln}")
        lines.append("  --- built-in functions ---")
        for name, fe in self.sym.all_funcs().items():
            if fe.is_builtin:
                p = self._fmt_params(fe.params)
                lines.append(f"  {fe.rtype:<6} {name}({p})  [built-in]")
        return '\n'.join(lines)

    def _fmt_params(self, params) -> str:
        parts = []
        for item in params:
            if isinstance(item, tuple) and len(item) == 3:
                dtype, is_ptr, pname = item
                parts.append(f"{dtype} {'*' if is_ptr else ''}{pname}")
        return ', '.join(parts)

    # ── TRACE 輔助 ──

    def _stmt_src(self, stmt) -> str:
        if isinstance(stmt, ExprStmt):    return self._expr_src(stmt.expr) + ';'
        if isinstance(stmt, VarDecl):     return f"{stmt.dtype} {stmt.name};"
        if isinstance(stmt, WhileStmt):   return f"while ({self._expr_src(stmt.cond)}) {{"
        if isinstance(stmt, IfStmt):      return f"if ({self._expr_src(stmt.cond)})"
        if isinstance(stmt, ReturnStmt):
            return f"return {self._expr_src(stmt.value) if stmt.value else ''};"
        if isinstance(stmt, BreakStmt):    return "break;"
        if isinstance(stmt, ContinueStmt): return "continue;"
        return type(stmt).__name__

    def _expr_src(self, node) -> str:
        if node is None:              return ''
        if isinstance(node, IntLit):  return str(node.value)
        if isinstance(node, CharLit): return repr(chr(node.value & 0xFF))
        if isinstance(node, StrLit):  return repr(node.value)
        if isinstance(node, Ident):   return node.name
        if isinstance(node, BinOp):
            return f"{self._expr_src(node.left)} {node.op} {self._expr_src(node.right)}"
        if isinstance(node, UnaryOp):
            return f"{node.op}{self._expr_src(node.operand)}"
        if isinstance(node, Assign):
            return f"{self._expr_src(node.target)} {node.op} {self._expr_src(node.value)}"
        if isinstance(node, FuncCall):
            args = ', '.join(self._expr_src(a) for a in node.args)
            return f"{node.name}({args})"
        if isinstance(node, ArrayIndex):
            return f"{self._expr_src(node.array)}[{self._expr_src(node.index)}]"
        return '...'
