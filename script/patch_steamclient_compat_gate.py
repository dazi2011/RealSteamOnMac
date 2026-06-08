#!/usr/bin/env python3

import argparse
import hashlib
import shutil
import struct
import sys
from pathlib import Path


ARM64_CPU_TYPE = 0x0100000C
LC_UUID = 0x1B
EXPECTED_UUID = bytes.fromhex("B2950628803A3EFD99EF3AD6B7B65D1C")
EXPECTED_SOURCE_SHA256 = (
    "f9c1df763087900a66020635f22559f49533edd3290f0880eb13f46d2dfe2ed5"
)
COMPAT_GATE_OFFSET = 0x00A012D0
EXPECTED_BYTES = bytes.fromhex("ffc301d1f44f05a9")
PATCHED_BYTES = bytes.fromhex("20008052c0035fd6")


class PatchError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def arm64_slice(data: bytes) -> tuple[int, int]:
    if len(data) < 8:
        raise PatchError("file is too small to be a Mach-O binary")

    magic, count = struct.unpack_from(">II", data, 0)
    if magic != 0xCAFEBABE:
        raise PatchError("expected a universal Mach-O binary")

    cursor = 8
    for _ in range(count):
        if cursor + 20 > len(data):
            raise PatchError("truncated universal Mach-O header")
        cpu_type, _subtype, offset, size, _alignment = struct.unpack_from(
            ">iiIII", data, cursor
        )
        if cpu_type == ARM64_CPU_TYPE:
            if offset + size > len(data):
                raise PatchError("ARM64 slice extends past the end of the file")
            return offset, size
        cursor += 20
    raise PatchError("ARM64 slice not found")


def macho_uuid(data: bytes, slice_offset: int, slice_size: int) -> bytes:
    if slice_size < 32:
        raise PatchError("ARM64 slice is too small")
    magic = struct.unpack_from("<I", data, slice_offset)[0]
    if magic != 0xFEEDFACF:
        raise PatchError("ARM64 slice is not a 64-bit little-endian Mach-O")

    command_count = struct.unpack_from("<I", data, slice_offset + 16)[0]
    cursor = slice_offset + 32
    end = slice_offset + slice_size
    for _ in range(command_count):
        if cursor + 8 > end:
            raise PatchError("truncated Mach-O load commands")
        command, command_size = struct.unpack_from("<II", data, cursor)
        if command_size < 8 or cursor + command_size > end:
            raise PatchError("invalid Mach-O load command size")
        if command == LC_UUID:
            if command_size < 24:
                raise PatchError("invalid LC_UUID command")
            return data[cursor + 8 : cursor + 24]
        cursor += command_size
    raise PatchError("LC_UUID command not found")


def inspect(path: Path) -> tuple[bytearray, int]:
    data = bytearray(path.read_bytes())
    slice_offset, slice_size = arm64_slice(data)
    uuid = macho_uuid(data, slice_offset, slice_size)
    if uuid != EXPECTED_UUID:
        raise PatchError(
            f"unexpected ARM64 UUID: {uuid.hex().upper()} "
            f"(expected {EXPECTED_UUID.hex().upper()})"
        )
    patch_offset = slice_offset + COMPAT_GATE_OFFSET
    if patch_offset + len(EXPECTED_BYTES) > slice_offset + slice_size:
        raise PatchError("compatibility gate offset is outside the ARM64 slice")
    return data, patch_offset


def patch(source: Path, output: Path) -> None:
    if output.exists():
        raise PatchError(f"output already exists: {output}")
    source_hash = sha256(source)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise PatchError(
            f"unexpected source SHA-256: {source_hash} "
            f"(expected {EXPECTED_SOURCE_SHA256})"
        )

    data, patch_offset = inspect(source)
    current = bytes(data[patch_offset : patch_offset + len(EXPECTED_BYTES)])
    if current != EXPECTED_BYTES:
        raise PatchError(
            f"unexpected gate bytes: {current.hex()} "
            f"(expected {EXPECTED_BYTES.hex()})"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    with output.open("r+b") as stream:
        stream.seek(patch_offset)
        stream.write(PATCHED_BYTES)

    verify_patched(output)
    print(f"source_sha256={source_hash}")
    print(f"arm64_uuid={EXPECTED_UUID.hex().upper()}")
    print(f"arm64_gate_offset=0x{COMPAT_GATE_OFFSET:08X}")
    print(f"output={output}")


def verify_patched(path: Path) -> None:
    data, patch_offset = inspect(path)
    current = bytes(data[patch_offset : patch_offset + len(PATCHED_BYTES)])
    if current != PATCHED_BYTES:
        raise PatchError(
            f"patched gate bytes do not match: {current.hex()} "
            f"(expected {PATCHED_BYTES.hex()})"
        )
    print(f"verified_patched={path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-patched", type=Path)
    args = parser.parse_args()

    try:
        if args.verify_patched is not None:
            if args.input is not None or args.output is not None:
                raise PatchError("--verify-patched cannot be combined with patch options")
            verify_patched(args.verify_patched)
        else:
            if args.input is None or args.output is None:
                raise PatchError("--input and --output are required")
            patch(args.input, args.output)
    except PatchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
