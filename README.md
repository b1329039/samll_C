# Small-C Interpreter

**A Robust, Scoped-Memory Abstract Syntax Tree (AST) Interpreter for the Small-C Language**

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Project: System Software](https://img.shields.io/badge/Project-System_Software-orange)

A Python 3 implementation of a Small-C interpreter, featuring a multi-layered architecture including a recursive descent parser, a simulated linear memory model, and a feature-rich REPL environment. This project was developed as a final project for the **System Software** course (Spring 2026).

## Overview

Small-C is a subset of the C programming language, originally designed for microcomputers with limited resources. This interpreter provides a modern execution environment for Small-C, supporting:

- **Recursive Descent Parsing** — Translates source code into a high-level Abstract Syntax Tree (AST).
- **Simulated Memory Model** — Implements a 32-bit linear memory space with manual allocation for stack frames and arrays.
- **Lexical Scoping** — Supports nested scopes with proper variable shadowing and lifetime management.
- **Interactive REPL** — A powerful line-based development environment with debugging capabilities.

## Features

- **Standard C Syntax** — Supports `int`, `char`, pointers, arrays, and standard control flow (`if-else`, `while`, `for`, `do-while`,`swith-case`).
- **Rich Expression Support** — Implements 13 levels of operator precedence, including pointer arithmetic (`&`, `*`) and compound assignments (`+=`, `*=`, etc.).
- **Dynamic REPL Environment** — Interactive shell with commands like `APPEND`, `EDIT`, `LIST`, `VARS`, and `TRACE`.
- **Integrated Debugger** — Real-time execution tracing and variable/function table inspection.
- **Pre-processor Support** — Implements `#define` macro expansion for constants.
- **Extensive Standard Library** — Built-in functions for I/O (`printf`, `scanf`), strings (`strlen`, `strcpy`), and math (`pow`, `sqrt`, `rand`).

## System Architecture

The interpreter is structured into five core technical layers:

1. **Lexical Analyzer (Lexer)**: Uses regular expressions to tokenize Small-C source, handling comments, literals, and preprocessor directives.
2. **Syntax Analyzer (Parser)**: A recursive descent parser that handles operator precedence and generates a tree-structured AST.
3. **Symbol Table Manager**: Manages nested scopes and symbol metadata (types, addresses, signatures) for both variables and functions.
4. **Memory Controller**: Simulates a 32-bit memory space. It manages cell-based storage (4 bytes for `int`, 1 byte for `char`) and handles stack frame cleanup via high-water mark tracking.
5. **AST Interpreter**: A tree-walking evaluator that executes AST nodes by interacting with the Memory and Symbol Table components.

## Installation

### Prerequisites

- Python 3.10 or higher

### Setup

```bash
git clone https://github.com/your-username/smallC.git
cd smallC
```

No external dependencies are required as the project uses the Python standard library.

## Usage

### REPL Mode (Interactive)

```bash
python main.py
```

This launches the Small-C Interactive Interpreter (v1.0). You can enter Small-C code directly or use environment commands:

| Command | Description |
|-----------|-------------|
| `LOAD <file>` | Load a `.c` file into the buffer |
| `RUN` | Execute the current buffer |
| `LIST` | Display the source code with line numbers |
| `VARS` | Inspect all current variables and their memory values |
| `TRACE ON` | Enable line-by-line execution tracing |
| `CHECK` | Perform a syntax check without execution |

### Batch Mode (Direct Execution)

```bash
python main.py test.c
```

## Technical Details

### Memory Model
The interpreter simulates memory starting at address `1000`. 
- **Integers**: Occupy 4 cells.
- **Characters**: Occupy 1 cell.
- **Pointers**: Store the simulated integer address.
- **Stack Frames**: Managed by `free_after(mark)` calls during function returns, ensuring local variable isolation and automatic memory reclamation.

### Operator Precedence
The parser implements C-standard precedence levels:
1. Postfix: `()`, `[]`
2. Unary: `-`, `!`, `~`, `*`, `&`, `++`, `--`
3. Multiplicative: `*`, `/`, `%`
4. Additive: `+`, `-`
5. Shift: `<<`, `>>`
6. Relational: `<`, `<=`, `>`, `>=`
7. Equality: `==`, `!=`
8. Bitwise: `&`, `^`, `|`
9. Logical: `&&`, `||`
10. Assignment: `=`, `+=`, `-=`, `*=`, `/=`, `%=`

## Project Structure

```
smallC/
├── main.py              # Entry point (CLI & REPL dispatch)
├── repl.py              # Interactive environment logic
├── interpreter.py       # AST walking execution engine
├── parser.py            # Recursive descent parser & AST definitions
├── lexer.py             # Tokenizer & pre-processor logic
├── memory.py            # Simulated 32-bit linear memory model
├── symtable.py          # Scoped symbol table management
├── smallc_builtins.py   # Standard library implementations
└── GEMINI.md            # Project specific instructions
```

## Authors

- **Small-C Interpreter Team** — System Software Final Project, Spring 2026.

## Citation

If you use this interpreter for academic purposes, please cite it as:

> Small-C Interpreter Team. (2026). *Small-C AST Interpreter: A Scoped-Memory Implementation for System Software Education*. System Software Project, Spring 2026.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
