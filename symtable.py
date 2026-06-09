"""
Small-C Symbol Table
管理變數與函式的宣告、型別、作用域。

設計：
  - 用「scope stack」實作巢狀作用域
  - 全域 scope 在最底層（index 0）
  - 每次進入函式就 push 一個新 scope
  - 離開函式就 pop
  - 變數查找從最內層 scope 往外找（遮蔽規則）

變數記錄（VarEntry）：
  dtype   : 'int' | 'char'
  is_ptr  : bool
  is_arr  : bool
  size    : int（陣列元素數，非陣列為 1）
  addr    : int（記憶體位址）
  cell_size: int（每個元素佔幾個 cell：int→4, char→1）

函式記錄（FuncEntry）：
  rtype  : 'int' | 'char' | 'void'
  params : list of (dtype, is_ptr, name)
  node   : FuncDef AST 節點（None 表示內建）
  is_builtin: bool
"""

from dataclasses import dataclass, field
from typing import Optional, Any


class SymbolError(Exception):
    def __init__(self, msg, line=0):
        super().__init__(msg)
        self.line = line


# ──────────────────────────────────────────
# 記錄型別
# ──────────────────────────────────────────

@dataclass
class VarEntry:
    dtype    : str          # 'int' | 'char'
    is_ptr   : bool = False
    is_arr   : bool = False
    size     : int  = 1     # 陣列元素數（非陣列為 1）
    addr     : int  = 0     # 記憶體位址
    cell_size: int  = 4     # int=4, char=1

    def elem_size(self) -> int:
        """單一元素佔幾個 cell"""
        return 1 if self.dtype == 'char' else 4

    def total_cells(self) -> int:
        """整個變數佔幾個 cell"""
        return self.size * self.elem_size()


@dataclass
class FuncEntry:
    rtype     : str                    # 'int' | 'char' | 'void'
    params    : list = field(default_factory=list)
    node      : Any  = None            # FuncDef AST 節點
    is_builtin: bool = False


# ──────────────────────────────────────────
# SymbolTable
# ──────────────────────────────────────────

