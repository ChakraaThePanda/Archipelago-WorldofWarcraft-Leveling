"""
A small, deliberately restricted Lua table-literal parser and serializer, used by
WoWLevelingClient.py to read the WoW addon's SavedVariables file (ArchipelagoWoW.lua,
written by the game itself at logout/ReloadUI) and to write our own sidecar
SavedVariables file (ArchipelagoWoW_Bridge.lua, read by the game at its next login).

Deliberately NOT a general Lua interpreter and NOT based on exec/eval/loadstring of any
kind -- SavedVariables files are plain data written by WoW's own serializer, but treating
them as "just run it as Lua/Python" would mean executing arbitrary code from a file this
process doesn't fully control (in principle, a hand-edited or corrupted SavedVariables
file). This only understands the fixed grammar WoW's serializer actually produces:
nested table constructors containing strings, numbers, booleans, nil, and other tables --
nothing else (no function calls, operators, control flow, etc.), which is both simpler
and strictly safer than embedding a real Lua sandbox.

Verified against real SavedVariables files on this machine (see
WTF/Account/*/*/*/SavedVariables/*.lua for e.g. InFlight.lua, StrudelStore.lua) which all
follow the same style this module reads and writes: tab-indented, `["key"] = value,`
entries (bracket-quoted string keys, `[N] = value` for array entries), trailing comma
after every entry including the last, double-quoted strings.
"""
from __future__ import annotations

