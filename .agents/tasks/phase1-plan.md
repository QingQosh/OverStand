# Implementation Plan: Security Fixes #197 and #198 (AlertRegistry v0.2.1)

## Overview

Two security fixes for AlertRegistry:
- **Fix #197:** Add `require_auth(querier)` to 8 gated read functions (+ `get_alerts_by_ids` and `get_alert_owner`)
- **Fix #198:** Add querier parameter + auth + gating to 2 incremental sync functions
- Version bump from 0.2.0 to 0.2.1

## Key Findings from Code Exploration

### Current State
- All 8 gated read functions already accept a `querier: Address` parameter
- They call `Self::assert_watcher_if_configured(&env, &querier)?;` for optional watcher-gating
- **Critical security gap:** None call `querier.require_auth();` — anyone can pass any address as querier
- Two sync functions (`get_alerts_modified_since`, `get_alerts_modified_since_ledger`) have NO querier parameter and bypass gating entirely
- Current version: 0.2.0 (in both lib.rs and Cargo.toml)

### Functions to Modify

#### Group 1: 8 Gated Reads (Add require_auth as FIRST line, line numbers from lib.rs)

1. **`get_alert(env, querier, config_id)`** — Line 2729
   - Currently: `assert_watcher_if_configured` only
   - Fix: add `querier.require_auth();` before `assert_watcher_if_configured`

2. **`get_alert_active(env, querier, config_id)`** — Line 2747
   - Same pattern

3. **`get_alerts_for_contract(env, querier, target_contract)`** — Line 2506
   - Same pattern

4. **`get_active_alerts_for_contract(env, querier, target_contract)`** — Line 2538
   - Same pattern

5. **`get_alerts_by_owner(env, querier, owner)`** — Line 2567
   - Same pattern

6. **`get_contract_alerts_paginated(env, querier, target_contract, offset, limit)`** — Line 2645
   - Same pattern

7. **`get_alerts_by_owner_paginated(env, querier, owner, offset, limit)`** — Line 2708
   - Same pattern

8. **`get_active_contract_alerts_paged(env, querier, target_contract, offset, limit)`** — Line 2689 (marked `#[must_use]`)
   - Same pattern

#### Group 2: Related Functions Also Affected

9. **`get_alerts_by_ids(env, querier, ids)`** — Line 2629
   - Already gated, needs require_auth

10. **`get_alert_owner(env, querier, config_id)`** — Not in original spec but has same pattern, needs require_auth
    - Calls `assert_watcher_if_configured` on line ~2779

#### Group 3: Sync Functions (Add querier parameter + signature change)

11. **`get_alerts_modified_since(env, since, offset, limit)`** — Line 3034
    - Current: `pub fn get_alerts_modified_since(env: Env, since: u64, offset: u32, limit: u32) -> Vec<AlertConfig>`
    - Has `#[must_use]` attribute
    - Fix: Change to `pub fn get_alerts_modified_since(env: Env, querier: Address, since: u64, offset: u32, limit: u32) -> Result<Vec<AlertConfig>, ContractError>`
    - Add `querier.require_auth();` as first line
    - Add `Self::assert_watcher_if_configured(&env, &querier)?;` after
    - Remove `#[must_use]` (breaking change already evident in Result return)

12. **`get_alerts_modified_since_ledger(env, since_ledger, offset, limit)`** — Line 3078
    - Current: `pub fn get_alerts_modified_since_ledger(env: Env, since_ledger: u32, offset: u32, limit: u32) -> Vec<AlertConfig>`
    - Has `#[must_use]` attribute
    - Same changes as function 11

## Implementation Steps

- [ ] 1. Add `querier.require_auth();` to 9 existing gated read functions
      
      Modify `get_alert`, `get_alert_active`, `get_alert_owner`, `get_alerts_for_contract`, `get_active_alerts_for_contract`, `get_alerts_by_owner`, `get_alerts_by_ids`, `get_contract_alerts_paginated`, and `get_alerts_by_owner_paginated` in lib.rs. Add `querier.require_auth();` as the FIRST line of each function body, before `assert_watcher_if_configured`.
      
      Files: `contracts/alert-registry/src/lib.rs` (lines 2506, 2538, 2567, 2629, 2645, 2708, 2729, 2747, ~2779)
      
      Verify: `cargo test --workspace --locked` passes; check that each modified function still compiles and logic is correct

- [ ] 2. Add `querier.require_auth();` to `get_active_contract_alerts_paged` 
      
      Modify function at line 2689. Add `querier.require_auth();` as first line (after the `#[must_use]` attribute). This function is marked deprecated but still used so it needs the same auth fix.
      
      Files: `contracts/alert-registry/src/lib.rs` (line 2689)
      
      Verify: `cargo test --workspace --locked` passes