class SymbolTable:
    def __init__(self):
        # scope stack：每個元素是 dict[name → VarEntry]
        self._scopes: list[dict] = [{}]   # index 0 = 全域

        # 函式表（全域唯一）
        self._funcs: dict[str, FuncEntry] = {}

        # #define 常數表
        self._defines: dict[str, int] = {}

    # ─────────────────── Scope 管理 ───────────────────

    def push_scope(self):
        """進入新作用域（進入函式或區塊）"""
        self._scopes.append({})

    def pop_scope(self):
        """離開目前作用域"""
        if len(self._scopes) <= 1:
            raise SymbolError("cannot pop global scope")
        self._scopes.pop()

    def current_depth(self) -> int:
        """目前作用域深度（0 = 全域）"""
        return len(self._scopes) - 1

    def is_global(self) -> bool:
        return len(self._scopes) == 1

    # ─────────────────── 變數操作 ───────────────────

    def declare_var(self, name: str, entry: VarEntry, line: int = 0):
        """在目前作用域宣告一個變數。若同層已宣告則報錯。"""
        current = self._scopes[-1]
        if name in current:
            raise SymbolError(
                f"variable '{name}' already declared in this scope", line)
        current[name] = entry

    def lookup_var(self, name: str, line: int = 0) -> VarEntry:
        """從最內層往外找變數，找不到則報錯。"""
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise SymbolError(f"undefined variable '{name}'", line)

    def lookup_var_safe(self, name: str) -> Optional[VarEntry]:
        """找不到時回傳 None 而非拋出例外。"""
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def update_var(self, name: str, addr: int = None,
                   value_hint=None, line: int = 0) -> VarEntry:
        """更新已宣告變數的位址（分配記憶體後回填）。"""
        for scope in reversed(self._scopes):
            if name in scope:
                if addr is not None:
                    scope[name].addr = addr
                return scope[name]
        raise SymbolError(f"undefined variable '{name}'", line)

    def all_global_vars(self) -> dict:
        """回傳全域作用域的所有變數（VARS 指令用）。"""
        return dict(self._scopes[0])

    def all_current_vars(self) -> dict:
        """回傳所有可見變數（含所有層，內層遮蔽外層）。"""
        merged = {}
        for scope in self._scopes:
            merged.update(scope)
        return merged

    # ─────────────────── 函式操作 ───────────────────

    def declare_func(self, name: str, entry: FuncEntry, line: int = 0):
        """宣告一個函式（全域）。"""
        # 允許重複宣告內建函式（不報錯）
        if name in self._funcs and not self._funcs[name].is_builtin:
            raise SymbolError(f"function '{name}' already defined", line)
        self._funcs[name] = entry

    def lookup_func(self, name: str, line: int = 0) -> FuncEntry:
        """查找函式，找不到則報錯。"""
        if name not in self._funcs:
            raise SymbolError(f"undefined function '{name}'", line)
        return self._funcs[name]

    def lookup_func_safe(self, name: str) -> Optional[FuncEntry]:
        return self._funcs.get(name)

    def all_funcs(self) -> dict:
        """回傳所有函式（FUNCS 指令用）。"""
        return dict(self._funcs)

    def user_funcs(self) -> dict:
        """只回傳使用者定義的函式。"""
        return {k: v for k, v in self._funcs.items() if not v.is_builtin}

    def builtin_funcs(self) -> dict:
        """只回傳內建函式。"""
        return {k: v for k, v in self._funcs.items() if v.is_builtin}

    # ─────────────────── #define 常數 ───────────────────

    def define(self, name: str, value: int):
        self._defines[name] = value

    def lookup_define(self, name: str) -> Optional[int]:
        return self._defines.get(name)

    def all_defines(self) -> dict:
        return dict(self._defines)

    # ─────────────────── 重置 ───────────────────

    def reset(self):
        """完全重置（NEW 指令用）。保留內建函式。"""
        builtins = {k: v for k, v in self._funcs.items() if v.is_builtin}
        self._scopes  = [{}]
        self._funcs   = builtins
        self._defines = {}

    def reset_globals(self):
        """只清除全域變數（RUN 前清除殘留狀態）。"""
        self._scopes = [{}]
        self._defines = {}
        # 保留函式表（使用者定義 + 內建）

    # ─────────────────── 除錯輸出 ───────────────────

    def dump_vars(self) -> str:
        """格式化輸出所有可見變數（VARS 指令）。"""
        lines = []
        seen = set()
        for scope in reversed(self._scopes):
            for name, entry in scope.items():
                if name in seen:
                    continue
                seen.add(name)
                lines.append(_format_var(name, entry))
        return '\n'.join(lines) if lines else '(no variables)'

    def dump_funcs(self, memory=None) -> str:
        """格式化輸出所有函式（FUNCS 指令）。"""
        lines = []
        # 使用者定義函式優先
        for name, entry in self._funcs.items():
            if not entry.is_builtin:
                params_str = _format_params(entry.params)
                line_no = entry.node.line if entry.node else '?'
                lines.append(
                    f"  {entry.rtype:<6} {name}({params_str})"
                    f"{'':>4} line {line_no}"
                )
        # 內建函式
        lines.append("  --- built-in functions ---")
        for name, entry in self._funcs.items():
            if entry.is_builtin:
                params_str = _format_params(entry.params)
                lines.append(
                    f"  {entry.rtype:<6} {name}({params_str})"
                    f"{'':>4} [built-in]"
                )
        return '\n'.join(lines) if lines else '(no functions)'


# ──────────────────────────────────────────
# 格式化輔助
# ──────────────────────────────────────────

def _format_var(name: str, entry: VarEntry) -> str:
    ptr_mark = '*' if entry.is_ptr else ''
    if entry.is_arr:
        # 陣列：顯示前 10 個元素
        return f"  {entry.dtype} {ptr_mark}{name}[{entry.size}]  addr={entry.addr}"
    else:
        return f"  {entry.dtype} {ptr_mark}{name}  addr={entry.addr}"


def _format_params(params: list) -> str:
    if not params:
        return ''
    parts = []
    for item in params:
        if isinstance(item, tuple):
            if len(item) == 3:
                dtype, is_ptr, pname = item
                parts.append(f"{dtype} {'*' if is_ptr else ''}{pname}")
            else:
                parts.append(str(item))
        else:
            parts.append(str(item))
    return ', '.join(parts)
