# Integration-test binaries

Cargo builds every file directly under a crate's `tests/` as its own test
binary, and each one statically links the whole engine. In a local debug
build that is roughly 450 MB and several seconds of linking per file. So
`relate/relate` and `surfaces/relate-cli` keep their shareable test files
in a single binary: `tests/integration/`, built from
`tests/integration/main.rs`.

## Running one file's tests

The file name is now a module path inside the `integration` binary:

```bash
cargo test -p relate --test integration clone::
```

```bash
cargo test -p relate-cli --test integration e2e_bundles::test_one_shot_query_runs_in_every_bundle -- --exact
```

## Adding a test file

Put it in `tests/integration/` and add a `mod <name>;` line to
`tests/integration/main.rs`. The shared helpers are reached as
`use crate::common;` (relate) or `use crate::support;` (relate-cli), not
re-declared with `mod`. The `every_file_is_declared` test fails if a file
in the directory has no `mod` line, because an undeclared file would
otherwise never compile or run.

Put it directly in `tests/` instead, as a binary of its own, when sharing
a process with the other tests would change what it tests. Under plain
`cargo test` a binary's tests run as threads of one process:

- it mutates the process environment: `set_var`, the `RELATE_PREVIEW`
  opt-in fixtures (`set_preview_once`, `preview_ontology`), or the
  pattern-engine switch. `Database::open` reads these variables, so a
  sibling test would observe the change.
- it samples process-wide state, such as RSS.
- it re-executes its own test binary as a child.
- it uses the test crate root as its own (`crate::` paths, `#[path]`
  submodules), as `constraint_validation.rs` does.
- it must also compile on its own outside this tree. `golden_stores.rs`
  is copied into old release checkouts (`testdata/stores/README.md`).

`scripts/merge-test-binaries.py <crate-dir>` applies these rules with a
conservative text scan and moves the files that pass. It is idempotent, so
re-running it after new files land directly in `tests/` folds in the
shareable ones.
