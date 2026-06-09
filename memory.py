"""
Small-C Memory Model
用 Python dict 模擬一塊線性記憶體空間。

設計原則：
  - 每個 int  佔 4 個位元組（cell）
  - 每個 char 佔 1 個位元組（cell）
  - 陣列/字串在記憶體中連續存放
  - 指標值 = 模擬位址（整數偏移量）
  - 位址從 1000 開始分配（0 保留為 NULL）

對外介面：
  mem = Memory()
  addr = mem.alloc(size)          # 分配 size 個 cell，回傳起始位址
  mem.write(addr, value)          # 寫入單一 cell
  mem.read(addr)                  # 讀取單一 cell
  mem.write_array(addr, values)   # 批次寫入
  mem.read_string(addr)           # 從位址讀取 null-terminated 字串
  mem.write_string(addr, s)       # 寫入字串（含結尾 \\0）
  mem.free_after(mark)            # 釋放 mark 之後的所有位址（函式返回用）
  mem.mark()                      # 回傳目前分配高水位（用於 stack frame）
"""

NULL = 0
HEAP_START = 1000


class MemoryError(Exception):
    def __init__(self, msg, addr=None):
        super().__init__(msg)
        self.addr = addr


class Memory:
    def __init__(self):
        self._cells: dict[int, int] = {}   # addr → value
        self._next_addr: int = HEAP_START
        self._alloc_log: list[tuple[int,int]] = []  # (addr, size) 紀錄

    # ──────────────────────────────────────────
    # 分配
    # ──────────────────────────────────────────

    def alloc(self, size: int) -> int:
        """分配 size 個 cell，初始化為 0，回傳起始位址。"""
        if size <= 0:
            raise MemoryError(f"alloc: invalid size {size}")
        addr = self._next_addr
        for i in range(size):
            self._cells[addr + i] = 0
        self._next_addr += size
        self._alloc_log.append((addr, size))
        return addr

    def mark(self) -> int:
        """回傳目前分配高水位，用於 stack frame 標記。"""
        return self._next_addr

    def free_after(self, mark: int):
        """釋放 mark 之後分配的所有 cell（函式返回時回收區域變數）。"""
        keys_to_del = [k for k in self._cells if k >= mark]
        for k in keys_to_del:
            del self._cells[k]
        self._next_addr = mark
        # 清除 alloc_log 中 mark 之後的記錄
        self._alloc_log = [(a, s) for a, s in self._alloc_log if a < mark]

    # ──────────────────────────────────────────
    # 讀寫
    # ──────────────────────────────────────────

    def write(self, addr: int, value: int):
        """寫入單一 cell。"""
        if addr == NULL:
            raise MemoryError("null pointer dereference", addr)
        if addr not in self._cells:
            raise MemoryError(f"write to unallocated address {addr}", addr)
        # 截斷到 32-bit 有號整數範圍
        value = self._to_int32(value)
        self._cells[addr] = value

    def read(self, addr: int) -> int:
        """讀取單一 cell。"""
        if addr == NULL:
            raise MemoryError("null pointer dereference", addr)
        if addr not in self._cells:
            raise MemoryError(f"read from unallocated address {addr}", addr)
        return self._cells[addr]

    def write_array(self, base_addr: int, values: list):
        """批次寫入連續 cell。"""
        for i, v in enumerate(values):
            self.write(base_addr + i, v)

    def read_array(self, base_addr: int, size: int) -> list:
        """批次讀取連續 cell。"""
        return [self.read(base_addr + i) for i in range(size)]

    # ──────────────────────────────────────────
    # 字串操作（char 陣列）
    # ──────────────────────────────────────────

    def write_string(self, addr: int, s: str):
        """將 Python str 寫入記憶體（含結尾 \\0）。
        呼叫者須確保已分配足夠空間。"""
        for i, ch in enumerate(s):
            self.write(addr + i, ord(ch))
        self.write(addr + len(s), 0)   # null terminator

    def read_string(self, addr: int) -> str:
        """從位址讀取 null-terminated 字串，回傳 Python str。"""
        if addr == NULL:
            raise MemoryError("null pointer dereference (read_string)", addr)
        chars = []
        offset = 0
        while True:
            if addr + offset not in self._cells:
                raise MemoryError(
                    f"read_string: unallocated address {addr + offset}", addr)
            c = self._cells[addr + offset]
            if c == 0:
                break
            chars.append(chr(c & 0xFF))
            offset += 1
            if offset > 65536:
                raise MemoryError("read_string: string too long (missing \\0?)", addr)
        return ''.join(chars)

    def strlen(self, addr: int) -> int:
        """計算 null-terminated 字串長度（不含 \\0）。"""
        return len(self.read_string(addr))

    def strcpy(self, dest: int, src: int):
        """將 src 位址的字串複製到 dest（含 \\0）。"""
        s = self.read_string(src)
        self.write_string(dest, s)

    def strcat(self, dest: int, src: int):
        """將 src 的字串串接到 dest 末尾。"""
        dest_str = self.read_string(dest)
        src_str  = self.read_string(src)
        self.write_string(dest + len(dest_str), src_str)

    def strcmp(self, s1_addr: int, s2_addr: int) -> int:
        """比較兩字串，回傳負/零/正整數。"""
        s1 = self.read_string(s1_addr)
        s2 = self.read_string(s2_addr)
        if s1 < s2: return -1
        if s1 > s2: return  1
        return 0

    def memset(self, addr: int, value: int, size: int):
        """將 addr 開始的 size 個 cell 全設為 value。"""
        for i in range(size):
            self.write(addr + i, value & 0xFF)

    # ──────────────────────────────────────────
    # 字串常數分配（唯讀區）
    # ──────────────────────────────────────────

    def alloc_string_literal(self, s: str) -> int:
        """分配並寫入一個字串常數，回傳位址。"""
        addr = self.alloc(len(s) + 1)
        self.write_string(addr, s)
        return addr

    # ──────────────────────────────────────────
    # 工具
    # ──────────────────────────────────────────

    @staticmethod
    def _to_int32(v: int) -> int:
        """截斷到 32-bit 有號整數。"""
        v = v & 0xFFFFFFFF
        if v >= 0x80000000:
            v -= 0x100000000
        return v

    @staticmethod
    def to_int32(v: int) -> int:
        return Memory._to_int32(v)

    @staticmethod
    def _to_int8(v: int) -> int:
        """截斷到 8-bit 有號整數（char）。"""
        v = v & 0xFF
        if v >= 0x80:
            v -= 0x100
        return v

    @staticmethod
    def to_int8(v: int) -> int:
        return Memory._to_int8(v)

    def is_allocated(self, addr: int) -> bool:
        return addr in self._cells

    def dump(self, start: int, end: int) -> str:
        """除錯用：印出 [start, end) 的記憶體內容。"""
        lines = []
        for a in range(start, end):
            v = self._cells.get(a, '?')
            lines.append(f"  [{a:4d}] = {v}")
        return '\n'.join(lines)
