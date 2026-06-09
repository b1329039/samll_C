"""
Small-C Interactive Interpreter
Entry point — python3 main.py
"""

import sys
from repl import Repl


def main():
    # 若有命令列引數，直接執行檔案（非互動模式）
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: file '{filename}' not found.")
            sys.exit(1)

        from interpreter import Interpreter, RuntimeError_
        from smallc_builtins import ExitCalled
        interp = Interpreter()
        try:
            interp.run_program(source)
        except RuntimeError_ as e:
            print(e)
            sys.exit(1)
        except ExitCalled as e:
            sys.exit(e.code)
        return

    # 互動模式
    repl = Repl()
    repl.run()


if __name__ == '__main__':
    main()
