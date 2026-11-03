#!/usr/bin/env python3
"""Compile and execute IFLC behavior tests against the reconstructed renderer.

This is an in-process CPU harness. It does not claim to render a GPU frame.
All production functions under test are compiled from SP/code/rend2/tr_scene.c.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path, help="Root containing SP/code")
    parser.add_argument("--output", type=Path, help="Optional JSON result file")
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    code = args.source_root.resolve() / "SP" / "code"
    tests = Path(__file__).resolve().parent
    if not (code / "rend2" / "tr_iflc.inc").is_file():
        parser.error("Production tr_iflc.inc has not been installed in the source tree")
    compiler = os.environ.get("CC", "gcc")
    with tempfile.TemporaryDirectory(prefix="dw-iflc-cpu-") as directory:
        binary = Path(directory) / "iflc_cpu_tests"
        # Link only the production paths reached by the harness. Cvars imported
        # from other renderer objects are mock storage, never scraped assertions.
        header = (code / "rend2" / "tr_local.h").read_text(errors="replace")
        declared = set(re.findall(r"extern\s+cvar_t\s*\*\s*(\w+)\s*;", header))
        explicit = set(re.findall(r"cvar_t\s*\*\s*(\w+)\s*=", (tests / "iflc_cpu_tests.c").read_text()))
        cvar_mocks = Path(directory) / "cvar_mocks.c"
        cvar_mocks.write_text('#include "tr_local.h"\nstatic cvar_t mockCvar;\n' +
            "\n".join(f"cvar_t *{name} = &mockCvar;" for name in sorted(declared-explicit)) + "\n")
        flags = ["-std=gnu99", "-O1", "-g", "-ffunction-sections", "-fdata-sections",
                 "-DUSE_LOCAL_HEADERS", "-DSP", '-DARCH_STRING="x86_64"',
                 "-Werror=implicit-function-declaration",
                 "-Wno-unused-function", "-Wno-unused-variable",
                 "-I", str(code / "rend2"), "-I", str(code / "SDL2" / "include")]
        if args.sanitize:
            # The unmodified renderer uses signed (1 << 31) for REF_FORCE_DLIGHT.
            # Do not mislabel that known baseline macro as a new IFLC regression.
            flags += ["-fsanitize=address,undefined", "-fno-sanitize=shift-base", "-fno-omit-frame-pointer"]
        command = [compiler, *flags, str(tests / "iflc_cpu_tests.c"), str(cvar_mocks),
                   str(code / "qcommon" / "q_shared.c"), str(code / "qcommon" / "q_math.c"),
                   "-Wl,--gc-sections", "-lm", "-o", str(binary)]
        compile_result = subprocess.run(command, text=True, capture_output=True)
        if compile_result.returncode:
            print(compile_result.stdout, end="")
            print(compile_result.stderr, end="")
            return compile_result.returncode
        run_result = subprocess.run([str(binary)], text=True, capture_output=True,
                                    env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0",
                                         "UBSAN_OPTIONS": "halt_on_error=1"})
        print(run_result.stdout, end="")
        print(run_result.stderr, end="")
        result = {"kind": "production-cpu-behavior-harness", "gpu_tested": False,
                  "sanitizers": args.sanitize, "compile_exit": compile_result.returncode,
                  "test_exit": run_result.returncode, "output": run_result.stdout,
                  "stderr": run_result.stderr}
        result["source_sha256"] = {
            str(path.relative_to(code)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (code / "rend2" / "tr_scene.c", code / "rend2" / "tr_iflc.inc",
                         code / "rend2" / "tr_local.h", code / "qcommon" / "q_shared.c",
                         code / "qcommon" / "q_math.c")}
        if args.sanitize:
            result["sanitizer_exclusions"] = [
                "shift-base: baseline REF_FORCE_DLIGHT signed high-bit marker",
                "LeakSanitizer: executor /proc task enumeration unavailable"]
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
        return run_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
