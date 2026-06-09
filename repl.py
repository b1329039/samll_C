"""
Small-C REPL
互動式解譯器環境，實作所有環境指令。
"""

import os
import sys
from interpreter import Interpreter, RuntimeError_
from smallc_builtins import ExitCalled


class Repl:
    def __init__(self):
        self.buffer    : list[str] = []   # 程式緩衝區（行列表）
        self.modified  : bool = False     # 是否有未儲存修改
        self.interp    = Interpreter()
        self.trace_on  : bool = False
        self.last_file : str  = ''        # 上次 SAVE/LOAD 的檔名

    # ─────────────────── 主迴圈 ───────────────────

    def run(self):
        self._print_welcome()
        while True:
            try:
                raw = input("sc> ")
            except (EOFError, KeyboardInterrupt):
                print()
                self._do_quit()
                return

            line = raw.strip()
            if not line:
                continue

            upper = line.upper()
            cmd   = upper.split()[0]

            try:
                if   cmd in ('QUIT', 'EXIT'):   self._do_quit(); return
                elif cmd == 'ABOUT':             self._do_about()
                elif cmd == 'HELP':              self._do_help(line)
                elif cmd == 'NEW':               self._do_new()
                elif cmd == 'APPEND':            self._do_append()
                elif cmd == 'LIST':              self._do_list(line)
                elif cmd == 'EDIT':              self._do_edit(line)
                elif cmd == 'DELETE':            self._do_delete(line)
                elif cmd == 'INSERT':            self._do_insert(line)
                elif cmd == 'SAVE':              self._do_save(line)
                elif cmd == 'LOAD':              self._do_load(line)
                elif cmd == 'RUN':               self._do_run()
                elif cmd == 'CHECK':             self._do_check()
                elif cmd == 'TRACE':             self._do_trace(line)
                elif cmd == 'VARS':              self._do_vars()
                elif cmd == 'FUNCS':             self._do_funcs()
                elif cmd == 'CLEAR':             self._do_clear()
                else:
                    # 當成程式碼執行（互動模式）
                    self._exec_interactive(raw)
            except SystemExit:
                return
            except Exception as e:
                print(f"Error: {e}")

    # ─────────────────── 互動模式程式碼執行 ───────────────────

    def _exec_interactive(self, first_line: str):
        """
        執行互動模式輸入。
        若輸入是多行結構（if/while/for/do/函式定義），
        持續讀取直到大括號平衡。
        """
        source = self._read_multiline(first_line)
        try:
            self.interp.exec_interactive(source)
        except RuntimeError_ as e:
            print(e)
        except ExitCalled as e:
            print(f"Program exited with return value {e.code}.")

    def _read_multiline(self, first_line: str) -> str:
        """若大括號未平衡，持續讀取後續行。"""
        lines  = [first_line]
        depth  = first_line.count('{') - first_line.count('}')
        indent = 1

        while depth > 0:
            try:
                cont = input(f"{'  ' * indent}> ")
            except (EOFError, KeyboardInterrupt):
                break
            lines.append(cont)
            depth += cont.count('{') - cont.count('}')
            if depth > 0:
                indent += 1
            else:
                indent = max(1, indent - 1)

        return '\n'.join(lines)

    # ─────────────────── 環境指令 ───────────────────

    def _do_about(self):
        print("=" * 44)
        print("  Small-C Interactive Interpreter v1.0")
        print("  System Software Final Project, Spring 2026")
        print("=" * 44)

    def _do_help(self, line):
        parts = line.split()
        if len(parts) >= 2:
            self._do_help_cmd(parts[1].upper())
            return
        print("""Available commands:
  ABOUT               Show interpreter info
  HELP [cmd]          Show help (or help for cmd)
  NEW                 Clear program buffer and reset state
  APPEND              Enter append mode (add lines to end)
  LIST [n|n1-n2]      List program buffer
  EDIT <n>            Edit line n
  DELETE <n|n1-n2>    Delete line(s)
  INSERT <n>          Insert lines before line n
  SAVE <filename>     Save buffer to file
  LOAD <filename>     Load file into buffer
  RUN                 Execute the program
  CHECK               Check syntax without running
  TRACE ON|OFF        Toggle execution trace
  VARS                Show all variables
  FUNCS               Show all functions
  CLEAR               Clear the screen
  QUIT / EXIT         Exit the interpreter""")

    def _do_help_cmd(self, cmd):
        helps = {
            'LOAD':   'LOAD <filename>  — Load a Small-C source file into the buffer.',
            'SAVE':   'SAVE <filename>  — Save the current buffer to a file.',
            'LIST':   'LIST [n|n1-n2]   — List all lines, line n, or range n1-n2.',
            'EDIT':   'EDIT <n>         — Edit line n interactively.',
            'DELETE': 'DELETE <n|n1-n2> — Delete line n or range n1-n2.',
            'INSERT': 'INSERT <n>       — Insert new lines before line n.',
            'APPEND': 'APPEND           — Append lines at the end of the buffer.',
            'NEW':    'NEW              — Clear buffer and reset all state.',
            'RUN':    'RUN              — Run the current program.',
            'CHECK':  'CHECK            — Check syntax without running.',
            'TRACE':  'TRACE ON|OFF     — Enable/disable execution trace.',
            'VARS':   'VARS             — Display all current variables.',
            'FUNCS':  'FUNCS            — Display all defined functions.',
            'CLEAR':  'CLEAR            — Clear the terminal screen.',
            'ABOUT':  'ABOUT            — Show interpreter name, version, author, semester.',
        }
        msg = helps.get(cmd, f"No help available for '{cmd}'.")
        print(msg)

    def _do_new(self):
        if self.modified and self.buffer:
            ans = input("Unsaved changes. Discard? [y/N] ").strip().lower()
            if ans != 'y':
                print("Cancelled.")
                return
        self.buffer   = []
        self.modified = False
        self.interp.reset()
        print("All cleared.")

    def _do_append(self):
        """進入 APPEND 模式，讀取到獨立的 '.' 為止。"""
        n = len(self.buffer) + 1
        while True:
            try:
                raw = input(f"{n:4d}> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if raw.strip() == '.':
                break
            self.buffer.append(raw)
            self.modified = True
            n += 1

    def _do_list(self, line):
        parts = line.split()
        if not self.buffer:
            print("(buffer is empty)")
            return

        if len(parts) == 1:
            # LIST 全部
            for i, ln in enumerate(self.buffer, 1):
                print(f"{i:4d}: {ln}")
            return

        arg = parts[1]
        if '-' in arg:
            # LIST n1-n2
            try:
                n1, n2 = arg.split('-')
                n1, n2 = int(n1), int(n2)
            except ValueError:
                print("Usage: LIST n1-n2")
                return
            for i in range(n1, min(n2 + 1, len(self.buffer) + 1)):
                print(f"{i:4d}: {self.buffer[i-1]}")
        else:
            # LIST n
            try:
                n = int(arg)
            except ValueError:
                print("Usage: LIST <n>")
                return
            if 1 <= n <= len(self.buffer):
                print(f"{n:4d}: {self.buffer[n-1]}")
            else:
                print(f"Line {n} out of range (1-{len(self.buffer)}).")

    def _do_edit(self, line):
        parts = line.split()
        if len(parts) < 2:
            print("Usage: EDIT <n>")
            return
        try:
            n = int(parts[1])
        except ValueError:
            print("Usage: EDIT <n>")
            return
        if not (1 <= n <= len(self.buffer)):
            print(f"Line {n} out of range.")
            return
        print(f"{n:4d}: {self.buffer[n-1]}")
        try:
            new_line = input(f"{n:4d}: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if new_line != '':   # Enter 保留原行
            self.buffer[n-1] = new_line
            self.modified = True

    def _do_delete(self, line):
        parts = line.split()
        if len(parts) < 2:
            print("Usage: DELETE <n|n1-n2>")
            return
        arg = parts[1]
        if '-' in arg:
            try:
                n1, n2 = arg.split('-')
                n1, n2 = int(n1), int(n2)
            except ValueError:
                print("Usage: DELETE n1-n2")
                return
            n1 = max(1, n1)
            n2 = min(len(self.buffer), n2)
            del self.buffer[n1-1:n2]
            self.modified = True
            print(f"Deleted lines {n1}-{n2}.")
        else:
            try:
                n = int(arg)
            except ValueError:
                print("Usage: DELETE <n>")
                return
            if not (1 <= n <= len(self.buffer)):
                print(f"Line {n} out of range.")
                return
            del self.buffer[n-1]
            self.modified = True
            print(f"Deleted line {n}.")

    def _do_insert(self, line):
        parts = line.split()
        if len(parts) < 2:
            print("Usage: INSERT <n>")
            return
        try:
            n = int(parts[1])
        except ValueError:
            print("Usage: INSERT <n>")
            return
        if not (1 <= n <= len(self.buffer) + 1):
            print(f"Line {n} out of range.")
            return

        new_lines = []
        cur = n
        while True:
            try:
                raw = input(f"{cur:4d}> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if raw.strip() == '.':
                break
            new_lines.append(raw)
            cur += 1

        self.buffer[n-1:n-1] = new_lines
        self.modified = True
        print(f"Inserted {len(new_lines)} line(s) before line {n}.")

    def _do_save(self, line):
        parts = line.split()
        if len(parts) < 2:
            if self.last_file:
                filename = self.last_file
            else:
                print("Usage: SAVE <filename>")
                return
        else:
            filename = parts[1]
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for ln in self.buffer:
                    f.write(ln + '\n')
            self.modified  = False
            self.last_file = filename
            print(f"Saved {len(self.buffer)} lines to '{filename}'.")
        except IOError as e:
            print(f"Error saving '{filename}': {e}")

    def _do_load(self, line):
        parts = line.split()
        if len(parts) < 2:
            print("Usage: LOAD <filename>")
            return
        filename = parts[1]
        if self.modified and self.buffer:
            ans = input("Unsaved changes. Discard? [y/N] ").strip().lower()
            if ans != 'y':
                print("Cancelled.")
                return
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            self.buffer    = lines
            self.modified  = False
            self.last_file = filename
            self.interp.reset()
            print(f"Loaded {len(lines)} lines from '{filename}'.")
        except FileNotFoundError:
            print(f"Error: file '{filename}' not found.")
        except IOError as e:
            print(f"Error loading '{filename}': {e}")

    def _do_run(self):
        if not self.buffer:
            print("Buffer is empty. Nothing to run.")
            return
        source = '\n'.join(self.buffer)
        self.interp.trace = self.trace_on
        try:
            self.interp.run_program(source)
        except RuntimeError_ as e:
            line_info = f" (line {e.line})" if e.line else ""
            print(f"{e}{line_info}")
        except ExitCalled as e:
            print(f"Program exited with return value {e.code}.")

    def _do_check(self):
        if not self.buffer:
            print("Buffer is empty.")
            return
        source = '\n'.join(self.buffer)
        errors = self.interp.check_syntax(source)
        if errors:
            for err in errors:
                print(err)
            print(f"{len(errors)} error(s) found.")
        else:
            print("No errors found.")

    def _do_trace(self, line):
        parts = line.upper().split()
        if len(parts) < 2:
            print("Usage: TRACE ON|OFF")
            return
        if parts[1] == 'ON':
            self.trace_on = True
            self.interp.trace = True
            print("Trace mode enabled.")
        elif parts[1] == 'OFF':
            self.trace_on = False
            self.interp.trace = False
            print("Trace mode disabled.")
        else:
            print("Usage: TRACE ON|OFF")

    def _do_vars(self):
        print(self.interp.dump_vars())

    def _do_funcs(self):
        print(self.interp.dump_funcs())

    def _do_clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def _do_quit(self):
        if self.modified and self.buffer:
            try:
                ans = input("Unsaved changes. Discard and quit? [y/N] ").strip().lower()
                if ans != 'y':
                    print("Cancelled.")
                    return
            except (EOFError, KeyboardInterrupt):
                print()
        print("Goodbye.")

    def _print_welcome(self):
        print("=" * 44)
        print("  Small-C Interactive Interpreter v1.0")
        print("  System Software Final Project, Spring 2026")
        print("=" * 44)
        print("Type `HELP` for a list of commands.")
        print()
