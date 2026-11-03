#!/usr/bin/env python3
"""Unified PCPS V6.1: replace only the failing baked-preview C function on verified V6 source."""
import base64
import hashlib
import lzma
import sys
from pathlib import Path

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply.py /path/to/iortcw-source")
    src = Path(sys.argv[1]) / "SP/code/rend2/tr_main.c"
    text = src.read_text()
    begin = text.index("static void DWPS6_BakedPreview_f(void)\n{")
    end = text.index("\nstatic void DWPS6_BakedCancel_f(void)", begin)
    before = text[begin:end].encode()
    assert sha(before) == "fac4d601cf2b7327c8c6cc81cd93c65373a076f502e1951773c5e885c3aec1d2", (
        "refuse unknown V6 baked editor version", sha(before)
    )
    encoded = (Path(__file__).with_name("baked_preview_v61.xz.b64")).read_text().strip()
    replacement = lzma.decompress(base64.b64decode(encoded))
    assert sha(replacement) == "ccbb1c69df2b142387c81f63ba9f5e53c9bc2d247e4c7428783c1084837e3b27", (
        "replacement checksum mismatch", sha(replacement)
    )
    new = text[:begin] + replacement.decode() + text[end:]
    assert new.count("DARKWOLF_UNIFIED_PCPS_V61_BAKED_ADAPTIVE_REFERENCE") == 1
    assert new.count('DWPS6_BakedPreview_f(void)\n{') == 1
    src.write_text(new)
    print("PCPS_UNIFIED_V61_EXACT_BAKED_PREVIEW_PATCH_PASS",
          "old", sha(before), "new", sha(replacement),
          "complete_tr_main", sha(new.encode()))

if __name__ == "__main__":
    main()
