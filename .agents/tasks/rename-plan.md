# Project Rename Plan: "contracts" → "OverStand"

## Overview

This plan renames the entire project from "contracts" to "OverStand" while preserving internal package and contract names that are product identifiers.

**Key Principle:** The top-level project/workspace is called "contracts" in three contexts:
1. **Directory name:** `contracts/` (the workspace root)
2. **Workspace logical name:** References in documentation and configuration that treat "contracts" as the project name
3. **Path references:** Import paths, workspace members, and relative paths that will break if the directory is renamed

The **sub-packages** (`alert-registry`, `watcher-registry`) are product names and must NOT be changed.

---

## Changes Required

### Category A: File Content Changes (before directory rename)

These files reference "contracts" as a project/workspace name or contain paths that reference the "contracts" directory. Update them FIRST so edits still work.

#### A1. Workspace Configuration Files

- [ ] **Root Cargo.toml** — Workspace members path
  - File: `Cargo.toml`
  - Change: Update `[workspace] members` paths from `"contracts/..."` to `"OverStand/..."` (if directory becomes `OverStand/`) OR keep relative paths as-is if renaming happens after content updates
  - Reasoning: The Cargo.toml uses paths like `"contracts/alert-registry"`, `"contracts/watcher-registry"`. After the directory rename, these paths will be stale. It's safer to update file contents first while the directory still exists with the old name, then rename the directory last.
  - Verify: `cargo metadata --format-version 1 | jq '.workspace_members'` confirms members are found

- [ ] **Sub-package Cargo.toml files** — repository and homepage URLs
  - Files:
    - `contracts/alert-registry/Cargo.toml`
    - `contracts/watcher-registry/Cargo.toml`
    - `contracts/test-utils/Cargo.toml`
    - `contracts/integration-tests/Cargo.toml`
    - `contracts/watcher-registry/fuzz/Cargo.toml`
    - `contracts/alert-registry/fuzz/Cargo.toml`
  - Change: `repository = "https://github.com/QingQosh/contracts"` → `repository = "https://github.com/QingQosh/OverStand"` and `homepage = "https://github.com/QingQosh/contracts"` → `homepage = "https://github.com/QingQosh/OverStand"`
  - Reasoning: These URLs point to the GitHub repository. After renaming, the repository URL changes. Update now to ensure consistency.
  - Verify: `grep -n "QingQosh/contracts" contracts/**/*.toml` returns no matches

