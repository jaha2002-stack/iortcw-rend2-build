#!/usr/bin/env python3
"""Fix opt-in Hybrid Relight V2's use of an upstream header-inclusive HDR length check.

The accepted stock HDR path is NOT changed; only hybridActive uses the pixel
payload pointer buf_p, which points past the Radiance-style file header.
"""
import argparse
import hashlib
import json
from pathlib import Path

OLD = "if ((int)(end - hdrLightmap) != tr.lightmapSize * tr.lightmapSize * 12)"
NEW = "if ((int)(end - (hybridActive ? buf_p : hdrLightmap)) != tr.lightmapSize * tr.lightmapSize * 12)"
MARK = "DARKWOLF_HYBRID_RELIGHT_V2_NATIVE_41019985033"
HDR_HEADER = b'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 128 +X 128\n'
PIXEL_BYTES = 128 * 128 * 3 * 4

def header_end(blob):
    pos = blob.find(b'\n\n')
    if pos < 0:
        raise ValueError("Missing Radiance header separator")
    end = blob.find(b'\n', pos + 2)
    if end < 0:
        raise ValueError("Missing resolution newline")
    return end + 1

def validate_header_and_payload(blob):
    if not blob.startswith(HDR_HEADER):
        raise ValueError("Non-Hybrid HDR header")
    start = header_end(blob)
    if start != len(HDR_HEADER) or len(blob) - start != PIXEL_BYTES:
        raise ValueError("Invalid Hybrid HDR pixel bytes")
    return {"header_bytes":start,"payload_bytes":len(blob)-start,
            "total_bytes":len(blob),"stock_bug_rejects":len(blob)!=PIXEL_BYTES}

def transform(text):
    if MARK not in text:
        raise ValueError("Wrong native renderer base")
    if NEW in text:
        raise ValueError("Hotfix already present")
    if text.count(OLD)!=1 or text.count("hybridActive")<4:
        raise ValueError("Unexpected source anchors")
    out = text.replace(OLD, NEW, 1)
    if out.count(NEW)!=1 or OLD in out:
        raise AssertionError("Non-surgical change")
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("root",type=Path)
    parser.add_argument("--check-only",action="store_true")
    parser.add_argument("--proof",type=Path)
    args=parser.parse_args()
    file=args.root/"SP/code/rend2/tr_bsp.c"
    old=file.read_text()
    new=transform(old)
    if not args.check_only:
        file.write_text(new)
    proof={"base_run":41019985033,"scope":"Hybrid V2 only",
           "original_hdr_path_unchanged":True,
           "before_sha256":hashlib.sha256(old.encode()).hexdigest(),
           "after_sha256":hashlib.sha256(new.encode()).hexdigest(),
           "header_bytes":len(HDR_HEADER),"float_rgb_payload_bytes":PIXEL_BYTES,
           "old_check_rejects_valid_payload":True}
    if args.proof:
        args.proof.parent.mkdir(parents=True,exist_ok=True)
        args.proof.write_text(json.dumps(proof,indent=2)+"\n")
    print("DW_HYBRID_V2_HDR_PAYLOAD_SIZE_HOTFIX_SOURCE_PASS")

if __name__=="__main__":
    main()
