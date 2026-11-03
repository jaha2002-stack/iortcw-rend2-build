#!/usr/bin/env python3
"""Compile actual IFLC backend functions against CPU-only GL/renderer stubs.

This checks uniform values and source selection inputs. It is not a GPU or
gameplay test. The production function bodies are extracted anew on each run.
"""
import argparse
import pathlib
import re
import subprocess
import tempfile


FUNCTIONS = (
    "RB_IFLC_BaseColor",
    "RB_IFLC_BaseRadius",
    "RB_IFLC_FireVolumeGain",
    "RB_LocalVolumetricDlightScore",
    "RB_LocalVolumetricRenderEx",
    "RB_LocalVolumetricRender",
)


def extract_function(source, name):
    match = re.search(r"^static [^\n]+\b" + re.escape(name) + r"\(", source, re.M)
    if not match:
        raise ValueError("Missing production function: " + name)
    opening = source.index("{", match.start())
    depth = 0
    state = "code"
    escaped = False
    i = opening
    while i < len(source):
        c = source[i]
        following = source[i + 1] if i + 1 < len(source) else ""
        if state == "line":
            if c == "\n":
                state = "code"
        elif state == "block":
            if c == "*" and following == "/":
                state = "code"
                i += 1
        elif state in ("string", "char"):
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == ('"' if state == "string" else "'"):
                state = "code"
        elif c == "/" and following == "/":
            state = "line"
            i += 1
        elif c == "/" and following == "*":
            state = "block"
            i += 1
        elif c == '"':
            state = "string"
        elif c == "'":
            state = "char"
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():i + 1]
        i += 1
    raise ValueError("Unclosed production function: " + name)


def run(source_root, output, compiler):
    here = pathlib.Path(__file__).resolve().parent
    source_path = source_root / "SP/code/rend2/tr_backend.c"
    source = source_path.read_text(encoding="utf-8")
    bodies = "\n\n".join(extract_function(source, name) for name in FUNCTIONS)
    harness = (
        (here / "backend_tests_support.h").read_text()
        + "\n/* Actual production functions from " + str(source_path) + " */\n"
        + bodies
        + "\n"
        + (here / "backend_tests_cases.c").read_text()
    )
    output.mkdir(parents=True, exist_ok=True)
    c_file = output / "backend_tests_extracted.c"
    binary = output / "backend_tests"
    c_file.write_text(harness, encoding="utf-8")
    subprocess.run(
        [compiler, "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror",
         str(c_file), "-lm", "-o", str(binary)], check=True
    )
    subprocess.run([str(binary.resolve())], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--cc", default="gcc")
    args = parser.parse_args()
    if args.output:
        run(args.source_root, args.output, args.cc)
    else:
        with tempfile.TemporaryDirectory(prefix="iflc-backend-tests-") as directory:
            run(args.source_root, pathlib.Path(directory), args.cc)


if __name__ == "__main__":
    main()
