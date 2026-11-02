#!/usr/bin/env python3
"""Restore true unmodified lightmap diagnostic without disabling SSGI in gameplay.

Exact October FourWeek Master (+ optional LUT V05) source-only one-line change.
In r_lightmap 1 the shader in tr_shade.c renders baked lightmaps, but the
post-process RB_PostProcess SSGI block previously continued adding a quarter-res
GI buffer, creating horizontal bars not present in September's inactive SSGI.
With r_lightmap 0 the path and all graphical effects remain unmodified.
"""
from pathlib import Path
import hashlib
import sys

MARK = "DARKWOLF_CRYPT1_LIGHTMAP_SSGI_ISOLATION_V1"
ANCHOR = "\t\tif (r_ssgi && r_ssgi->integer)"
OLD_CONTEXT = (
    "\t// REND2_GI_2_V1_SCREEN_SPACE_LOCAL_INDIRECT\n"
    "\t// Quarter-resolution local screen-space color bounce using current color + copied depth."
)
def main(root: Path) -> None:
    p = root / "SP/code/rend2/tr_backend.c"
    text = p.read_text()
    if MARK in text:
        raise RuntimeError("Patch already applied: do not silently double-apply")
    assert text.count(OLD_CONTEXT) == 1, "Expected GI-2 post-process context not present"
    at = text.index(OLD_CONTEXT)
    start = text.index("\t{", at)
    end = text.index("\t\t// REND2_GI_2_V1_DIAGNOSTIC_TRACE", start)
    block = text[start:end]
    assert block.count(ANCHOR) == 1, "Exactly one SSGI generation branch expected"
    assert text.count(ANCHOR) == 1, "Unexpected other matching SSGI condition"
    assert 'ssgiDepth = tr.softParticleDepthImage ? tr.softParticleDepthImage : tr.hdrDepthImage;' in block
    new = (
        "\t\t// " + MARK + ": r_lightmap shows the baked lightmap alone.\n"
        "\t\t// SSGI stays fully enabled for every normal r_lightmap 0 frame.\n"
        "\t\tif (r_ssgi && r_ssgi->integer && !(r_lightmap && r_lightmap->integer))"
    )
    before = hashlib.sha256(text.encode()).hexdigest()
    text = text[:start] + block.replace(ANCHOR,new,1) + text[end:]
    assert text.count(MARK) == 1
    assert "if (r_ssgi && r_ssgi->integer && !(r_lightmap && r_lightmap->integer))" in text
    p.write_text(text)
    after = hashlib.sha256(text.encode()).hexdigest()
    print(f"{MARK}_PATCH_PASS before={before} after={after} only_file=tr_backend.c")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python apply.py <exact-Oct24-Rend2-source>")
    main(Path(sys.argv[1]))
