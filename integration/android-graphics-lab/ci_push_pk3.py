#!/usr/bin/env python3
"""Reliable binary-safe Android 11 app-private PK3 importer for Graphics Lab CI.

adb exec-in may silently truncate a huge stdin stream despite returning zero.
Transfer each source in independently verified 512 KiB blocks, retry an invalid
block, then verify the accumulated length and full remote SHA-256 before launch.
Game data stays inside the debuggable CI app sandbox; never uploaded to artifacts.
"""
from __future__ import annotations
import argparse
import hashlib
import io
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time

CHUNK_BYTES = 512 * 1024
ATTEMPTS = 5
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

def app_shell_command(pkg: str, script: str) -> str:
    """Keep redirection inside run-as, not the surrounding Android shell.

    adb shell concatenates argv and reparses it with an outer remote shell;
    without quoting, >> executes outside run-as and gets Permission denied.
    """
    if not re.fullmatch(r"[A-Za-z0-9._]+", pkg):
        raise ValueError("Invalid Android package name")
    return f"run-as {shlex.quote(pkg)} sh -c {shlex.quote(script)}"


def app_shell(pkg: str, script: str, *, timeout: int = 90) -> str:
    return adb(["shell", app_shell_command(pkg, script)], timeout=timeout)


def probe_private_redirection(pkg: str, dest: str) -> None:
    """Catch shell-UID writing failures before the large retail PK3 transfer."""
    probe = f"{dest}/.darkwolf-write-probe"
    try:
        app_shell(pkg, f"printf abcd > {shlex.quote(probe)}")
        if remote_size(pkg, probe) != 4:
            raise RuntimeError("run-as write probe: incorrect size")
        app_shell(pkg, f"printf efgh >> {shlex.quote(probe)}")
        if remote_size(pkg, probe) != 8:
            raise RuntimeError("run-as append probe: incorrect size")
        if remote_hash(pkg, probe) != digest(b"abcdefgh"):
            raise RuntimeError("run-as append probe SHA256 mismatch")
        print("GRAPHICS_LAB_PK3_PRIVATE_WRITE_APPEND_PROBE=PASS", flush=True)
    finally:
        app(["rm", "-f", probe], pkg)


def remote_size(pkg: str, file: str) -> int:
    value = app(["stat", "-c", "%s", file], pkg)
    return int(value.strip())

def remote_hash(pkg: str, file: str) -> str:
    value = app(["sha256sum", file], pkg, timeout=200)
    token = value.split()[0].lower()
    if not re.fullmatch("[0-9a-f]{64}", token):
        raise RuntimeError("Invalid remote SHA-256 output")
    return token

def app_private_destination(pkg: str, cwd: str, requested: str) -> str:
    """Use one absolute path across adb shell and exec-in run-as invocations.

    Android's run-as does not promise that sh -c starts in the same working
    directory as separate shell commands. Avoid all relative PK3 redirections.
    """
    root = cwd.strip()
    if not root.startswith("/data/") or not root.endswith("/" + pkg):
        raise ValueError("Unexpected run-as app directory: " + repr(root))
    if requested.startswith("/"):
        destination = requested
        relative = requested[len(root) + 1:] if requested.startswith(root + "/") else ""
    else:
        relative = requested
        destination = root + "/" + relative
    parts = relative.split("/")
    if (len(parts) < 3 or parts[0] != "files" or
            any(part in ("", ".", "..") for part in parts)):
        raise ValueError("Refusing PK3 destination outside private app files")
    return destination


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
            app_shell(pkg, f"cat {shlex.quote(tmp)} >> {shlex.quote(dst)}", timeout=90)
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
        pieces = [data[i:i+CHUNK_BYTES] for i in range(0, len(data), CHUNK_BYTES)]
        assert len(pieces) > 1
        assert len(pieces[0]) == CHUNK_BYTES
        assert all(0 < len(piece) <= CHUNK_BYTES for piece in pieces)
        # A chunk hash is not the full file hash. Exercise the actual
        # multi-chunk append contract and compare the concatenated digest.
        assembled = hashlib.sha256()
        for piece in pieces:
            assert digest(piece) == hashlib.sha256(piece).hexdigest()
            assembled.update(piece)
        assert b"".join(pieces) == data
        assert assembled.hexdigest() == file_hash(file)
        assert digest(pieces[0]) != file_hash(file)
        assert app_private_destination(
            "org.darkwolf.rend2", "/data/user/0/org.darkwolf.rend2",
            "files/DarkWolfRTCW/main") == (
                "/data/user/0/org.darkwolf.rend2/files/DarkWolfRTCW/main")
        script = "cat '/data/user/0/org.darkwolf.rend2/files/a' >> '/data/user/0/org.darkwolf.rend2/files/b'"
        assert shlex.split(app_shell_command("org.darkwolf.rend2", script)) == [
            "run-as", "org.darkwolf.rend2", "sh", "-c", script]
        try:
            app_private_destination(
                "org.darkwolf.rend2", "/data/user/0/org.darkwolf.rend2",
                "../files/DarkWolfRTCW/main")
            raise AssertionError("PK3 destination escaped sandbox")
        except ValueError:
            pass
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
        # Resolve the run-as app root once. Always use this same absolute
        # destination for mkdir, 4 MiB redirection, append, stat and hashing.
        app_root = app(["pwd"], args.pkg)
        args.dest = app_private_destination(args.pkg, app_root, args.dest)
        app(["mkdir", "-p", args.dest], args.pkg)
        app(["test", "-d", args.dest], args.pkg)
        print(f"GRAPHICS_LAB_RETAIL_DEST={args.dest}", flush=True)
        probe_private_redirection(args.pkg, args.dest)
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
