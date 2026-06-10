"""
Small-C Lexer
Tokenizes Small-C source code into a stream of tokens.
"""

import re
from enum import Enum, auto

class TokenType(Enum):
    # Literals
    INT_LIT    = auto()
    CHAR_LIT   = auto()
    STR_LIT    = auto()
    HEX_LIT    = auto()
    IDENT      = auto()

    # Keywords
    INT        = auto()
    CHAR       = auto()
    VOID       = auto()
    IF         = auto()
    ELSE       = auto()
    WHILE      = auto()
    FOR        = auto()
    DO         = auto()
    BREAK      = auto()
    CONTINUE   = auto()
    RETURN     = auto()
    SWITCH     = auto()
    CASE       = auto()
    DEFAULT    = auto()
    DEFINE     = auto()  # #define

    # Operators
    PLUS       = auto()  # +
    MINUS      = auto()  # -
    STAR       = auto()  # *
    SLASH      = auto()  # /
    PERCENT    = auto()  # %
    AMP        = auto()  # &
    PIPE       = auto()  # |
    CARET      = auto()  # ^
    TILDE      = auto()  # ~
    BANG       = auto()  # !
    LSHIFT     = auto()  # <<
    RSHIFT     = auto()  # >>
    AND        = auto()  # &&
    OR         = auto()  # ||
    EQ         = auto()  # ==
    NEQ        = auto()  # !=
    LT         = auto()  # <
    LE         = auto()  # <=
    GT         = auto()  # >
    GE         = auto()  # >=
    ASSIGN     = auto()  # =
    PLUS_EQ    = auto()  # +=
    MINUS_EQ   = auto()  # -=
    STAR_EQ    = auto()  # *=
    SLASH_EQ   = auto()  # /=
    PERCENT_EQ = auto()  # %=
    INC        = auto()  # ++
    DEC        = auto()  # --

    # Delimiters
    LPAREN     = auto()  # (
    RPAREN     = auto()  # )
    LBRACE     = auto()  # {
    RBRACE     = auto()  # }
    LBRACKET   = auto()  # [
    RBRACKET   = auto()  # ]
    SEMICOLON  = auto()  # ;
    COMMA      = auto()  # ,
    COLON      = auto()  # :

    # Special
    EOF        = auto()


KEYWORDS = {
    'int': TokenType.INT,
    'char': TokenType.CHAR,
    'void': TokenType.VOID,
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'while': TokenType.WHILE,
    'for': TokenType.FOR,
    'do': TokenType.DO,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'return': TokenType.RETURN,
    'switch': TokenType.SWITCH,
    'case': TokenType.CASE,
    'default': TokenType.DEFAULT,
}


class Token:
    def __init__(self, type: TokenType, value, line: int = 0, col: int = 0):
        self.type = type
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, line={self.line})'


class LexerError(Exception):
    def __init__(self, msg, line=0, col=0):
        super().__init__(msg)
        self.line = line
        self.col = col


def _parse_escape(s, pos):
    """Parse escape sequence starting after backslash. Returns (char, new_pos)."""
    if pos >= len(s):
        raise LexerError("Unterminated escape sequence")
    c = s[pos]
    pos += 1
    mapping = {'n': '\n', 't': '\t', '0': '\0', '\\': '\\', "'": "'", '"': '"', 'r': '\r'}
    if c in mapping:
        return mapping[c], pos
    raise LexerError(f"Unknown escape sequence: \\{c}")


