"""
Small-C Built-in Functions
實作所有內建函式，並提供登記到 SymbolTable 的介面。

分類：
  I/O      : printf, puts, putchar, getchar, scanf
  字串     : strlen, strcpy, strcat, strcmp
  數學     : abs, max, min, pow, sqrt, mod, rand, srand
  工具     : memset, sizeof_int, sizeof_char, atoi, itoa, exit
"""

import math
import random
import sys

from memory import Memory, MemoryError
from symtable import SymbolTable, FuncEntry


# ──────────────────────────────────────────
# 例外：exit() 呼叫
# ──────────────────────────────────────────

class ExitCalled(Exception):
    def __init__(self, code=0):
        super().__init__(f"exit({code})")
        self.code = code


class BuiltinError(Exception):
    def __init__(self, msg, line=0):
        super().__init__(msg)
        self.line = line


# ──────────────────────────────────────────
# printf 格式化輸出（核心）
# ──────────────────────────────────────────

def _do_printf(fmt: str, args: list, mem: Memory) -> str:
    """
    解析 printf 格式字串，回傳輸出字串。
    支援：%d %c %s %x %%
    """
    result = []
    i = 0
    arg_idx = 0

    while i < len(fmt):
        c = fmt[i]
        if c != '%':
            result.append(c)
            i += 1
            continue

        i += 1
        if i >= len(fmt):
            break

        spec = fmt[i]
        i += 1

        if spec == '%':
            result.append('%')
        elif spec == 'd':
            if arg_idx >= len(args):
                raise BuiltinError("printf: not enough arguments for %d")
            val = args[arg_idx]; arg_idx += 1
            result.append(str(int(val)))
        elif spec == 'c':
            if arg_idx >= len(args):
                raise BuiltinError("printf: not enough arguments for %c")
            val = args[arg_idx]; arg_idx += 1
            result.append(chr(int(val) & 0xFF))
        elif spec == 's':
            if arg_idx >= len(args):
                raise BuiltinError("printf: not enough arguments for %s")
            addr = args[arg_idx]; arg_idx += 1
            result.append(mem.read_string(int(addr)))
        elif spec == 'x':
            if arg_idx >= len(args):
                raise BuiltinError("printf: not enough arguments for %x")
            val = args[arg_idx]; arg_idx += 1
            result.append(format(int(val) & 0xFFFFFFFF, 'x'))
        else:
            # 未知格式碼，原樣輸出
            result.append('%')
            result.append(spec)

    return ''.join(result)


# ──────────────────────────────────────────
# scanf 格式化輸入
# ──────────────────────────────────────────

_scanf_buffer = []

def _do_scanf(fmt: str, arg_addrs: list, mem: Memory,
              input_fn=None) -> int:
    """
    解析 scanf 格式字串，從 stdin 讀取並寫入對應位址。
    支援：%d %c
    支援單行多個輸入（Token 緩衝區）。
    回傳成功讀取的項目數。
    """
    global _scanf_buffer
    if input_fn is None:
        input_fn = input

    count = 0
    i = 0
    arg_idx = 0

    while i < len(fmt) and arg_idx < len(arg_addrs):
        c = fmt[i]
        if c != '%':
            i += 1
            continue
        i += 1
        if i >= len(fmt):
            break
        spec = fmt[i]; i += 1

        addr = arg_addrs[arg_idx]; arg_idx += 1

        # 若緩衝區空了，則讀取新行
        if not _scanf_buffer:
            try:
                line = input_fn()
                if line is None: break
                _scanf_buffer = line.split()
            except (EOFError, KeyboardInterrupt):
                break
        
        if not _scanf_buffer:
            break

        if spec == 'd':
            try:
                token = _scanf_buffer.pop(0)
                val = int(token)
                mem.write(int(addr), val)
                count += 1
            except (ValueError, IndexError):
                break
        elif spec == 'c':
            try:
                token = _scanf_buffer.pop(0)
                mem.write(int(addr), ord(token[0]))
                count += 1
                # 若 token 還有剩餘字元，放回緩衝區供下次使用
                if len(token) > 1:
                    _scanf_buffer.insert(0, token[1:])
            except (IndexError, EOFError):
                break

    return count


def clear_scanf_buffer():
    global _scanf_buffer
    _scanf_buffer = []


# ──────────────────────────────────────────
# 內建函式實作表
# key   = 函式名稱
# value = callable(args: list, mem: Memory, input_fn) → int|None
# ──────────────────────────────────────────