- [ ] 3. Update `get_alerts_modified_since` signature and implementation
      
      Change function at line 3034 from `pub fn get_alerts_modified_since(env: Env, since: u64, offset: u32, limit: u32) -> Vec<AlertConfig>` to `pub fn get_alerts_modified_since(env: Env, querier: Address, since: u64, offset: u32, limit: u32) -> Result<Vec<AlertConfig>, ContractError>`. Remove `#[must_use]` attribute. Add `querier.require_auth();` and `Self::assert_watcher_if_configured(&env, &querier)?;` as first two lines of the function body. Wrap the return value in `Ok()`.
      
      Files: `contracts/alert-registry/src/lib.rs` (line 3034)
      
      Verify: Code compiles; function signature matches spec

- [ ] 4. Update `get_alerts_modified_since_ledger` signature and implementation
      
      Change function at line 3078 from `pub fn get_alerts_modified_since_ledger(env: Env, since_ledger: u32, offset: u32, limit: u32) -> Vec<AlertConfig>` to `pub fn get_alerts_modified_since_ledger(env: Env, querier: Address, since_ledger: u32, offset: u32, limit: u32) -> Result<Vec<AlertConfig>, ContractError>`. Remove `#[must_use]` attribute. Add `querier.require_auth();` and `Self::assert_watcher_if_configured(&env, &querier)?;` as first two lines. Wrap return in `Ok()`.
      
      Files: `contracts/alert-registry/src/lib.rs` (line 3078)
      
      Verify: Code compiles; function signature matches spec

- [ ] 5. Update version in contractmeta
      
      Change `contractmeta!(key = "Version", val = "0.2.0")` to `"0.2.1"` at the top of lib.rs.
      
      Files: `contracts/alert-registry/src/lib.rs` (line ~18)
      
      Verify: `grep "0.2.1" contracts/alert-registry/src/lib.rs` returns the contractmeta line

- [ ] 6. Update Cargo.toml version
      
      Change `version = "0.2.0"` to `"0.2.1"` in the `[package]` section.
      
      Files: `contracts/alert-registry/Cargo.toml` (line 3)
      
      Verify: `grep "version = \"0.2.1\"" contracts/alert-registry/Cargo.toml` returns the version line

- [ ] 7. Add tests for unauthenticated querier failures on gated reads (when watcher-gating enabled)
      
      In `contracts/alert-registry/src/tests.rs`, add test functions that:
      - Set up a WatcherRegistry via `set_watcher_registry`
      - Create an authenticated watcher address
      - Create a non-authenticated address
      - Call each of the 10 modified functions with the non-authenticated address
      - Verify each returns `ContractError::NotAWatcher` (which comes AFTER auth check would fail)
      - Note: with `env.mock_all_auths()` in setup, unauthenticated calls will fail the `require_auth()` check at the Soroban SDK level, not at the contract level. Tests must be adjusted: either disable `mock_all_auths` for auth failure tests, or test with a properly signed but unauthorized address.
      
      Test names:
      - `test_get_alert_requires_auth`
      - `test_get_alert_active_requires_auth`
      - `test_get_alert_owner_requires_auth`
      - `test_get_alerts_for_contract_requires_auth`
      - `test_get_active_alerts_for_contract_requires_auth`
      - `test_get_alerts_by_owner_requires_auth`
      - `test_get_alerts_by_ids_requires_auth`
      - `test_get_contract_alerts_paginated_requires_auth`
      - `test_get_alerts_by_owner_paginated_requires_auth`
      - `test_get_active_contract_alerts_paged_requires_auth`
      - `test_get_alerts_modified_since_requires_auth`
      - `test_get_alerts_modified_since_ledger_requires_auth`
      
      Files: `contracts/alert-registry/src/tests.rs`
      
      Verify: `cargo test --package alert-registry --lib tests` passes; auth failure tests confirm NotAWatcher or auth rejection

- [ ] 8. Add tests for authenticated + authorized querier success on gated reads
      
      In `contracts/alert-registry/src/tests.rs`, add test functions showing that with a proper watcher registered and authenticated, gated reads succeed. One test per function:
      - `test_get_alert_authenticated_succeeds`
      - `test_get_alert_active_authenticated_succeeds`
      - `test_get_alert_owner_authenticated_succeeds`
      - `test_get_alerts_for_contract_authenticated_succeeds`
      - `test_get_active_alerts_for_contract_authenticated_succeeds`
      - `test_get_alerts_by_owner_authenticated_succeeds`
      - `test_get_alerts_by_ids_authenticated_succeeds`
      - `test_get_contract_alerts_paginated_authenticated_succeeds`
      - `test_get_alerts_by_owner_paginated_authenticated_succeeds`
      - `test_get_active_contract_alerts_paged_authenticated_succeeds`
      - `test_get_alerts_modified_since_authenticated_succeeds`
      - `test_get_alerts_modified_since_ledger_authenticated_succeeds`
      
      Files: `contracts/alert-registry/src/tests.rs`
      
      Verify: `cargo test --package alert-registry --lib tests` passes; all authenticated tests confirm data is returned correctly

