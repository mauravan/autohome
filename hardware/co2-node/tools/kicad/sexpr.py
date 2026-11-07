#!/usr/bin/env python3
"""Deterministic s-expression writer for KiCad schematic/symbol output.

Node model: Sym(name, *children) for a list, plain str for atoms.
uid(*parts): stable uuid5 (NAMESPACE_URL, "co2-node:" + "/".join(parts)).
write(node, path): KiCad-style layout — leaf records stay on one line,
nodes with Sym children break one child per line, closing paren on its own
line at parent indent. Numbers via f"{v:g}", booleans as yes/no.

A node is "inline" when none of its children is a Sym (pure atom record).
"""
from __future__ import annotations

import uuid
from pathlib import Path


class Sym:
    __slots__ = ("name", "kids")

    def __init__(self, name: str, *kids):
        self.name = name
        self.kids = kids

    def __repr__(self):  # pragma: no cover - debug helper
        return f"Sym({self.name!r}, ...{len(self.kids)} kids)"


def uid(*parts: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "co2-node:" + "/".join(parts)))


def _fmt(atom) -> str:
    if isinstance(atom, bool):
        return "yes" if atom else "no"
    if isinstance(atom, float):
        return f"{atom:g}"
    if isinstance(atom, int):
        return str(atom)
    return str(atom)


def _inline(node: Sym) -> str:
    parts = [f"({node.name}"]
    for k in node.kids:
        if isinstance(k, Sym):
            parts.append(_inline(k))
        else:
            parts.append(_fmt(k))
    return " ".join(parts) + ")"


def _lines(node, depth: int, out: list[str]) -> None:
    if not isinstance(node, Sym):
        out.append("\t" * depth + _fmt(node))
        return
    name = node.name
    force1 = name.endswith("/1")
    if force1:
        name = name[:-2]
        depth = 1
    if not any(isinstance(k, Sym) for k in node.kids):
        out.append("\t" * depth + _inline(Sym(name, *node.kids)))
        return
    lead = []
    for k in node.kids:
        if isinstance(k, Sym):
            break
        lead.append(_fmt(k))
    rest = node.kids[len(lead):]
    if lead:
        out.append("\t" * depth + f"({name} " + " ".join(lead))
    elif name.endswith(":"):
        out.append("\t" * depth + f"({name[:-1]}")
    else:
        out.append("\t" * depth + f"({name}")
    for k in rest:
        _lines(k, depth + 1, out)
    out.append("\t" * depth + ")")


def dumps(node: Sym) -> str:
    out: list[str] = []
    _lines(node, 0, out)
    return "\n".join(out) + "\n"


def write(node: Sym, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dumps(node))