def _builtin_putchar(args, mem, input_fn):
    if len(args) < 1:
        raise BuiltinError("putchar: expected 1 argument")
    ch = int(args[0]) & 0xFF
    sys.stdout.write(chr(ch))
    sys.stdout.flush()
    return ch

def _builtin_getchar(args, mem, input_fn):
    try:
        if input_fn:
            line = input_fn()
            return ord(line[0]) if line else -1
        ch = sys.stdin.read(1)
        return ord(ch) if ch else -1
    except EOFError:
        return -1

def _builtin_printf(args, mem, input_fn):
    if len(args) < 1:
        raise BuiltinError("printf: expected at least 1 argument")
    fmt_addr = int(args[0])
    fmt_str  = mem.read_string(fmt_addr)
    out = _do_printf(fmt_str, args[1:], mem)
    sys.stdout.write(out)
    sys.stdout.flush()
    return 0

def _builtin_puts(args, mem, input_fn):
    if len(args) < 1:
        raise BuiltinError("puts: expected 1 argument")
    addr = int(args[0])
    s = mem.read_string(addr)
    print(s)   # puts 自動換行
    return 0

def _builtin_scanf(args, mem, input_fn):
    if len(args) < 1:
        raise BuiltinError("scanf: expected at least 1 argument")
    fmt_addr  = int(args[0])
    fmt_str   = mem.read_string(fmt_addr)
    arg_addrs = args[1:]
    return _do_scanf(fmt_str, arg_addrs, mem, input_fn)

# 字串函式
def _builtin_strlen(args, mem, input_fn):
    if len(args) < 1:
        raise BuiltinError("strlen: expected 1 argument")
    return mem.strlen(int(args[0]))

def _builtin_strcpy(args, mem, input_fn):
    if len(args) < 2:
        raise BuiltinError("strcpy: expected 2 arguments")
    mem.strcpy(int(args[0]), int(args[1]))
    return int(args[0])

def _builtin_strcat(args, mem, input_fn):
    if len(args) < 2:
        raise BuiltinError("strcat: expected 2 arguments")
    mem.strcat(int(args[0]), int(args[1]))
    return int(args[0])

def _builtin_strcmp(args, mem, input_fn):
    if len(args) < 2:
        raise BuiltinError("strcmp: expected 2 arguments")
    return mem.strcmp(int(args[0]), int(args[1]))

# 數學函式
def _builtin_abs(args, mem, input_fn):
    if len(args) < 1:
        raise BuiltinError("abs: expected 1 argument")
    return abs(int(args[0]))

def _builtin_max(args, mem, input_fn):
    if len(args) < 2:
        raise BuiltinError("max: expected 2 arguments")
    return max(int(args[0]), int(args[1]))

def _builtin_min(args, mem, input_fn):
    if len(args) < 2:
        raise BuiltinError("min: expected 2 arguments")
    return min(int(args[0]), int(args[1]))

def _builtin_pow(args, mem, input_fn):
    if len(args) < 2:
        raise BuiltinError("pow: expected 2 arguments")
    base = int(args[0])
    exp  = int(args[1])
    if exp < 0:
        return 0
    return int(base ** exp)

def _builtin_sqrt(args, mem, input_fn):
    if len(args) < 1:
        raise BuiltinError("sqrt: expected 1 argument")
    x = int(args[0])
    if x < 0:
        raise BuiltinError("Runtime error: sqrt() argument must be non-negative")
    return int(math.sqrt(x))

def _builtin_mod(args, mem, input_fn):
    if len(args) < 2:
        raise BuiltinError("mod: expected 2 arguments")
    a, b = int(args[0]), int(args[1])
    if b == 0:
        raise BuiltinError("Runtime error: division by zero in mod()")
    return a % b

def _builtin_rand(args, mem, input_fn):
    return random.randint(0, 32767)

def _builtin_srand(args, mem, input_fn):
    if len(args) < 1:
        raise BuiltinError("srand: expected 1 argument")
    random.seed(int(args[0]))
    return 0

# 工具函式
def _builtin_memset(args, mem, input_fn):
    if len(args) < 3:
        raise BuiltinError("memset: expected 3 arguments")
    mem.memset(int(args[0]), int(args[1]), int(args[2]))
    return int(args[0])

def _builtin_sizeof_int(args, mem, input_fn):
    return 4

def _builtin_sizeof_char(args, mem, input_fn):
    return 1

def _builtin_atoi(args, mem, input_fn):
    if len(args) < 1:
        raise BuiltinError("atoi: expected 1 argument")
    s = mem.read_string(int(args[0]))
    s = s.strip()
    try:
        # 處理正負號
        return int(s)
    except ValueError:
        return 0

