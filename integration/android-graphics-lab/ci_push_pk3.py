#!/usr/bin/env python3
"""Reliable binary-safe Android 11 app-private PK3 importer for Graphics Lab CI.

adb exec-in may silently truncate a huge stdin stream despite returning zero.
Transfer each source in independently verified 4 MiB blocks, retry an invalid
block, then verify the accumulated length and full remote SHA-256 before launch.
Game data stays inside the debuggable CI app sandbox; never uploaded to artifacts.
"""
from __future__ import annotations
import argparse
import hashlib
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

CHUNK_BYTES = 4 * 1024 * 1024
ATTEMPTS = 4
VALID_NAME = re.compile(r"[A-Za-z0-9._-]+[.]pk3", re.IGNORECASE)

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(CHUNK_BYTES):
            h.update(block)
    return h.hexdigest()

def manifest_names(path: Path) -> list[str]:
    names = path.read_text().splitlines()
    if len(names) < 2 or not any(x.lower() == "pak0.pk3" for x in names):
        raise ValueError("Expected verified retail manifest with pak0.pk3 and >=2 PK3s")
    if len(names) != len(set(x.lower() for x in names)):
        raise ValueError("Duplicate PK3 names in manifest")
    for name in names:
        if not VALID_NAME.fullmatch(name) or name.startswith("."):
            raise ValueError("Invalid PK3 basename " + repr(name))
    return names

def adb(args: list[str], *, input_bytes: bytes | None = None,
        timeout: int = 90) -> str:
    argv = ["adb", *args]
    try:
        out = subprocess.run(argv, input=input_bytes, capture_output=True,
                             timeout=timeout, check=False)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("ADB command timed out: " + " ".join(argv[:5])) from e
    if out.returncode:
        err = out.stderr.decode("utf-8", errors="replace").strip()[-450:]
        raise RuntimeError(f"ADB exit {out.returncode}: {err}")
    return out.stdout.decode("utf-8", errors="replace").strip().replace("\r", "")

def app(args: list[str], pkg: str, *, timeout: int = 45) -> str:
    return adb(["shell", "run-as", pkg, *args], timeout=timeout)

def remote_size(pkg: str, file: str) -> int:
    value = app(["stat", "-c", "%s", file], pkg)
    return int(value.strip())

def remote_hash(pkg: str, file: str) -> str:
    value = app(["sha256sum", file], pkg, timeout=200)
    token = value.split()[0].lower()
    if not re.fullmatch("[0-9a-f]{64}", token):
        raise RuntimeError("Invalid remote SHA-256 output")
    return token

def upload_block(pkg: str, tmp: str, chunk: bytes, label: str) -> None:
    expected_hash = digest(chunk)
    for attempt in range(1, ATTEMPTS + 1):
        try:
            adb(["exec-in", "run-as", pkg, "sh", "-c",
                 f"cat > '{tmp}'"], input_bytes=chunk, timeout=85)
            actual_size = remote_size(pkg, tmp)
            if actual_size != len(chunk):
                raise RuntimeError(
                    f"short ADB stream: {actual_size}/{len(chunk)}")
            actual_hash = remote_hash(pkg, tmp)
            if actual_hash != expected_hash:
                raise RuntimeError("SHA-256 mismatch for uploaded block")
            return
        except Exception as e:
            print(f"GRAPHICS_LAB_PK3_CHUNK_RETRY={label} "
                  f"attempt={attempt}/{ATTEMPTS} reason={e}",
                  flush=True)
            if attempt >= ATTEMPTS:
                raise RuntimeError(
                    f"Unrecoverable ADB transfer for {label}") from e
            time.sleep(attempt)

def import_file(source: Path, pkg: str, dest: str) -> None:
    dst = f"{dest}/{source.name}"
    tmp = f"{dest}/.darkwolf-upload-part"
    app(["rm", "-f", dst, tmp], pkg)
    accumulated = 0
    blocks = 0
    with source.open("rb") as stream:
        while (chunk := stream.read(CHUNK_BYTES)):
            blocks += 1
            upload_block(pkg, tmp, chunk, f"{source.name}:{blocks}")
            # Only a fully length/hash-verified block can be appended.
            app(["sh", "-c", f"cat '{tmp}' >> '{dst}'"], pkg, timeout=90)
            accumulated += len(chunk)
            actual = remote_size(pkg, dst)
            if actual != accumulated:
                raise RuntimeError(
                    f"Android append mismatch {source.name} block={blocks}: "
                    f"actual={actual} expected={accumulated}")
            if blocks % 12 == 0:
                print(f"GRAPHICS_LAB_PK3_PROGRESS={source.name} "
                      f"blocks={blocks} bytes={actual}", flush=True)
    app(["rm", "-f", tmp], pkg)
    expected_size = source.stat().st_size
    if not expected_size or accumulated != expected_size:
        raise RuntimeError(f"Local PK3 length changed during upload: {source.name}")
    actual_size = remote_size(pkg, dst)
    if actual_size != expected_size:
        raise RuntimeError(f"Final PK3 size mismatch: {source.name}")
    local_sha = file_hash(source)
    remote_sha = remote_hash(pkg, dst)
    if remote_sha != local_sha:
        raise RuntimeError(f"Final PK3 checksum mismatch: {source.name}")
    print("GRAPHICS_LAB_PK3_TRANSFER_VERIFIED="
          f"{source.name} bytes={actual_size} blocks={blocks} sha256={remote_sha}",
          flush=True)

def selftest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        good = d / "pk3-files.txt"
        good.write_text("pak0.pk3\nsp_pak1.pk3\n")
        assert manifest_names(good) == ["pak0.pk3", "sp_pak1.pk3"]
        good.write_text("pak0.pk3\n../bad.pk3\n")
        try:
            manifest_names(good)
            raise AssertionError("path traversal accepted")
        except ValueError:
            pass
        good.write_text("pak0.pk3\npak0.pk3\n")
        try:
            manifest_names(good)
            raise AssertionError("duplicate accepted")
        except ValueError:
            pass
        data = bytes(range(256)) * 16001
        file = d / "fixture.bin"
        file.write_bytes(data)
        pieces = [data[i:i+CHUNK_BYTES] for i in range(0,len(data),CHUNK_BYTES)]
        assert len(pieces) == 1
        assert digest(pieces[0]) == file_hash(file)
        # A truncated ADB stream must not be considered a valid transfer.
        assert digest(data[:-8192]) != digest(data)
        assert len(data[:-8192]) != len(data)
    print("GRAPHICS_LAB_PK3_CHUNK_IMPORT_SELFTEST=PASS")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("retail_main", type=Path)
        parser.add_argument("manifest", type=Path)
        parser.add_argument("out", type=Path)
        parser.add_argument("--pkg", default="org.darkwolf.rend2")
        parser.add_argument("--dest", default="files/DarkWolfRTCW/main")
        args = parser.parse_args()
        names = manifest_names(args.manifest)
        args.out.mkdir(parents=True, exist_ok=True)
        app(["mkdir", "-p", args.dest], args.pkg)
        app(["pwd"], args.pkg)
        done = []
        for name in names:
            f = args.retail_main / name
            if not f.is_file() or f.stat().st_size <= 0:
                raise SystemExit("Private retail PK3 missing: " + name)
            import_file(f, args.pkg, args.dest)
            done.append(name)
        (args.out / "retail-pk3-copied.txt").write_text("\n".join(done) + "\n")
        print(f"GRAPHICS_LAB_RETAIL_PK3_MANIFEST=PASS files={len(done)}",
              flush=True)