import re
import typing

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
      (?P<WS>\s+)
    | (?P<LCOMMENT>--\[\[.*?\]\])
    | (?P<COMMENT>--[^\n]*)
    | (?P<STRING>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
    | (?P<NUMBER>-?\d+\.\d+(?:[eE][+-]?\d+)?|-?\d+(?:[eE][+-]?\d+)?)
    | (?P<NAME>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<PUNCT>[{}\[\]=,;])
    """,
    re.VERBOSE | re.DOTALL,
)

_STRING_ESCAPES = {
    "n": "\n", "r": "\r", "t": "\t", "a": "\a", "b": "\b", "f": "\f", "v": "\v",
    "\\": "\\", '"': '"', "'": "'", "\n": "\n",
}


class LuaParseError(Exception):
    """Raised for any malformed/unsupported Lua source encountered while parsing a
    SavedVariables file. Callers should treat this as "retry on the next poll tick" --
    it can legitimately happen if the game is mid-write (extremely unlikely given writes
    only happen at logout/ReloadUI, but not impossible) or the addon's shape changed."""


Token = typing.Tuple[str, str]  # (kind, raw_text)


def _tokenize(text: str) -> typing.List[Token]:
    tokens: typing.List[Token] = []
    pos = 0
    length = len(text)
    while pos < length:
        m = _TOKEN_RE.match(text, pos)
        if m is None:
            raise LuaParseError(f"unexpected character {text[pos]!r} at offset {pos}")
        pos = m.end()
        kind = m.lastgroup
        if kind in ("WS", "COMMENT", "LCOMMENT"):
            continue
        tokens.append((kind, m.group()))
    return tokens


def _unescape_lua_string(raw: str) -> str:
    """`raw` includes its surrounding quotes, e.g. '"Un\\'Goro Crater"'."""
    quote = raw[0]
    body = raw[1:-1]
    out: typing.List[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            out.append(_STRING_ESCAPES.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

LuaValue = typing.Union[None, bool, int, float, str, "LuaTable"]
LuaTable = typing.Dict[typing.Union[str, int], "LuaValue"]

_INT_RE = re.compile(r"-?\d+$")


class _Parser:
    def __init__(self, tokens: typing.List[Token]):
        self._tokens = tokens
        self._i = 0

    def _peek(self) -> typing.Optional[Token]:
        return self._tokens[self._i] if self._i < len(self._tokens) else None

    def _peek_next(self) -> typing.Optional[Token]:
        return self._tokens[self._i + 1] if self._i + 1 < len(self._tokens) else None

    def _advance(self) -> Token:
        tok = self._peek()
        if tok is None:
            raise LuaParseError("unexpected end of input")
        self._i += 1
        return tok

    def _expect_punct(self, ch: str) -> None:
        tok = self._advance()
        if tok[0] != "PUNCT" or tok[1] != ch:
            raise LuaParseError(f"expected {ch!r}, got {tok!r}")

    def parse_value(self) -> LuaValue:
        tok = self._peek()
        if tok is None:
            raise LuaParseError("unexpected end of input while parsing a value")
        kind, raw = tok

        if kind == "PUNCT" and raw == "{":
            return self.parse_table()
        if kind == "STRING":
            self._advance()
            return _unescape_lua_string(raw)
        if kind == "NUMBER":
            self._advance()
            return int(raw) if _INT_RE.match(raw) else float(raw)
        if kind == "NAME" and raw == "true":
            self._advance()
            return True
        if kind == "NAME" and raw == "false":
            self._advance()
            return False
        if kind == "NAME" and raw == "nil":
            self._advance()
            return None
        raise LuaParseError(f"unexpected token {tok!r} while parsing a value")

    def parse_table(self) -> LuaTable:
        self._expect_punct("{")
        result: LuaTable = {}
        array_index = 1

        while True:
            tok = self._peek()
            if tok is None:
                raise LuaParseError("unterminated table (missing '}')")
            if tok[0] == "PUNCT" and tok[1] == "}":
                self._advance()
                break

            if tok[0] == "PUNCT" and tok[1] == "[":
                self._advance()
                key = self.parse_value()
                self._expect_punct("]")
                self._expect_punct("=")
                value = self.parse_value()
                if not isinstance(key, (str, int)) or isinstance(key, bool):
                    raise LuaParseError(f"unsupported table key type: {key!r}")
                result[key] = value
            elif tok[0] == "NAME" and tok[1] not in ("true", "false", "nil"):
                nxt = self._peek_next()
                if nxt is not None and nxt[0] == "PUNCT" and nxt[1] == "=":
                    name = self._advance()[1]
                    self._advance()  # '='
                    value = self.parse_value()
                    result[name] = value
                else:
                    result[array_index] = self.parse_value()
                    array_index += 1
            else:
                result[array_index] = self.parse_value()
                array_index += 1

            sep = self._peek()
            if sep is not None and sep[0] == "PUNCT" and sep[1] in (",", ";"):
                self._advance()
            elif sep is not None and sep[0] == "PUNCT" and sep[1] == "}":
                continue  # loop head consumes it
            elif sep is None:
                raise LuaParseError("unterminated table (missing '}')")
            else:
                raise LuaParseError(f"expected ',' or '}}' after table entry, got {sep!r}")

        return result


def parse_saved_variables(text: str, var_name: str) -> LuaValue:
    """Finds the (first) top-level `var_name = <value>` assignment in `text` and parses
    just that value -- everything else in the file (other globals, comments, a leading
    blank line, etc., all of which real SavedVariables files routinely contain) is
    ignored. Raises LuaParseError if the assignment isn't found or doesn't parse."""
    tokens = _tokenize(text)
    for i, tok in enumerate(tokens):
        if tok[0] == "NAME" and tok[1] == var_name:
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if nxt is not None and nxt[0] == "PUNCT" and nxt[1] == "=":
                parser = _Parser(tokens[i + 2:])
                return parser.parse_value()
    raise LuaParseError(f"no assignment to {var_name!r} found")


def lua_table_to_list(value: typing.Any) -> list:
    """Converts a parsed Lua array-style table (e.g. `{ [1] = 12, [2] = 15 }`, parsed
    into a Python dict keyed 1..N) into a plain ordered Python list. Tolerates the field
    being absent, empty, or not shaped like an array (returns [] rather than raising --
    callers poll this file repeatedly and should just skip a tick on an unexpected shape,
    not crash the client)."""
    if isinstance(value, list):
        return list(value)
    if not isinstance(value, dict):
        return []
    int_keys = [k for k in value.keys() if isinstance(k, int)]
    if len(int_keys) != len(value):
        return []  # mixed/string-keyed table -- not actually array-shaped
    return [value[k] for k in sorted(int_keys)]


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------

def _escape_lua_string(s: str) -> str:
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return "".join(out)


def _format_key(key: typing.Union[str, int]) -> str:
    if isinstance(key, bool):
        raise TypeError("bool table keys are not supported")
    if isinstance(key, int):
        return f"[{key}]"
    if isinstance(key, str):
        return f'["{_escape_lua_string(key)}"]'
    raise TypeError(f"unsupported table key type: {type(key)!r}")


def _dump_value(value: typing.Any, indent: int, out: typing.List[str]) -> None:
    if value is None:
        out.append("nil")
    elif isinstance(value, bool):
        out.append("true" if value else "false")
    elif isinstance(value, int):
        out.append(str(value))
    elif isinstance(value, float):
        # Whole-number floats (e.g. epoch timestamps that came back as float) render
        # without a trailing ".0" -- Lua's number type doesn't distinguish int/float
        # the way Python does, so this is lossless from the addon's point of view.
        out.append(str(int(value)) if value.is_integer() else repr(value))
    elif isinstance(value, str):
        out.append(f'"{_escape_lua_string(value)}"')
    elif isinstance(value, dict):
        pad = "\t" * (indent + 1)
        out.append("{\n")
        for k, v in value.items():
            out.append(f"{pad}{_format_key(k)} = ")
            _dump_value(v, indent + 1, out)
            out.append(",\n")
        out.append("\t" * indent + "}")
    elif isinstance(value, (list, tuple)):
        pad = "\t" * (indent + 1)
        out.append("{\n")
        for i, v in enumerate(value, start=1):
            out.append(f"{pad}[{i}] = ")
            _dump_value(v, indent + 1, out)
            out.append(",\n")
        out.append("\t" * indent + "}")
    else:
        raise TypeError(f"unsupported value type for Lua serialization: {type(value)!r}")


def dumps_lua_assignment(var_name: str, data: typing.Any) -> str:
    """Renders `var_name = <data>` as valid, WoW-SavedVariables-style Lua source
    (tab-indented, bracket-quoted keys, trailing comma per entry) -- see module
    docstring. `data` is a plain Python dict/list/str/int/float/bool/None tree, the
    exact shape produced by parse_saved_variables/parse_table above."""
    out: typing.List[str] = [f"{var_name} = "]
    _dump_value(data, 0, out)
    out.append("\n")
    return "".join(out)