def _builtin_itoa(args, mem, input_fn):
    if len(args) < 2:
        raise BuiltinError("itoa: expected 2 arguments")
    val  = int(args[0])
    addr = int(args[1])
    s    = str(val)
    mem.write_string(addr, s)
    return 0

def _builtin_exit(args, mem, input_fn):
    code = int(args[0]) if args else 0
    raise ExitCalled(code)


# ──────────────────────────────────────────
# 函式簽名表（用於 FUNCS 指令顯示與型別檢查）
# ──────────────────────────────────────────

BUILTIN_SIGNATURES = {
    # name: (rtype, params)
    # params: list of (dtype, is_ptr, name)
    'putchar':    ('int',  [('int',  False, 'ch')]),
    'getchar':    ('int',  []),
    'printf':     ('void', [('char', True,  'fmt')]),
    'puts':       ('void', [('char', True,  's')]),
    'scanf':      ('int',  [('char', True,  'fmt')]),
    'strlen':     ('int',  [('char', True,  's')]),
    'strcpy':     ('void', [('char', True,  'dest'), ('char', True, 'src')]),
    'strcat':     ('void', [('char', True,  'dest'), ('char', True, 'src')]),
    'strcmp':     ('int',  [('char', True,  's1'),   ('char', True, 's2')]),
    'abs':        ('int',  [('int',  False, 'x')]),
    'max':        ('int',  [('int',  False, 'a'),    ('int',  False, 'b')]),
    'min':        ('int',  [('int',  False, 'a'),    ('int',  False, 'b')]),
    'pow':        ('int',  [('int',  False, 'base'), ('int',  False, 'exp')]),
    'sqrt':       ('int',  [('int',  False, 'x')]),
    'mod':        ('int',  [('int',  False, 'a'),    ('int',  False, 'b')]),
    'rand':       ('int',  []),
    'srand':      ('void', [('int',  False, 'seed')]),
    'memset':     ('void', [('char', True,  'ptr'),
                            ('int',  False, 'value'),
                            ('int',  False, 'size')]),
    'sizeof_int':  ('int', []),
    'sizeof_char': ('int', []),
    'atoi':       ('int',  [('char', True,  's')]),
    'itoa':       ('void', [('int',  False, 'value'), ('char', True, 'str')]),
    'exit':       ('void', [('int',  False, 'code')]),
}

# 實作對應表
BUILTIN_IMPLS = {
    'putchar':    _builtin_putchar,
    'getchar':    _builtin_getchar,
    'printf':     _builtin_printf,
    'puts':       _builtin_puts,
    'scanf':      _builtin_scanf,
    'strlen':     _builtin_strlen,
    'strcpy':     _builtin_strcpy,
    'strcat':     _builtin_strcat,
    'strcmp':     _builtin_strcmp,
    'abs':        _builtin_abs,
    'max':        _builtin_max,
    'min':        _builtin_min,
    'pow':        _builtin_pow,
    'sqrt':       _builtin_sqrt,
    'mod':        _builtin_mod,
    'rand':       _builtin_rand,
    'srand':      _builtin_srand,
    'memset':     _builtin_memset,
    'sizeof_int':  _builtin_sizeof_int,
    'sizeof_char': _builtin_sizeof_char,
    'atoi':       _builtin_atoi,
    'itoa':       _builtin_itoa,
    'exit':       _builtin_exit,
}


# ──────────────────────────────────────────
# 公開介面
# ──────────────────────────────────────────

def register_builtins(sym: SymbolTable):
    """將所有內建函式登記到符號表。"""
    for name, (rtype, params) in BUILTIN_SIGNATURES.items():
        entry = FuncEntry(
            rtype=rtype,
            params=params,
            node=None,
            is_builtin=True,
        )
        sym.declare_func(name, entry)


def call_builtin(name: str, args: list,
                 mem: Memory, input_fn=None):
    """
    呼叫一個內建函式。
    name     : 函式名稱
    args     : 已求值的引數列表（Python int）
    mem      : Memory 物件
    input_fn : 可替換的輸入函式（測試用），預設為 None（用 input()）
    回傳值   : int 或 None（void 函式）
    """
    impl = BUILTIN_IMPLS.get(name)
    if impl is None:
        raise BuiltinError(f"unknown built-in function: '{name}'")
    result = impl(args, mem, input_fn)
    return 0 if result is None else result


def is_builtin(name: str) -> bool:
    return name in BUILTIN_IMPLS
