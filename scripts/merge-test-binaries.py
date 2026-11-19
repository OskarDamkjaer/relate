#!/usr/bin/env python3
"""Fold a crate's integration-test files into one test binary.

Every file directly under `<crate>/tests/` is its own Cargo test target:
its own rustc invocation and its own static link of the whole engine. For
`relate/relate` that is ~145 links of a ~450 MB debug binary. This script
moves the files that can share a process into `<crate>/tests/<binary>/`,
which Cargo builds as one target from `<binary>/main.rs`.

A file stays a binary of its own when sharing a process would change
what it tests:

- it mutates the process environment (`set_var`, the `RELATE_PREVIEW`
  opt-in fixtures, the pattern-engine switch) — `Database::open` reads it,
  so a sibling test would observe the mutation;
- it measures process-wide state (RSS sampling);
- it re-executes its own test binary as a child;
- it treats the test crate root as its own (`crate::` paths).

The check is a conservative text scan; `--keep` adds names by hand.
Files the scan keeps separate are reported. The move is idempotent: files
already under `<binary>/` are left alone and `main.rs` is regenerated.

Usage: scripts/merge-test-binaries.py <crate-dir> [--binary NAME] [--keep a,b] [--dry-run]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# A file is kept separate when its text matches any of these.
ISOLATION_PATTERNS = {
    "mutates the process environment": re.compile(
        r"\bset_var\b|\bremove_var\b|\bset_preview_once\b|\bpreview_ontology\b"
        r"|\bopen_with_engine\b|\bfor_each_engine\b|\bEnvRestore\b"
    ),
    "samples process-wide memory": re.compile(r"\brss\b|\bRSS\b|global_allocator"),
    "re-executes its own binary": re.compile(r"current_exe\(\)"),
    "owns the crate root": re.compile(r"\bcrate::|#\[path\s*="),
}



def shared_module_pattern(name: str):
    """The per-file declaration of a shared helper module (`tests/<name>/mod.rs`)."""
    return re.compile(rf'^(#\[path = "{name}/mod.rs"\]\n)?mod {name};\n', re.M)


# A file-relative include path: one directory deeper after the move.
RELATIVE_INCLUDE = re.compile(r'(include_(?:str|bytes)!\(\s*")(?!/)')


def isolation_reason(text: str):
    for reason, pattern in ISOLATION_PATTERNS.items():
        if pattern.search(text):
            return reason
    return None


def render_main(binary: str, modules: list[str], shared: list[str]) -> str:
    lines = [
        f"//! The `{binary}` integration-test binary: every test file that can",
        "//! share a process with its siblings, compiled and linked once instead",
        "//! of once per file (scripts/merge-test-binaries.py). A file that",
        "//! mutates the process environment, samples process-wide memory, or",
        "//! re-executes its own binary stays a binary of its own directly under",
        "//! `tests/`. Add a new shareable test file here as a `mod` line; the",
        "//! `every_file_is_declared` test fails on a file left out.",
        "",
    ]
    for name in shared:
        lines += [f'#[path = "../{name}/mod.rs"]', f"mod {name};"]
    if shared:
        lines.append("")
    for name in modules:
        if name != name.lower():
            lines.append("#[allow(non_snake_case)]")
        lines.append(f"mod {name};")
    lines += [
        "",
        "/// A file under this directory that no `mod` line declares would",
        "/// silently never compile or run.",
        "#[test]",
        "fn every_file_is_declared() {",
        '    let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))',
        f'        .join("tests/{binary}");',
        '    let main = include_str!("main.rs");',
        "    for entry in std::fs::read_dir(&dir).expect(\"test directory is readable\") {",
        "        let path = entry.expect(\"directory entry is readable\").path();",
        '        if path.extension().is_some_and(|ext| ext == "rs") {',
        "            let stem = path.file_stem().unwrap().to_str().unwrap();",
        '            if stem != "main" {',
        "                assert!(",
        '                    main.contains(&format!("\\nmod {stem};\\n")),',
        f'                    "tests/{binary}/{{stem}}.rs is not declared in main.rs"',
        "                );",
        "            }",
        "        }",
        "    }",
        "}",
        "",
    ]
    return "\n".join(lines)


# Historical records keep the path they were written with.
FROZEN_PREFIXES = ("docs/adr/", "CHANGELOG")


def rewrite_references(crate_dir: Path, binary: str, stems: list[str]) -> None:
    """Point every tracked mention of a moved file at its new path."""
    if not stems:
        return
    tests = crate_dir.as_posix().rstrip("/") + "/tests/"
    old = re.compile(re.escape(tests) + r"(" + "|".join(map(re.escape, stems)) + r")\.rs\b")
    listed = subprocess.run(
        ["git", "grep", "-l", "-E", re.escape(tests) + r"[A-Za-z0-9_]+\.rs"],
        capture_output=True, text=True,
    ).stdout.split()
    for name in listed:
        if name.startswith(FROZEN_PREFIXES):
            continue
        path = Path(name)
        text = path.read_text()
        new = old.sub(lambda m: f"{tests}{binary}/{m.group(1)}.rs", text)
        if new != text:
            path.write_text(new)
            print(f"rewrote references in {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("crate_dir", type=Path)
    parser.add_argument("--binary", default="integration")
    parser.add_argument("--keep", default="", help="comma-separated file stems to keep separate")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tests = args.crate_dir / "tests"
    target = tests / args.binary
    keep = {name for name in args.keep.split(",") if name}
    moved, kept = [], []
    for path in sorted(tests.glob("*.rs")):
        stem = path.stem
        reason = "--keep" if stem in keep else isolation_reason(path.read_text())
        if reason:
            kept.append((stem, reason))
        else:
            moved.append(path)

    shared = sorted(d.name for d in tests.iterdir() if (d / "mod.rs").is_file())
    existing = sorted(p.stem for p in target.glob("*.rs") if p.stem != "main") if target.is_dir() else []
    for stem, reason in kept:
        print(f"keep  {stem}: {reason}")
    print(f"merge {len(moved)} new + {len(existing)} existing files into tests/{args.binary}/; "
          f"{len(kept)} stay separate")
    if args.dry_run:
        return 0

    target.mkdir(exist_ok=True)
    for path in moved:
        text = RELATIVE_INCLUDE.sub(r"\g<1>../", path.read_text())
        for name in shared:
            text = shared_module_pattern(name).sub(f"use crate::{name};\n", text, count=1)
        dest = target / path.name
        subprocess.run(["git", "mv", str(path), str(dest)], check=True)
        dest.write_text(text)
    modules = sorted({p.stem for p in moved} | set(existing))
    (target / "main.rs").write_text(
        render_main(args.binary, modules, shared)
    )
    rewrite_references(args.crate_dir, args.binary, [p.stem for p in moved])
    # The include-path rewrite can push a line past rustfmt's width.
    subprocess.run(["rustfmt", "--edition", "2021", *map(str, sorted(target.glob("*.rs")))], check=True)
    subprocess.run(["git", "add", str(target)], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
