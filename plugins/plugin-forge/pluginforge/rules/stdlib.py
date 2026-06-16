# SPDX-License-Identifier: MIT
"""Tier-1 (strict): the plugin's engine code imports only stdlib (or its own packages).
Scans every .py under the plugin EXCEPT tests/, examples/, __pycache__/. Mirrors the
test_no_third_party invariant, generalized to an arbitrary plugin."""
import ast
import glob
import os
import sys
from ..model import Finding

_STDLIB = set(getattr(sys, "stdlib_module_names", ()))
_FALLBACK = {
    "abc", "argparse", "array", "ast", "asyncio", "base64", "bdb", "binascii", "bisect",
    "builtins", "bz2", "calendar", "cgi", "cmath", "cmd", "codecs", "codeop", "collections",
    "colorsys", "compileall", "concurrent", "configparser", "contextlib", "contextvars",
    "copy", "copyreg", "csv", "ctypes", "curses", "dataclasses", "datetime", "decimal",
    "difflib", "dis", "doctest", "email", "encodings", "enum", "errno", "faulthandler",
    "fcntl", "filecmp", "fileinput", "fnmatch", "fractions", "ftplib", "functools", "gc",
    "getopt", "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib", "heapq",
    "hmac", "html", "http", "imaplib", "imp", "importlib", "inspect", "io", "ipaddress",
    "itertools", "json", "keyword", "linecache", "locale", "logging", "lzma", "mailbox",
    "marshal", "math", "mimetypes", "mmap", "multiprocessing", "numbers", "operator", "os",
    "pathlib", "pickle", "pickletools", "pkgutil", "platform", "plistlib", "poplib",
    "posixpath", "pprint", "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc",
    "queue", "quopri", "random", "re", "reprlib", "resource", "runpy", "sched", "secrets",
    "select", "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtplib", "socket",
    "socketserver", "sqlite3", "ssl", "stat", "statistics", "string", "stringprep", "struct",
    "subprocess", "symtable", "sys", "sysconfig", "tarfile", "tempfile", "termios", "textwrap",
    "threading", "time", "timeit", "token", "tokenize", "trace", "traceback", "tracemalloc",
    "tty", "types", "typing", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
    "warnings", "wave", "weakref", "webbrowser", "wsgiref", "xml", "xmlrpc", "zipapp",
    "zipfile", "zipimport", "zlib", "zoneinfo",
}
_SKIP_DIRS = {"__pycache__", "tests", "examples", ".pytest_cache"}


def _engine_pyfiles(plugin_dir):
    out = []
    for root, dirs, files in os.walk(plugin_dir):
        dirs[:] = [x for x in dirs if x not in _SKIP_DIRS]
        out.extend(os.path.join(root, fn) for fn in files if fn.endswith(".py"))
    return out


def _local_packages(plugin_dir):
    local = set()
    for nm in os.listdir(plugin_dir):
        sub = os.path.join(plugin_dir, nm)
        if os.path.isdir(sub) and glob.glob(os.path.join(sub, "*.py")):
            local.add(nm)
    return local


def check(plugin_dir, strict):
    if not strict:
        return []
    name = os.path.basename(os.path.normpath(plugin_dir))
    allowed = (_STDLIB or _FALLBACK) | _local_packages(plugin_dir)
    findings = []
    for path in _engine_pyfiles(plugin_dir):
        rel = os.path.relpath(path, plugin_dir)
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
        except (OSError, SyntaxError) as e:
            findings.append(Finding(f"stdlib:parse:{rel}", "stdlib", "HARD", name, rel,
                                    f"cannot parse: {e}"))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top not in allowed:
                        findings.append(Finding(f"stdlib:{rel}:{alias.name}", "stdlib", "HARD",
                                                name, rel, f"non-stdlib import: {alias.name}"))
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                top = node.module.split(".")[0]
                if top not in allowed:
                    findings.append(Finding(f"stdlib:{rel}:from:{node.module}", "stdlib", "HARD",
                                            name, rel, f"non-stdlib import: from {node.module}"))
    return findings
