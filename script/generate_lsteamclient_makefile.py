#!/usr/bin/python3

import argparse
import re
from pathlib import Path


MARKER = "### Dependencies (everything below this line is auto-generated; DO NOT EDIT!!)"


def replace_assignment(lines, name, value, allow_insert=False):
    pattern = re.compile(rf"^{re.escape(name)}\s*=")
    for index, line in enumerate(lines):
        if not pattern.match(line):
            continue
        end = index + 1
        while lines[end - 1].rstrip().endswith("\\"):
            end += 1
        lines[index:end] = [f"{name} = {value}\n"]
        return
    if allow_insert:
        lines.append(f"{name} = {value}\n")
        return
    raise RuntimeError(f"missing Makefile variable: {name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wine-makefile", required=True)
    parser.add_argument("--wine-source", required=True)
    parser.add_argument("--wine-build", required=True)
    parser.add_argument("--lsteamclient-source", required=True)
    parser.add_argument("--ntdll", required=True)
    parser.add_argument("--prelude", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    wine_source = Path(args.wine_source).resolve()
    wine_build = Path(args.wine_build).resolve()
    lsteamclient_source = Path(args.lsteamclient_source).resolve()
    prelude = Path(args.prelude).resolve()
    prefix = Path(args.prefix).resolve()
    # Keep the no-space symlink path. Wine's generated Makefile does not quote
    # UNIX_LIBS entries, so resolving it back into Application Support breaks
    # the final link command.
    ntdll = Path(args.ntdll).absolute()

    source = Path(args.wine_makefile).read_text(encoding="utf-8")
    if MARKER not in source:
        raise RuntimeError("Wine Makefile dependency marker is missing")
    header = source.split(MARKER, 1)[0]
    lines = header.splitlines(keepends=True)

    includes = f"-I{wine_build / 'include'} -I{wine_source / 'include'}"
    replacements = {
        "prefix": str(prefix),
        "libdir": str(prefix / "lib"),
        "srcdir": str(wine_source),
        "objdir": str(wine_build),
        "CFLAGS": f"-arch x86_64 {includes} -O2 -g",
        "LDFLAGS": "",
        "CPPFLAGS": includes,
        "CXXFLAGS": (
            f"-arch x86_64 -DNOMINMAX -include {prelude} "
            f"{includes} -std=c++17 -O2 -g"
        ),
        "x86_64_CXX": "x86_64-w64-mingw32-g++",
        "x86_64_CFLAGS": f"{includes} -O2 -g",
        "x86_64_CXXFLAGS": f"{includes} -std=c++17 -O2 -g",
        "x86_64_LDFLAGS": "",
        "toolsdir": str(wine_build),
        "PE_ARCHS": "x86_64",
        "TOP_INSTALL_LIB": "dlls/src-lsteamclient",
        "SUBDIRS": str(lsteamclient_source),
    }
    for name, value in replacements.items():
        replace_assignment(
            lines,
            name,
            value,
            allow_insert=name in {"objdir", "x86_64_CXX"},
        )

    output = Path(args.output)
    output.write_text(
        f"UNIX_LIBS = {ntdll}\n"
        + "".join(lines)
        + MARKER
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