def tokenize(source: str, start_line: int = 1):
    """Tokenize source string, returning list of Token objects."""
    tokens = []
    i = 0
    line = start_line
    line_start = 0

    def col():
        return i - line_start + 1

    n = len(source)

    while i < n:
        # Skip whitespace
        if source[i] in ' \t\r':
            i += 1
            continue

        if source[i] == '\n':
            line += 1
            i += 1
            line_start = i
            continue

        # Block comment
        if source[i:i+2] == '/*':
            i += 2
            while i < n and source[i:i+2] != '*/':
                if source[i] == '\n':
                    line += 1
                    line_start = i + 1
                i += 1
            if i >= n:
                raise LexerError("Unterminated block comment", line, col())
            i += 2
            continue

        # Line comment
        if source[i:i+2] == '//':
            while i < n and source[i] != '\n':
                i += 1
            continue

        # #define
        if source[i] == '#':
            # Read until end of line
            rest = source[i:]
            m = re.match(r'#\s*define\s+([A-Za-z_]\w*)\s+(.+)', rest)
            if m:
                name = m.group(1)
                val_str = m.group(2).strip()
                tok = Token(TokenType.DEFINE, (name, val_str), line, col())
                tokens.append(tok)
                i += m.end()
            else:
                # Skip unknown preprocessor directive
                while i < n and source[i] != '\n':
                    i += 1
            continue

        c = source[i]

        # String literal
        if c == '"':
            i += 1
            s = []
            while i < n and source[i] != '"':
                if source[i] == '\\':
                    i += 1
                    ch, i = _parse_escape(source, i)
                    s.append(ch)
                elif source[i] == '\n':
                    raise LexerError("Unterminated string literal", line, col())
                else:
                    s.append(source[i])
                    i += 1
            if i >= n:
                raise LexerError("Unterminated string literal", line, col())
            i += 1  # closing "
            tokens.append(Token(TokenType.STR_LIT, ''.join(s), line, col()))
            continue

        # Char literal
        if c == "'":
            i += 1
            if i >= n:
                raise LexerError("Unterminated char literal", line, col())
            if source[i] == '\\':
                i += 1
                ch, i = _parse_escape(source, i)
            else:
                ch = source[i]
                i += 1
            if i >= n or source[i] != "'":
                raise LexerError("Unterminated char literal", line, col())
            i += 1
            tokens.append(Token(TokenType.CHAR_LIT, ord(ch), line, col()))
            continue

        # Hex literal
        if source[i:i+2] in ('0x', '0X'):
            j = i + 2
            while j < n and source[j] in '0123456789abcdefABCDEF':
                j += 1
            val = int(source[i:j], 16)
            tokens.append(Token(TokenType.INT_LIT, val, line, col()))
            i = j
            continue

        # Integer literal
        if c.isdigit():
            j = i
            while j < n and source[j].isdigit():
                j += 1
            tokens.append(Token(TokenType.INT_LIT, int(source[i:j]), line, col()))
            i = j
            continue

        # Identifier or keyword
        if c.isalpha() or c == '_':
            j = i
            while j < n and (source[j].isalnum() or source[j] == '_'):
                j += 1
            word = source[i:j]
            tt = KEYWORDS.get(word, TokenType.IDENT)
            tokens.append(Token(tt, word, line, col()))
            i = j
            continue

        # Two-char operators
        two = source[i:i+2]
        two_map = {
            '<<': TokenType.LSHIFT,
            '>>': TokenType.RSHIFT,
            '&&': TokenType.AND,
            '||': TokenType.OR,
            '==': TokenType.EQ,
            '!=': TokenType.NEQ,
            '<=': TokenType.LE,
            '>=': TokenType.GE,
            '+=': TokenType.PLUS_EQ,
            '-=': TokenType.MINUS_EQ,
            '*=': TokenType.STAR_EQ,
            '/=': TokenType.SLASH_EQ,
            '%=': TokenType.PERCENT_EQ,
            '++': TokenType.INC,
            '--': TokenType.DEC,
        }
        if two in two_map:
            tokens.append(Token(two_map[two], two, line, col()))
            i += 2
            continue

        # Single-char operators/delimiters
        one_map = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.STAR,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '&': TokenType.AMP,
            '|': TokenType.PIPE,
            '^': TokenType.CARET,
            '~': TokenType.TILDE,
            '!': TokenType.BANG,
            '<': TokenType.LT,
            '>': TokenType.GT,
            '=': TokenType.ASSIGN,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            ';': TokenType.SEMICOLON,
            ',': TokenType.COMMA,
            ':': TokenType.COLON,
        }
        if c in one_map:
            tokens.append(Token(one_map[c], c, line, col()))
            i += 1
            continue

        raise LexerError(f"Unexpected character: {c!r}", line, col())

    tokens.append(Token(TokenType.EOF, None, line, col()))
    return tokens
