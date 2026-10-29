# SPDX-License-Identifier: MIT
# Copyright (c) 2026 s0912758806p
# Source: https://github.com/s0912758806p/agentic-sop-to-work
"""Console output that never crashes the run.

The engine's messages are bilingual and carry emoji. On a cp950 / cp1252 console (Windows
without PYTHONIOENCODING=utf-8) a plain print() raises UnicodeEncodeError mid-run — after
side effects, before the manifest is written. safe_print degrades the unencodable
characters to '?' for that stream instead; files are always written as UTF-8 regardless.
"""
import sys


def safe_print(*args, file=None, sep=" ", end="\n", flush=False):
    stream = file if file is not None else sys.stdout
    try:
        print(*args, file=stream, sep=sep, end=end, flush=flush)
    except UnicodeEncodeError:
        enc = getattr(stream, "encoding", None) or "ascii"
        text = sep.join(str(a) for a in args) + end
        stream.write(text.encode(enc, errors="replace").decode(enc, errors="replace"))
        if flush:
            stream.flush()