- [ ] **Cargo Mutants Configuration** (`.cargo/mutants.toml`)
  - File: `.cargo/mutants.toml`
  - Change: Update comment from "TxWatch contracts workspace" to "TxWatch OverStand workspace". Update path references in `examine_globs` and `exclude_globs` if they reference the "contracts/" directory prefix (currently they do: `"contracts/alert-registry/src/lib.rs"` etc.)
  - Reasoning: Glob patterns use relative paths; after directory rename, these patterns will still work if kept as-is (they're relative to workspace root). However, the comment should reflect the new project name for clarity.
  - Verify: `cargo mutants --version` and dry-run to ensure patterns still match

#### A2. README and Documentation Files

- [ ] **Root README.md**
  - File: `README.md`
  - Changes:
    - Update title from `# tx-watch-contracts ....` to `# OverStand` (or similar)
    - Update codecov badge URL: `https://codecov.io/gh/QingQosh/contracts/` → `https://codecov.io/gh/QingQosh/OverStand/`
    - Update any references to "contracts" as a project name to "OverStand"
    - Keep links like `[Alert Registry](contracts/alert-registry/src/lib.rs)` as-is (relative paths, still work)
    - Keep references to the "contracts" in smart contract context ("Soroban smart contracts") unchanged
  - Reasoning: The README is user-facing; the project name should reflect "OverStand". Codecov must point to the new repo URL. Relative links to subdirectories remain unchanged.
  - Verify: `cargo doc --no-deps 2>&1 | head -20` (doc build should succeed)

- [ ] **CONTRIBUTING.md**
  - File: `CONTRIBUTING.md`
  - Changes:
    - Update GitHub URL references from `QingQosh/contracts` to `QingQosh/OverStand` (e.g., in sections about branch protection, deployment, etc.)
    - Update relative doc links (e.g., `docs/testing.md` stays the same; `[sister repos](...)` links update to new org URLs if they reference the contracts repo)
  - Reasoning: Contributes must refer to the correct GitHub repository.
  - Verify: `grep -n "github.com/QingQosh/contracts" CONTRIBUTING.md` returns no matches

- [ ] **DEPLOYMENTS.md**
  - File: `DEPLOYMENTS.md`
  - Changes:
    - Update script path reference: `./scripts/deploy.sh` → stays the same (scripts directory name doesn't change)
    - Update file references: `DEPLOYMENTS.md` → stays the same
    - No GitHub repo URL references in this file that need updating
  - Reasoning: Script paths are relative and don't include the workspace directory name. No URL changes needed.
  - Verify: File content remains readable; no broken references

- [ ] **CHANGELOG.md**
  - File: `CHANGELOG.md`
  - Changes:
    - Update GitHub URLs in comparison links from `compare/vX.Y.Z...HEAD` → stays the same (relative links)
    - Update full repository URLs if present: `https://github.com/QingQosh/contracts` → `https://github.com/QingQosh/OverStand`
  - Reasoning: CHANGELOG should reflect the correct GitHub repository URL.
  - Verify: `grep -n "QingQosh/contracts" CHANGELOG.md` returns no matches (or only expected matches like in version diffs)

- [ ] **Security Documentation (SECURITY.md)**
  - File: `SECURITY.md`
  - Changes:
    - Update GitHub security advisory URL: `https://github.com/QingQosh/contracts/security/advisories/new` → `https://github.com/QingQosh/OverStand/security/advisories/new`
    - Update API endpoint examples: `repos/QingQosh/contracts/` → `repos/QingQosh/OverStand/`
  - Reasoning: Security reports must go to the correct repository.
  - Verify: `grep -n "QingQosh/contracts" SECURITY.md` returns no matches

- [ ] **Contract READMEs**
  - Files:
    - `contracts/alert-registry/README.md`
    - `contracts/watcher-registry/README.md`
  - Changes:
    - Update GitHub URLs from `QingQosh/contracts` to `QingQosh/OverStand`
    - Keep internal cross-references to other contracts the same (e.g., links within the repo)
  - Reasoning: Contract documentation should reference the correct repository.
  - Verify: `grep -n "QingQosh/contracts" contracts/**/*README.md` returns no matches

- [ ] **TypeScript Bindings READMEs and Metadata**
  - Files:
    - `bindings/alert-registry/README.md`
    - `bindings/alert-registry/CHANGELOG.md`
    - `bindings/watcher-registry/README.md`
    - `bindings/watcher-registry/CHANGELOG.md`
  - Changes:
    - Update GitHub URLs: `https://github.com/Tx-wat/stellar-txwatch-contracts` → `https://github.com/QingQosh/OverStand`
    - Update GitHub compare links in CHANGELOG entries
  - Reasoning: Bindings documentation must reference the correct repository.
  - Verify: `grep -n "QingQosh/contracts\|Tx-wat/" bindings/**/*.md` returns no matches for "contracts", "Tx-wat" returns only if they reference sister repos

- [ ] **docs/ markdown files**
  - Files: All `.md` files in `docs/`
  - Changes:
    - Search for `contracts/` path references (e.g., `[ref](../contracts/alert-registry/src/lib.rs)`) and verify they still work after rename. Most should, as they're relative.
    - Update GitHub repo URLs: `QingQosh/contracts` → `QingQosh/OverStand`
  - Reasoning: Documentation should reflect the new repository URL.
  - Verify: Run `./scripts/check-links.sh` (if it exists) or manually verify no broken links

#### A3. Configuration Files (Tool Configs)

- [ ] **.lychee.toml** (Link checker config)
  - File: `.lychee.toml`
  - Change: If it excludes patterns or includes specific GitHub URLs, update them if they reference `QingQosh/contracts` → `QingQosh/OverStand`
  - Reasoning: Link checker should not skip the new repository URLs.
  - Verify: `lychee --config .lychee.toml .` or similar, ensure no new errors

- [ ] **_typos.toml** (Spell/typo checker)
  - File: `_typos.toml`
  - Change: Check if it has any allowlist entries or ignore patterns for "contracts"; if the project name is mentioned, update if necessary
  - Reasoning: Typo checker should recognize the new project name if configured.
  - Verify: `typos .` should pass

- [ ] **rust-toolchain.toml**
  - File: `rust-toolchain.toml`
  - Change: No changes needed (this file specifies Rust version, not project name)
  - Verify: `rustc --version` matches the pinned version

#### A4. TypeScript Package Metadata

- [ ] **bindings/alert-registry/package.json**
  - File: `bindings/alert-registry/package.json`
  - Changes:
    - `"repository": { "url": "https://github.com/QingQosh/contracts.git", ... }` → `"url": "https://github.com/QingQosh/OverStand.git"`
    - `"homepage": "https://github.com/QingQosh/contracts#readme"` → `"https://github.com/QingQosh/OverStand#readme"`
    - `"bugs": { "url": "https://github.com/QingQosh/contracts/issues" }` → `"https://github.com/QingQosh/OverStand/issues"`
  - Reasoning: npm package metadata should point to the correct repository.
  - Verify: `npm view @QingQosh/alert-registry-bindings` (once published) or `jq .repository package.json`

- [ ] **bindings/watcher-registry/package.json**
  - File: `bindings/watcher-registry/package.json`
  - Changes: Same as above for the watcher registry bindings
  - Verify: `jq .repository package.json`

---

### Category B: Directory Rename (final step)

Once all file content changes are complete, rename the workspace directory.

- [ ] **Rename directory**
  - Action: Rename `contracts/` to `OverStand/`
  - Command: `mv "c:\Users\LENOVO PC\Desktop\New folder (5)\contracts" "c:\Users\LENOVO PC\Desktop\New folder (5)\OverStand"`
  - Reasoning: The directory name is the final change because it's the most disruptive; doing it last ensures all file edits still work. The Cargo.toml paths now become `"OverStand/alert-registry"` relative to their new location.
  - Verify: `ls "c:\Users\LENOVO PC\Desktop\New folder (5)\" | grep -E "OverStand|contracts"` confirms old name is gone and new name exists

---

### Category C: Verification After All Changes

- [ ] **Verify workspace compiles**
  - Command: `cd "c:\Users\LENOVO PC\Desktop\New folder (5)\OverStand" && cargo build --release --target wasm32-unknown-unknown --all 2>&1 | tail -20`
  - Expected: Build succeeds with no errors
  - Reasoning: Ensures Cargo.toml paths and configuration are correct after rename

- [ ] **Verify all tests pass**
  - Command: `cd "c:\Users\LENOVO PC\Desktop\New folder (5)\OverStand" && cargo test --workspace --locked 2>&1 | tail -30`
  - Expected: All tests pass
  - Reasoning: Ensures no build or path-related issues broke the codebase

- [ ] **Verify documentation links**
  - Command: `grep -r "github.com/QingQosh/contracts" "c:\Users\LENOVO PC\Desktop\New folder (5)\OverStand"` (excluding `.git/` if present)
  - Expected: No matches (all updated to "OverStand")
  - Reasoning: Ensures all GitHub references are updated

- [ ] **Verify no broken relative paths**
  - Command: Spot-check key files for relative imports, e.g., `grep -n "contracts/" "c:\Users\LENOVO PC\Desktop\New folder (5)\OverStand\Cargo.toml"`
  - Expected: Paths like `"OverStand/alert-registry"` now (if workspace was updated) or relative paths still work
  - Reasoning: Ensures import paths are still valid

---

## Files Summary

### Files to Modify (Content Only)

1. `Cargo.toml` — workspace members paths
2. `contracts/alert-registry/Cargo.toml` — repository/homepage URLs
3. `contracts/watcher-registry/Cargo.toml` — repository/homepage URLs
4. `contracts/test-utils/Cargo.toml` — repository/homepage URLs
5. `contracts/integration-tests/Cargo.toml` — repository/homepage URLs
6. `contracts/watcher-registry/fuzz/Cargo.toml` — repository/homepage URLs
7. `contracts/alert-registry/fuzz/Cargo.toml` — repository/homepage URLs
8. `.cargo/mutants.toml` — comment and optionally paths (if needed)
9. `README.md` — project title, codecov badge, project name references
10. `CONTRIBUTING.md` — GitHub URLs
11. `DEPLOYMENTS.md` — verify no broken references
12. `CHANGELOG.md` — GitHub URLs
13. `SECURITY.md` — GitHub security advisory URL, API endpoints
14. `contracts/alert-registry/README.md` — GitHub URLs
15. `contracts/watcher-registry/README.md` — GitHub URLs
16. `bindings/alert-registry/README.md` — GitHub URLs
17. `bindings/alert-registry/CHANGELOG.md` — GitHub URLs
18. `bindings/watcher-registry/README.md` — GitHub URLs
19. `bindings/watcher-registry/CHANGELOG.md` — GitHub URLs
20. All files in `docs/` directory with GitHub URLs
21. `bindings/alert-registry/package.json` — repository, homepage, bugs URLs
22. `bindings/watcher-registry/package.json` — repository, homepage, bugs URLs

### Files NOT to Change

- **Sub-package names:** `alert-registry`, `watcher-registry`, `test-utils`, `integration-tests` remain unchanged (these are product identifiers, not the workspace name)
- **npm package names:** `@QingQosh/alert-registry-bindings`, `@QingQosh/watcher-registry-bindings` remain unchanged (these are published package identities)
- **rust-toolchain.toml** — no changes
- **Binary/library names in Cargo.toml** `[package] name = "..."` fields in sub-crates remain unchanged

### Directory Rename

- Rename: `contracts/` → `OverStand/` (final step, after all content updates)

---

## Execution Order

1. **Update all file contents** (Cargo.toml, README, docs, package.json, etc.) while the directory is still named `contracts/`
2. **Verify builds and tests** to ensure content changes are correct
3. **Rename directory** from `contracts/` to `OverStand/`
4. **Final verification** (build, tests, no broken references)

This order ensures that file edits don't fail due to missing paths, and that the directory rename happens only once all internal references are fixed.

---

## Notes for Implementer

- **GitHub references:** The project is currently at `https://github.com/QingQosh/OverStand`. After the directory is renamed locally, assuming the GitHub repository is ALSO renamed to `OverStand`, all these URLs must be updated to `https://github.com/QingQosh/OverStand`. If the GitHub repository is NOT being renamed, update URLs to reflect that.
- **Sister repositories:** The CONTRIBUTING.md and other docs reference sister repos like `stellar-txwatch-core` and `stellar-txwatch-web`. These are separate repositories and should not be changed in this task; only update references if they incorrectly point to the `contracts` repo.
- **Bindings publication:** Once changes are merged and released, the npm packages `@QingQosh/alert-registry-bindings` and `@QingQosh/watcher-registry-bindings` will reference the new repository URL. The package names themselves stay the same.