- [ ] 9. Update sync function callers in tests
      
      Search for any existing test code calling `get_alerts_modified_since` or `get_alerts_modified_since_ledger` and update the calls to include a `querier` Address as the second parameter. Update expected return types from `Vec<AlertConfig>` to `Result<Vec<AlertConfig>, ContractError>` and unwrap/match as needed.
      
      Files: `contracts/alert-registry/src/tests.rs` (search for calls to the two sync functions)
      
      Verify: `cargo test --package alert-registry --lib` passes; no compilation errors from signature mismatch

- [ ] 10. Update TypeScript bindings (manual or regenerated)
      
      The TypeScript bindings at `bindings/alert-registry/src/index.ts` re-export from `dist/` which is generated. Either:
      a) Regenerate via `stellar contract bindings typescript`, or
      b) Manually update function signatures to reflect the new querier parameter and Result return type for the sync functions
      
      For each of the 10 modified functions, add a JSDoc comment: "Caller must sign the transaction as querier (querier.require_auth() enforced on-chain)."
      
      Files: `bindings/alert-registry/src/index.ts` (or regenerate `dist/` by running build tool)
      
      Verify: TypeScript compiles; signatures match Rust contract

- [ ] 11. Update bindings README if it has code examples
      
      Check `bindings/alert-registry/README.md` for any code examples using the 10 modified functions. Update signatures to pass querier as second param, and update return type handling for the sync functions (now Result).
      
      Files: `bindings/alert-registry/README.md`
      
      Verify: Examples compile and make sense in context

- [ ] 12. Add v0.2.1 migration section to main README
      
      Add a section to `README.md` documenting the breaking changes in v0.2.1:
      - List the 10 functions with changed signatures
      - Explain the breaking change: callers must now sign as querier
      - Provide before/after CLI examples for at least 2-3 functions using `stellar contract invoke`
      - Mention that `get_alerts_modified_since` and `get_alerts_modified_since_ledger` now return `Result` instead of `Vec`
      
      Files: `README.md`
      
      Verify: Documentation is clear and examples are syntactically correct

- [ ] 13. Add entry to CHANGELOG.md
      
      Add a new section `## [0.2.1] - <date>` to the top of the unreleased/released sections with:
      - Summary of fix #197: authentication on gated reads
      - Summary of fix #198: querier parameter + auth on sync functions
      - List of the 10 functions with changed signatures
      - Note about breaking changes and the reason (security: prevent querier impersonation)
      
      Files: `CHANGELOG.md`
      
      Verify: CHANGELOG format matches existing entries; date is present and reasonable

- [ ] 14. Build and test the contract
      
      Run `cargo build --release --target wasm32-unknown-unknown --all` to compile.
      Verify the WASM binary at `target/wasm32-unknown-unknown/release/alert_registry.wasm` is less than 60 KB.
      Run `cargo test --workspace --locked` to ensure all tests pass.
      
      Files: (build artifacts only)
      
      Verify: 
      - Build succeeds with no errors or warnings
      - WASM size is reported: `ls -lh target/wasm32-unknown-unknown/release/alert_registry.wasm`
      - Size is < 60 KB
      - All tests pass: `cargo test --workspace --locked` returns 0 errors

- [ ] 15. Commit and tag
      
      Locally commit the changes on a feature branch with the message:
      `feat: add authentication to gated reads and incremental sync (#197, #198)`
      
      Create a git tag `v0.2.1` pointing to this commit.
      
      Do NOT push; let the normal CI/review/merge process handle it.
      
      Files: (git objects)
      
      Verify: `git log --oneline | head -1` shows the commit message; `git tag -l v0.2.1` confirms the tag exists

## Notes

- All functions that accept `querier: Address` must call `querier.require_auth();` as the FIRST line of the function body, before any other logic, to prevent impersonation.
- The two sync functions change return type from `Vec<AlertConfig>` to `Result<Vec<AlertConfig>, ContractError>` to propagate the `NotAWatcher` error when gating is enabled and querier is not authorized.
- The `#[must_use]` attribute can be dropped from the sync functions since they now return `Result`, which is inherently marked as must-use by Rust best practices.
- Version in both `lib.rs` (contractmeta) and `Cargo.toml` must be bumped to `0.2.1`.
- The contract must compile to < 60 KB WASM to stay within the Soroban limit.
- TypeScript bindings changes are manual or require regeneration; the plan assumes the build tool is available.
