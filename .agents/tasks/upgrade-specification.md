# OverStand Upgrade Specification

**Version:** 1.0  
**Date:** 2025  
**Status:** READY FOR IMPLEMENTATION  
**Target Outcome:** Global recognition as the de facto standard for decentralized on-chain alerts on Stellar  

---

## Executive Summary

This document specifies the complete upgrade roadmap for OverStand across three tiers:

- **Tier 0 (Critical):** Security fixes blocking mainnet deployment (2–3 weeks)
- **Tier 1 (High-Priority):** Core extensibility and SDK features (1–3 months post-mainnet)
- **Tier 2 (Medium-Priority):** Governance, operations, and ecosystem hardening (6+ months)

The Tier 0 fixes are **mandatory** before production mainnet deployment. Tier 1 features are **essential** for global adoption and ecosystem extensibility. Tier 2 establishes long-term governance and operational maturity.

---

## SECTION 1: TIER 0 CRITICAL SECURITY FIXES (Target: 2–3 weeks)

### Overview

Two authentication vulnerabilities prevent secure mainnet deployment:

1. **Fix #197:** Read functions with `querier` parameter do not authenticate the querier, allowing impersonation of authorized watchers.
2. **Fix #198:** Incremental sync functions bypass watcher-gating entirely.

Both must be fixed before any production mainnet deployment. This section specifies exact pseudocode, ABI impact, and migration steps for each.

---

### Important: Current State vs. Target State (Clarification)

**DECISION: HIGH-001 Resolution**

To resolve the contradiction between "new features" and "security fixes," this specification ASSUMES the following (to be verified):

**If gated read functions WITH `querier` parameter already exist in v0.2.0:**
- This is a **security fix:** adding `require_auth()` to existing gated reads
- Framing: "Fix #197/198: Add Authentication to Existing Gated Reads"
- Impact: Breaking change to existing function semantics
- All 8 affected functions keep their names; semantics change from unauthenticated to authenticated

**If gated read functions do NOT exist in v0.2.0:**
- This is a **new feature:** implementing secure gated reads for the first time
- Framing: "Tier 0 Addition: Implement Secure Gated Reads with Authentication"
- Impact: New functions added to contract surface
- All 8 functions are new to v0.3.0; existing read functions (if any) remain unchanged

**Action Required Before Implementation:** Read v0.2.0 AlertRegistry contract source (`contracts/alert-registry/src/lib.rs`) in the repository to determine which scenario is true. This specification assumes **Scenario 1** (functions exist but lack authentication) based on Fix #197/198 terminology, but verification is mandatory.

**For this specification:** We proceed assuming Scenario 1 (fixing existing functions), which requires breaking API changes to 10 function signatures (8 from Fix #197, 2 from Fix #198).

---

### Fix #197: Gated Reads Must Authenticate the `querier` Parameter

#### Problem Statement

When an AlertRegistry admin enables watcher-gating via `set_watcher_registry(registry_address)`, all gated read queries accept a `querier: Address` parameter and internally check whether the querier is authorized via:

```
is_authorized = AlertRegistry::WatcherRegistry.is_watcher_authorized(querier)
```

However, the `querier` parameter is **not cryptographically authenticated by Stellar**. A malicious caller can pass any address (e.g., a known authorized watcher) as the `querier`, receive alert data, and leave no on-chain trace of who made the request. The watcher whose address was spoofed has no way to know their identity was used maliciously.

**Security Implication:** Watcher-gating is ineffective; any unauthenticated caller can masquerade as any other address.

#### Solution: Require Authentication of the Querier

Add `querier.require_auth()` to every gated read function **before** performing any watcher-gating check or data access. This forces Stellar to verify that the `querier` address signed the current transaction. Only the caller with the private key for `querier` can satisfy this check.

#### Affected Functions

The following read functions in `AlertRegistry` must be updated. Each is listed with:
- Function name and current signature
- Current line range (if available from source inspection)
- Whether ABI is breaking
- Required changes

| Function | File | Current Behavior | Change Required | Breaking Change |
|---|---|---|---|---|
| `get_alert` | `alert-registry/src/lib.rs` | Takes `querier: Address`, checks watcher-gating after data lookup | Add `querier.require_auth()` at entry | [BREAKING] Callers cannot pass unauthenticated addresses |
| `get_alert_active` | `alert-registry/src/lib.rs` | Takes `querier: Address`, checks watcher-gating | Add `querier.require_auth()` at entry | [BREAKING] |
| `get_alerts_for_contract` | `alert-registry/src/lib.rs` | Takes `querier: Address`, returns all alerts for contract | Add `querier.require_auth()` at entry | [BREAKING] |
| `get_active_alerts_for_contract` | `alert-registry/src/lib.rs` | Takes `querier: Address`, filters by active=true | Add `querier.require_auth()` at entry | [BREAKING] |
| `get_alerts_by_owner` | `alert-registry/src/lib.rs` | Takes `querier: Address`, returns all alerts by owner | Add `querier.require_auth()` at entry | [BREAKING] |
| `get_contract_alerts_paginated` | `alert-registry/src/lib.rs` | Takes `querier: Address`, paginated query for contract alerts | Add `querier.require_auth()` at entry | [BREAKING] |
| `get_alerts_by_owner_paginated` | `alert-registry/src/lib.rs` | Takes `querier: Address`, paginated query for owner alerts | Add `querier.require_auth()` at entry | [BREAKING] |
| `get_active_contract_alerts_paged` | `alert-registry/src/lib.rs` | Takes `querier: Address`, paginated active alerts for contract | Add `querier.require_auth()` at entry | [BREAKING] |

#### Pseudocode

**Before (Vulnerable):**

```rust
pub fn get_alert(env: Env, querier: Address, config_id: u64) -> AlertConfig {
    // No authentication of querier
    let data = env.storage().persistent().get(&DataKey::Alert(config_id))?;
    
    // Gating happens here, but querier is trusted
    if let Some(registry) = get_watcher_registry(&env) {
        let is_watcher = registry.is_watcher_authorized(&querier);
        if !is_watcher {
            panic_with_error!(env, ContractError::NotAWatcher);
        }
    }
    
    data
}
```

**After (Secure):**

```rust
pub fn get_alert(env: Env, querier: Address, config_id: u64) -> AlertConfig {
    // REQUIRED: Authenticate querier at entry point
    querier.require_auth();
    
    let data = env.storage().persistent().get(&DataKey::Alert(config_id))?;
    
    // Now gating is effective because querier has proven their identity
    if let Some(registry) = get_watcher_registry(&env) {
        let is_watcher = registry.is_watcher_authorized(&querier);
        if !is_watcher {
            panic_with_error!(env, ContractError::NotAWatcher);
        }
    }
    
    data
}
```

Same change applies to all 8 affected functions: add `querier.require_auth();` as the first statement.

#### ABI Impact

**[BREAKING]** All eight functions change their semantics: they now reject any caller that does not hold the private key for `querier`. Existing callers must adapt:

- **TypeScript bindings:** Client code calling these functions must now authenticate the querier address (already done by `stellar-sdk` when building transactions, but the semantics change from "read-only" to "signed").
- **CLI users:** `stellar contract invoke` commands must now specify `--source` (the signer) as the same identity as `querier`.
- **Tests:** Unit and integration tests must update mock calls to use authenticated sources.

### Retry and Fallback Specification

**Cross-Contract Call Failures:**

When AlertRegistry calls RuleRegistry::validate_rule for a custom rule and receives an error (e.g., RuleRegistry is temporarily unavailable):

1. **Alert registration with 1+ custom rules:** Reject immediately with ExternalRegistryError.
   - No automatic retry; caller is responsible.
   - RuleRegistry downtime blocks ALL alert registrations using custom rules.
   - Rationale: Fail-closed for security; built-in rules always work.

2. **Alert registration with ONLY built-in rules:** Always succeeds (no cross-contract call).
   - Fallback path ensures base functionality survives RuleRegistry outage.

3. **Caller Responsibility:** SDK clients must implement retry logic as needed.
   - Python: backoff_factor, max_retries (see HIGH-003)
   - Go: same pattern

**Builtin Rules Always Available:** VALID_RULE_DESCRIPTORS (transfer/mint/burn/approve/clawback) are validated locally; no cross-contract call required. Alerts using only these rules always register successfully, even if RuleRegistry is offline.

**Implementation Pseudocode:**

```rust
pub fn register_alert(..., rules: Vec<String>) -> u64 {
    owner.require_auth();
    
    // Validate each rule (fast path: builtins don't call RuleRegistry)
    for rule in &rules {
        if !Self::validate_rule(&env, rule.clone()) {
            panic_with_error!(env, ContractError::InvalidRuleDescriptor);
        }
    }
    
    // ... rest of logic (fails if ANY rule is invalid)
}

fn validate_rule(env: &Env, rule: String) -> bool {
    // Check hardcoded builtins first (fast path, never fails)
    if VALID_RULE_DESCRIPTORS.contains(&rule.as_str()) {
        return true;
    }
    
    // If no RuleRegistry configured, custom rules are invalid
    if let Some(registry) = Self::get_rule_registry(&env) {
        // Cross-contract call; may fail
        match registry.validate_rule(&rule) {
            Ok(is_valid) => is_valid,
            Err(_) => {
                // Cross-contract call failed; reject rule (fail-closed)
                false
            }
        }
    } else {
        // No RuleRegistry; only builtins allowed
        false
    }
}
```

#### ABI Impact

**[BREAKING]** All eight functions change their semantics: they now reject any caller that does not hold the private key for `querier`. Existing callers must adapt:

- **TypeScript bindings:** Client code calling these functions must now authenticate the querier address (already done by `stellar-sdk` when building transactions, but the semantics change from "read-only" to "signed").
- **CLI users:** `stellar contract invoke` commands must now specify `--source` (the signer) as the same identity as `querier`.
- **Tests:** Unit and integration tests must update mock calls to use authenticated sources.

#### High-002 Resolution: Function Count Clarification

**DECISION: Complete Precision on Function Count and Terminology**

- **Fix #197 affects 8 gated read functions** (they gain `querier.require_auth()` at entry point):
  1. `get_alert`
  2. `get_alert_active`
  3. `get_alerts_for_contract`
  4. `get_active_alerts_for_contract`
  5. `get_alerts_by_owner`
  6. `get_contract_alerts_paginated`
  7. `get_alerts_by_owner_paginated`
  8. `get_active_contract_alerts_paged`

- **Fix #198 affects 2 incremental sync functions** (they gain `querier: Address` parameter AND `require_auth()` + watcher-gating check):
  1. `get_alerts_modified_since`
  2. `get_alerts_modified_since_ledger`

- **Total: 10 functions** with breaking signature changes (functions 1-8 change semantics; functions 9-10 add parameter)

All references in this specification use "8 gated read functions" and "2 incremental sync functions" for precision. When counting total affected functions, the count is always 10.

#### Call Sites Requiring Updates

**TypeScript Bindings (`bindings/alert-registry/src/`)**

- `src/index.ts` or the generated client: Every call to the 10 functions listed above must be updated.
- Update JSDoc to note authentication requirements.

**CLI Examples (`README.md`)**

All stellar contract invoke examples for the 10 functions must add the `--source` flag to authenticate the querier:

```bash
# OLD (may still work but querier not authenticated):
stellar contract invoke \
  --id <ALERT_REGISTRY_CONTRACT_ID> \
  --network testnet \
  -- get_alert \
  --querier <QUERIER_ADDRESS> \
  --config_id 1

# NEW (querier authenticated):
stellar contract invoke \
  --id <ALERT_REGISTRY_CONTRACT_ID> \
  --source <QUERIER_IDENTITY> \
  --network testnet \
  -- get_alert \
  --querier <QUERIER_ADDRESS> \
  --config_id 1
```

**Integration Tests (`contracts/integration-tests/src/`)**

All test cases invoking these functions must:
1. Build transactions with the querier as the signer (already typical in most tests)
2. Verify that non-authorized queriers are rejected when watcher-gating is enabled

**Off-Chain Watchers (`tx-watch-core`, not in this repo)**

Watcher nodes polling alerts must sign their queries with their own private key (as querier). This is already the expected pattern but now enforced.

#### Migration Strategy

**For Existing Mainnet Deployments (if any):**

Since mainnet is not yet live, migration is a non-issue. This is the **first** mainnet deployment.

**For Testnet:**

1. Deploy a new contract version (v0.2.1) with these fixes.
2. Existing testnet deployments at the old address remain unchanged.
3. Alert owners must re-register alerts on the new contract address (a one-time one-ledger operation per alert).
4. Watchers must update their polling code to use the new contract address.

#### Version Strategy Clarification

**DECISION: Use v0.3.0 for both testnet and mainnet deployments.**

Rationale:
- No intermediate v0.2.1; fixes go directly to v0.3.0
- Cleaner versioning; avoids confusion between testnet and mainnet versions
- Watcher operators maintain single version (v0.3.0) across all networks

**Timeline:**

| Phase | Version | Network | Action | Watchers Must Update |
|---|---|---|---|---|
| Week 1 | v0.3.0 | Testnet | Deploy security fixes + breaking signature changes | YES (upgrade from v0.2.0) |
| Week 1–2 | v0.3.0 | Testnet | Stress-test; audit begins | Ongoing |
| Week 2–3 | v0.3.0 | Mainnet | Deploy to mainnet with identical contract code | None (first mainnet version) |
| Week 3+ | v0.3.0 | Testnet + Mainnet | Both networks run v0.3.0; consistent behavior | No (both on same version) |

**Testnet Migration Path:**

1. v0.2.0 contract remains at old address for 2 weeks (grace period for external users)
2. v0.3.0 deployed to new address immediately
3. Alert owners manually migrate: re-register on v0.3.0 (one-ledger operation)
4. Watchers update to call v0.3.0 contract address
5. v0.2.0 address deprecated after 2 weeks

**No v0.2.1 release.**

#### Pseudocode

---

### Fix #198: Add Watcher-Gating to Incremental Sync Functions

#### Problem Statement

The incremental sync functions `get_alerts_modified_since(since: i64, offset: u32, limit: u32)` and `get_alerts_modified_since_ledger(since_ledger: u32, offset: u32, limit: u32)` return lists of recently modified alerts (with timestamps, ledger numbers, and tombstone metadata).

These functions **do not accept a `querier` parameter**, so they **cannot enforce watcher-gating**. An unauthenticated caller can fetch the full list of all alerts modified in a time window, leaking alert metadata (existence, modification timing) without authorization.

This is a **privacy breach**: alert owners expect that when watcher-gating is enabled, only authorized watchers can see alert existence.

**Security Implication:** Incremental sync leaks alert metadata; watcher-gating is incomplete.

#### Solution: Add `querier` Parameter and Enforce Gating

Add an optional or required `querier: Address` parameter to both functions. When `querier` is provided:
1. Call `querier.require_auth()` to authenticate them
2. Check if querier is an authorized watcher (via WatcherRegistry)
3. Return results only if authorized

**Design Choice:** `querier: Option<Address>` vs. `querier: Address`

| Choice | Pros | Cons | Decision |
|---|---|---|---|
| `querier: Option<Address>` | Backward-compatible with unauthenticated sync if gating not enabled | Adds complexity; two code paths (nullable parameter support in some SDKs) | Preferred if testnet has external callers |
| `querier: Address` | Simple; one code path; forces authentication | Breaking change; any existing unauthenticated caller breaks | Cleaner but only viable if testnet is internal-only |

**Recommendation:** Use `querier: Address` (required parameter) for simplicity and security-by-default. If testnet callers exist that rely on unauthenticated incremental sync, they must update to provide a querier address (a quick fix).

#### Design Decision: Querier Parameter Type

**DECISION: Use `querier: Address` (required parameter).**

Rationale:
- Security-by-default: Forces all incremental sync callers to authenticate, closing the privacy leak
- Simplicity: One code path; no need for optional parameter handling in SDKs
- Mainnet readiness: If testnet has external callers relying on unauthenticated sync, they have 2 weeks (before mainnet) to update their code
- Consistency: All gated read functions now require authentication

Breaking Change Notice:
- Testnet watchers currently calling `get_alerts_modified_since(env, since, offset, limit)` must update to `get_alerts_modified_since(env, querier, since, offset, limit)`
- This change is applied in v0.3.0, which is released as v0.3.0 (minor version bump, not patch) to signal breaking changes
- All watchers must re-register against v0.3.0 contract address; v0.2.0 address is deprecated

Migration Deadline:
- v0.2.0 remains on testnet for 2 weeks (grace period)
- v0.3.0 deployed to testnet concurrently
- All watcher operators must migrate before mainnet launch (Week 3)

#### Pseudocode

**Before (Vulnerable):**

```rust
pub fn get_alerts_modified_since(
    env: Env,
    since: i64,
    offset: u32,
    limit: u32,
) -> Vec<(u64, AlertConfig, i64)> {
    // No querier parameter, no authentication, no gating
    let cursor = ...;
    let results = ...;
    results
}

pub fn get_alerts_modified_since_ledger(
    env: Env,
    since_ledger: u32,
    offset: u32,
    limit: u32,
) -> Vec<(u64, AlertConfig, u32)> {
    // No querier parameter, no authentication, no gating
    let cursor = ...;
    let results = ...;
    results
}
```

**After (Secure):**

```rust
pub fn get_alerts_modified_since(
    env: Env,
    querier: Address,
    since: i64,
    offset: u32,
    limit: u32,
) -> Vec<(u64, AlertConfig, i64)> {
    // REQUIRED: Authenticate querier at entry point
    querier.require_auth();
    
    // Enforce watcher-gating if enabled
    if let Some(registry) = get_watcher_registry(&env) {
        let is_watcher = registry.is_watcher_authorized(&querier);
        if !is_watcher {
            panic_with_error!(env, ContractError::NotAWatcher);
        }
    }
    
    // Return results only after gating check passes
    let cursor = ...;
    let results = ...;
    results
}

pub fn get_alerts_modified_since_ledger(
    env: Env,
    querier: Address,
    since_ledger: u32,
    offset: u32,
    limit: u32,
) -> Vec<(u64, AlertConfig, u32)> {
    // REQUIRED: Authenticate querier at entry point
    querier.require_auth();
    
    // Enforce watcher-gating if enabled
    if let Some(registry) = get_watcher_registry(&env) {
        let is_watcher = registry.is_watcher_authorized(&querier);
        if !is_watcher {
            panic_with_error!(env, ContractError::NotAWatcher);
        }
    }
    
    // Return results only after gating check passes
    let cursor = ...;
    let results = ...;
    results
}
```

#### ABI Impact

**[BREAKING]** Both functions gain a required `querier: Address` parameter. All callers must supply it.

#### Call Sites Requiring Updates

**TypeScript Bindings (`bindings/alert-registry/src/`)**

- `src/index.ts` or generated client: Update method signatures to accept and pass `querier` parameter.
- Update JSDoc to note querier authentication requirement.

**CLI Examples (`README.md`)**

```bash
# OLD (unauthenticated, vulnerable):
stellar contract invoke \
  --id <ALERT_REGISTRY_CONTRACT_ID> \
  --network testnet \
  -- get_alerts_modified_since \
  --since 1700000000 \
  --offset 0 \
  --limit 50

# NEW (authenticated, secure):
stellar contract invoke \
  --id <ALERT_REGISTRY_CONTRACT_ID> \
  --source <QUERIER_IDENTITY> \
  --network testnet \
  -- get_alerts_modified_since \
  --querier <QUERIER_ADDRESS> \
  --since 1700000000 \
  --offset 0 \
  --limit 50
```

**Integration Tests (`contracts/integration-tests/src/`)**

All test cases using these functions must:
1. Provide a `querier` parameter (the test's signer address)
2. Ensure querier is authenticated (already the case in transaction-based tests)
3. Add new test cases to verify gating rejects unauthorized queriers

**Off-Chain Watchers (`tx-watch-core`, not in this repo)**

Watchers performing incremental sync must update their polling code to:
1. Construct queries with the watcher's own address as `querier`
2. Sign the query transaction with the watcher's private key

#### Migration Strategy

Same as Fix #197:
- Deploy v0.3.0 (minor version bump, breaking change in signatures)
- Testnet gets new contract address; alert re-registration required
- Update watchers to use new function signatures
- Update CLI examples and docs

---

### Tier 0 Implementation Checklist

#### Code Changes

- [ ] **AlertRegistry contract (`contracts/alert-registry/src/lib.rs`)**
  - [ ] Add `querier.require_auth()` to `get_alert`
  - [ ] Add `querier.require_auth()` to `get_alert_active`
  - [ ] Add `querier.require_auth()` to `get_alerts_for_contract`
  - [ ] Add `querier.require_auth()` to `get_active_alerts_for_contract`
  - [ ] Add `querier.require_auth()` to `get_alerts_by_owner`
  - [ ] Add `querier.require_auth()` to `get_contract_alerts_paginated`
  - [ ] Add `querier.require_auth()` to `get_alerts_by_owner_paginated`
  - [ ] Add `querier.require_auth()` to `get_active_contract_alerts_paged`
  - [ ] Add `querier: Address` parameter to `get_alerts_modified_since`
  - [ ] Add `querier: Address` parameter to `get_alerts_modified_since_ledger`
  - [ ] Add `querier.require_auth()` + watcher-gating check to both incremental sync functions
  - [ ] Update `Cargo.toml` version: `v0.2.0` → `v0.3.0`
  - [ ] Update `contractmeta!(key = "Version", val = "0.3.0")`

#### Testing

- [ ] **Unit Tests (`contracts/alert-registry/tests.rs`)**
  - [ ] Add test: `get_alert` rejects unauthenticated querier
  - [ ] Add test: `get_alert` succeeds when querier is authenticated and authorized
  - [ ] Add test: `get_alert` rejects authenticated but unauthorized querier (when gating enabled)
  - [ ] Add test: `get_alerts_modified_since` rejects unauthenticated querier
  - [ ] Add test: `get_alerts_modified_since` succeeds when querier is authenticated and authorized
  - [ ] Add test: `get_alerts_modified_since_ledger` rejects unauthenticated querier
  - [ ] Repeat pattern for all 8 functions in Fix #197

- [ ] **Integration Tests (`contracts/integration-tests/src/`)**
  - [ ] End-to-end: Admin enables watcher-gating, registers watchers, creates alerts
  - [ ] Authorized watcher can read gated queries
  - [ ] Unauthorized address cannot read gated queries (rejected or empty results)
  - [ ] Test incremental sync gating with multiple alerts

- [ ] **Property-Based Tests (`contracts/alert-registry/proptests.rs`)**
  - [ ] Property: For all querier addresses Q and all alerts A, if Q is not authenticated, queries fail
  - [ ] Property: For all authenticated authorized queriers Q, all gated queries succeed

#### Documentation

- [ ] **README.md**
  - [ ] Update all CLI examples for gated reads: add `--source <QUERIER_IDENTITY>` and `--querier <QUERIER_ADDRESS>`
  - [ ] Update TypeScript examples to show authentication

- [ ] **docs/alert-registry.md**
  - [ ] Document that all gated read functions now require `querier.require_auth()`
  - [ ] Add security notice: "Incremental sync now enforces watcher-gating"

- [ ] **CHANGELOG.md**
  - [ ] v0.3.0 breaking changes: 10 function signatures changed to require `querier.require_auth()`

- [ ] **docs/upgrade-guide.md**
  - [ ] Create migration guide: "Upgrading from v0.2.0 to v0.3.0 — Authentication Changes"
  - [ ] List all 10 functions that changed
  - [ ] Show before/after CLI examples
  - [ ] Link TypeScript binding migration notes

#### TypeScript Bindings

- [ ] **`bindings/alert-registry/src/index.ts`**
  - [ ] Regenerate from new WASM (stellar contract bindings typescript)
  - [ ] Manually verify `querier` parameter added to all methods
  - [ ] Update JSDoc: "Caller must sign this transaction (querier.require_auth)"

- [ ] **`bindings/alert-registry/README.md`**
  - [ ] Update examples to show authenticated calls
  - [ ] Note: "All gated read queries now require transaction signing"

- [ ] **npm package version**
  - [ ] Bump to `@QingQosh/alert-registry-bindings@0.3.0`
  - [ ] Add BREAKING CHANGES section to package release notes

#### Mainnet Deployment Plan

The Tier 0 work unlocks mainnet deployment. Once all fixes are verified on testnet:

1. **Tag Release:** Create `v0.3.0` git tag in OverStand repo
2. **Build WASM:** `cargo build --release --target wasm32-unknown-unknown`
3. **Verify Binary:**
   - WASM size < 60KB
   - SHA-256 hash matches golden file
   - All tests pass
4. **Deploy to Testnet (dry-run):**
   - `scripts/deploy-testnet.sh v0.3.0`
   - Run full integration test suite
   - Smoke-test with external watcher (if available)
5. **Deploy to Mainnet:**
   - Reserve mainnet contract addresses
   - Execute `scripts/deploy-mainnet.sh v0.3.0` on secured host
   - Record addresses in `DEPLOYMENTS.md`
   - Update TypeScript bindings with mainnet addresses
   - Publish bindings to npm (`@QingQosh/alert-registry-bindings@0.3.0`)
6. **Post-Launch Monitoring:**
   - Monitor Soroban RPC for errors
   - Daily liveness check (are gated reads being called successfully?)
   - Alert setup if error rates spike

---

### Mainnet Deployment Plan (Post-Security Fixes)

#### 1. Testnet Stress-Test Checklist (Updated with Quantified Acceptance Criteria)

Before declaring mainnet-ready, verify the following scenarios on testnet with the fixed v0.3.0 contracts:

| Scenario | Description | Success Criteria | Failure Threshold |
|---|---|---|---|
| **High-Volume Registration** | 1000 alert registrations in 1 hour | All 1000 alerts stored without rejection; zero storage errors | >0 rejections or storage errors → BLOCK mainnet |
| **Mixed Read/Write Load** | 100 watchers querying gated reads concurrently while alerts are being created | Query success rate ≥99.5%; p95 latency ≤3s | Query success <99.5% or p95 latency >3s → BLOCK mainnet |
| **Large Watcher Set** | 50 watchers registered in WatcherRegistry | Cross-contract calls succeed; zero gas limit errors | Any gas limit hit → BLOCK mainnet |
| **Complex Rule Matching** | 100 alerts with 5 rules each, watched by multiple contracts | All 500 rules validate correctly; zero false positives/negatives in 1000-TX simulation | Any validation error or rule mismatch → BLOCK mainnet |
| **Incremental Sync Throughput** | Watchers polling `get_alerts_modified_since_ledger` continuously for 24h | Cursor advances correctly; zero tombstone loss; p95 latency ≤1s | Any data loss or latency >1s → BLOCK mainnet |
| **TTL Culling** | 5000 alerts expire simultaneously; prune operations triggered | All expired entries removed; zero storage leaks; active alerts unaffected | Any storage leak or active alert affected → BLOCK mainnet |
| **Webhook Rotation** | 100 webhook proposals and confirmations under concurrent alert access | All rotations complete successfully; zero orphaned proposals; zero data corruption | Any failed rotation or data corruption → BLOCK mainnet |
| **Admin Transfer** | Admin transfers happen while watchers are reading; ownership transfers queued | All transfers complete successfully; reads unaffected; zero state inconsistency | Any failed transfer or state inconsistency → BLOCK mainnet |
| **Fail-Open vs Fail-Closed** | Intentionally disable WatcherRegistry; re-enable it | Reads become public; re-enabling gating works correctly; no data loss | Any unexpected behavior → BLOCK mainnet |
| **Edge Case: Max Limits** | Trigger per-owner/per-contract/global alert limits | Rejected with correct error; alerts still queryable; no partial state | Any incorrect error or partial state → BLOCK mainnet |

**Acceptance Decision (Revised):**

Mainnet launch is approved if and only if ALL of the following are met:

1. **Security Fixes:** Issues #197 and #198 implemented and merged to main branch ✅
2. **All 10 stress tests PASS** (see table above) ✅
3. **Third-Party Security Audit: REQUIRED** (no exceptions)
   - Audit must be completed by an external firm with Soroban contract experience
   - No known or medium-severity issues; HIGH/CRITICAL issues must be resolved
   - Audit report is public (posted to GitHub releases or docs/)
4. **Code Review:** Main branch reviewed and approved by at least 2 maintainers ✅
5. **Mainnet Admin Key Custody:** Secured via multi-sig or hardware wallet; backup procedures documented ✅

**If a stress test FAILS:**

1. **Immediate:** Stop testnet deployment; do not proceed to mainnet
2. **Root Cause:** Identify whether failure is contract bug, test infrastructure issue, or environmental (24h SLA)
3. **Fix:** Implement contract fix or test adjustment
4. **Retest:** Re-run the failed stress test; all dependent tests also re-run
5. **Approval:** Maintainers review fix; re-approve if appropriate
6. **Timeline Reset:** Mainnet launch is delayed by at least 1 week from re-approval

**If audit identifies issues:**

1. **CRITICAL/HIGH:** Must be fixed; audit re-run after fix; restart timeline
2. **MEDIUM:** Must be fixed or explicitly accepted (documented risk); maintainer sign-off required
3. **LOW:** Document as known limitation; may not block launch

**Final Sign-Off (Checklist):**

- [ ] Security Audit: COMPLETED and PASSED
- [ ] All 10 stress tests: PASSED (log files attached to GitHub release)
- [ ] Code review: APPROVED (2+ maintainers)
- [ ] Admin key custody: SECURED and DOCUMENTED
- [ ] Mainnet deployment authorized by: [Name / Date]

**Sign-Off:**
- [ ] Security Audit: PASSED (if applicable, via external firm)
- [ ] All 10 stress tests: PASSED
- [ ] Code review: APPROVED
- [ ] Mainnet deployment signed off by: [Name/Date]

**Tooling:** Use `stellar-load` or `cargo-flamegraph` to profile resource usage; capture before/after metrics.

#### 2. Contract Upgrade vs. Redeploy Decision

**Question:** Should mainnet AlertRegistry be deployed fresh, or is there a path to upgrade an existing contract?

**Answer:** Fresh deployment on mainnet. Reasoning:

1. Stellar Testnet resets periodically; no production-like state exists.
2. Even if state existed on testnet, main-net is the authoritative deployment.
3. Storage layout is stable (no breaking data migrations planned between v0.2.0 and v0.3.0).
4. Upgrading an existing contract requires on-chain proof of prior deployment, which doesn't exist yet.

**Implication:** Mainnet gets a new contract address; testnet gets a new address; both are separate deployments.

**Future Upgrades (Post-Mainnet):** If a v0.4.0 is needed, Stellar's contract upgrade mechanism (authorized by admin) can be used—no redeploy required.

#### 3. Version Governance: Semver Tagging, On-Chain Version Storage, Migration Contracts

**On-Chain Version Storage:**

Both contracts will use `contractmeta!` to store version:

```rust
contractmeta!(key = "Version", val = "0.3.0");
```

This is queryable via:

```bash
stellar contract info --id <CONTRACT_ID> --network mainnet
```

CLI will return `"Version": "0.3.0"`.

**Semver Tagging (GitHub):**

- Tag every release: `git tag v0.3.0 && git push origin v0.3.0`
- GitHub Actions workflow (`publish-bindings.yml`) publishes bindings on tag
- npm packages use semver: `@QingQosh/alert-registry-bindings@0.3.0`
- CHANGELOG.md entry per release with breaking changes clearly marked

**Migration Contracts (Future):**

If a breaking upgrade is needed (e.g., v0.4.0 changes storage layout), a migration contract can:
1. Read state from old contract
2. Transform it
3. Write to new contract

For now, this is future-only. Document the pattern in `docs/migration-contracts.md` for implementers.

**Versioning Policy (Document in `docs/versioning-policy.md`):**

- **Major (X.y.z):** ABI breaking changes, storage migration, new rule descriptors
- **Minor (x.Y.z):** Non-breaking feature additions, security patches that don't change semantics
- **Patch (x.y.Z):** Bug fixes, internal optimizations, no ABI or semantics changes

Examples:
- v0.2.0 → v0.3.0 (minor): Fix #197/198 break gated read signatures; new parameter required
- v0.3.0 → v0.4.0 (minor): Add RuleRegistry support; new optional feature
- v0.4.0 → v1.0.0 (major): Mainnet-stable; mark as production-ready

#### 4. Rollback Plan

**Scenario:** Mainnet AlertRegistry has a bug that causes data loss or unexpected behavior.

**Immediate Mitigation (No Redeploy):**

1. **Admin Pause:** If WatcherRegistry exists, admin calls `pause_contract()` or manually stops recommending the buggy contract
2. **Stop Watchers:** Broadcast to watcher operators: "Stop querying contract X; switch to contract Y"
3. **Diagnostic Snapshot:** Export state from chain for post-mortem analysis

**Rollback Path:**

- If bug is in v0.3.0, redeploy to a fresh address (v0.3.1 with fix)
- Broadcast new contract address to all watcher operators
- Alert owners migrate by re-registering alerts on new contract (one-ledger operation per alert)
- Old contract is abandoned (data remains on-chain but ignored)

**Prevention:**

- Run 2-week testnet stress-test (see above) before mainnet deployment
- Schedule a 3rd-party security audit (post-Tier 0, pre-mainnet)
- Enforce comprehensive integration tests in CI

#### 5. Success Metrics — Definitions and Remediation

| Metric | Target | Baseline | Measurement Method | Remediation (if missed) | Severity |
|---|---|---|---|---|---|
| **Mainnet Deployment** | Ship v0.3.0 with zero security regressions | N/A (first mainnet) | Post-audit; zero vulnerability reports in first month | Re-run audit if issues emerge | HIGH |
| **Liveness** | >99.9% uptime of RPC endpoints querying contract | N/A | Daily smoke test; alert if error rate >1% | Investigate RPC provider; switch if needed | MEDIUM |
| **Adoption** | ≥5 production alert configs on mainnet by end of Q1 | 0 (first mainnet) | Monitor via Soroban events or direct queries | Increase community outreach and documentation | LOW |
| **Query Latency** | p95 latency <3s for gated reads with <100 alerts | TBD (testnet baseline) | Synthetic monitoring from 3+ geographic regions | Optimize contract code; investigate RPC bottlenecks | MEDIUM |
| **Watcher Integration** | ≥2 active watcher nodes polling mainnet | 0 | Community feedback; monitor GitHub issues and Discord | Provide better documentation and SDK support | MEDIUM |
| **Zero Data Loss** | No alerts lost or corrupted | Depends on testnet | Transaction audit logs; daily state snapshots compared | Root-cause post-mortem; contract rollback if needed | HIGH |

**Weekly/Monthly Review Procedure:**

1. **Collect metrics** (automated dashboard or manual queries)
2. **Compare to targets** (flag if any metric misses target)
3. **Escalation thresholds:**
   - LOW: Document issue; fix in sprint planning
   - MEDIUM: Fix within 1 week; on-call rotation if blocking
   - HIGH: 4-hour on-call response; 24-hour root-cause; fix within 1 week
4. **Publish metrics** publicly on OverStand docs or GitHub
5. **Incident review** every Friday (if any escalations)

#### 5. Success Metrics---

## SECTION 2: TIER 1 HIGH-PRIORITY FEATURES (Target: 1–3 months post-mainnet)

### Overview

With security fixes deployed and mainnet live, Tier 1 features unlock extensibility, multi-language support, and ecosystem participation. These features position OverStand as the platform for decentralized event monitoring on Stellar.

---

### HIGH-002: Extensible Rule Descriptor Registry (RuleRegistry Contract)

#### Problem Statement

Currently, AlertRegistry supports only 5 hardcoded rule descriptors:

```rust
pub const VALID_RULE_DESCRIPTORS: [&str; 5] = [
    "rule:transfer",
    "rule:mint",
    "rule:burn",
    "rule:approve",
    "rule:clawback",
];
```

All are Stellar SEP-0041 (fungible token) events. To monitor:

- **NFT (SEP-0053)** events (mint, transfer, burn of NFTs)
- **Custom contract events** (e.g., governance proposals, liquidations)
- **Cross-protocol patterns** (e.g., atomic swaps, pool rebalancing)

...requires a new AlertRegistry contract version and a mainnet redeploy. This is unsustainable for a multi-year ecosystem platform.

**Impact:** OverStand cannot evolve beyond token transfers without disruptive contract upgrades.

#### Design: RuleRegistry Contract

**Architecture Diagram:**

```
┌─────────────────────────────────────────────────────────┐
│  Stellar Mainnet                                          │
├─────────────────────────────────────────────────────────┤
│  AlertRegistry (v0.3.0)                                   │
│    ├─ register_alert(owner, target, rules, webhook)    │
│    ├─ rules: Vec<String> → ["rule:transfer", ...]      │
│    └─ Validates rules against RuleRegistry               │
│       RuleRegistry::validate_rule("rule:custom:nft")    │
│                                                           │
│  RuleRegistry (v0.1.0) NEW                               │
│    ├─ register_rule(owner, id, descriptor, schema)      │
│    ├─ approve_rule(admin, id) — multi-sig or DAO        │
│    ├─ revoke_rule(admin, id)                            │
│    ├─ get_rule(rule_id) → RuleDescriptor                │
│    └─ Data: RuleId ↦ (name, schema, owner, approved)   │
│                                                           │
│  WatcherRegistry (v0.1.0)                                │
│    └─ [unchanged]                                        │
└─────────────────────────────────────────────────────────┘
```

#### Data Model

```rust
// In RuleRegistry contract

#[derive(Clone, Debug, PartialEq, Eq)]
#[contracttype]
pub enum RuleId {
    // Built-in descriptors (always approved)
    Builtin(String), // "rule:transfer", "rule:mint", etc.
    // User-registered descriptors
    Custom(String),  // "rule:custom:nft_transfer", "rule:custom:uniswap_swap", etc.
}

#[derive(Clone, Debug)]
#[contracttype]
pub struct RuleDescriptor {
    /// Human-readable rule name ("SEP-0041 Transfer", "NFT Mint", "Custom Liquidation")
    pub name: String,
    /// Semantic version (allows rule semantics to evolve)
    pub version: String,
    /// Address of the rule owner/maintainer (can propose updates)
    pub owner: Address,
    /// Approved for use by AlertRegistry (DAO or multi-sig decision)
    pub approved: bool,
    /// Last update timestamp (to track stale rules)
    pub updated_at: i64,
    /// Machine-readable schema: JSON or custom encoding (TBD)
    pub schema: Bytes,
}

// Storage Keys (in RuleRegistry)
enum DataKey {
    Rule(RuleId),           // RuleId ↦ RuleDescriptor
    BuiltinsApproved(i32),  // Version counter for builtin set
    OwnerRules(Address),    // Address ↦ Vec<RuleId> (custom rules owned by addr)
}
```

#### Authorization Model

Three roles:

1. **Rule Owner:** Registers a custom rule; can propose updates; must have signature
2. **Approver (Admin/DAO):** Decides which rules are safe for AlertRegistry to use
3. **Watcher/Observer:** Reads rule schema to implement matching

**Authorization Flows:**

| Function | Caller | Requirement | Success | Failure |
|---|---|---|---|---|
| `register_rule` | Any | No auth required; open registration | Rule created, marked `approved=false` | Max rules reached |
| `propose_rule_update` | Owner | `caller.require_auth()` and caller == rule.owner | Update staged, old rule still active | Unauthorized |
| `approve_rule` | Admin | `caller.require_auth()` and caller is admin | Rule marked `approved=true` | Unauthorized, rule not found |
| `revoke_rule` | Admin | `caller.require_auth()` and caller is admin | Rule marked `approved=false`; AlertRegistry reads see it as invalid | Unauthorized |
| `get_rule` | Any | None (read-only) | Return RuleDescriptor | Rule not found |
| `validate_rule` | Any | None (read-only) | Return true if rule is approved; false otherwise | None |

### Rule Approval Criteria (Governance Policy)

**For v0.3.0 (Single-Admin Approval):**

The designated admin reviews custom rule proposals and approves based on:

1. **Security:** Rule schema does not encode arbitrary code; rule validation is deterministic
2. **Clarity:** Rule descriptor and name are clear; watcher reference implementation exists
3. **Compatibility:** Rule does not conflict with existing descriptors; naming follows `rule:custom:*` pattern
4. **Community Consensus:** (Optional) Proposal was discussed publicly (GitHub RFC) for 5+ days; no major objections

**Approval Process:**

1. Rule owner submits via `register_rule(owner, rule_id, name, schema)`
2. Community comments on GitHub RFC (issue or discussion)
3. Admin reviews RFC and schema
4. Admin calls `approve_rule(rule_id)` or provides rejection feedback (off-chain)
5. If rejected, rule owner can update schema and resubmit via `propose_rule_update`

**For v0.4.0+ (Multi-Admin or DAO Governance):**

Approval transitions to multi-sig or DAO vote. Document this transition in `docs/governance.md`.

**Rejection Handling:**

- If admin rejects a rule, the owner may request detailed feedback (off-chain, via Discord/GitHub)
- Admin may suggest improvements; owner resubmits via `propose_rule_update`
- No appeal mechanism in v0.3.0; consider for v0.4.0+

**Rate Limiting (Future Enhancement):**

Consider adding per-owner rule submission limits in v0.4.0 to prevent spam.

### Schema Semantics and Watcher Consumption

**Schema Format (JSON):**

Each rule's schema is a JSON object describing the event structure and matching criteria.

**Example Schema (rule:custom:nft_transfer):**

```json
{
  "event_type": "nft_transfer",
  "version": "1.0",
  "fields": {
    "from": { "type": "address", "required": true },
    "to": { "type": "address", "required": true },
    "token_id": { "type": "string", "required": true },
    "contract": { "type": "address", "required": false }
  },
  "reference_implementation": "https://github.com/QingQosh/overstand-watchers/blob/main/rules/nft_transfer.rs",
  "examples": [
    {
      "from": "GXXX...",
      "to": "GYYY...",
      "token_id": "nft:1",
      "contract": "CZZZZ..."
    }
  ]
}
```

**Watcher Consumption Model:**

1. **At Startup:** Watcher fetches `RuleRegistry::get_rule(rule_id)` and caches the schema
2. **Rule Matching:** For each transaction, watcher deserializes Soroban events and matches against cached schemas
3. **Validation:** Watcher checks that event fields match schema types and required fields are present
4. **No Match:** If event doesn't match schema, rule doesn't fire
5. **Schema Updates:** Watcher refreshes schema every 24h or on manual force-refresh

**Failure Handling:**

- **Invalid JSON in schema:** Watcher logs error and skips the rule (non-fatal)
- **Missing reference implementation:** Watcher may warn but continue (reference is documentation, not code)
- **Schema version mismatch:** Watcher uses best-effort matching based on available fields

**Documentation Requirement:**

Every approved rule MUST have:
1. Clear `description` explaining what events it matches
2. `reference_implementation` URL pointing to watcher code
3. `examples` array with 2–3 sample events that match the rule

**Watcher Reference Implementation:**

The OverStand team will maintain example watcher implementations for each builtin rule in a public `overstand-watchers` repository. Ecosystem contributors should provide reference implementations when submitting custom rules.

### Rule Version Management

**Versioning Scheme:**

Rules use semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR:** Breaking change to schema semantics (e.g., field renamed or removed); watchers MUST be updated
- **MINOR:** Backward-compatible addition (e.g., new optional field); old watchers still work
- **PATCH:** Documentation or example update; no schema change

**Auto-Bump on Update:**

When `propose_rule_update` is called with a new schema:
- If new fields are added: bump MINOR version
- If existing fields are changed/removed: bump MAJOR version
- If only docs/examples change: bump PATCH version

**Watcher Compatibility Matrix:**

| Watcher Version | Rule v1.0 | Rule v2.0 (MINOR update) | Rule v3.0 (MAJOR update) |
|---|---|---|---|
| Watcher supporting v1.0 | ✅ Works | ✅ Works (ignores new fields) | ❌ Fails or uses wrong logic |
| Watcher supporting v2.0 | ⚠️ May not handle new fields | ✅ Works | ❌ Fails |
| Watcher supporting v3.0 | ❌ Fails | ❌ Fails | ✅ Works |

**Rule Deprecation (v0.5.0+):**

Plan to deprecate old rules with notice period:
1. Mark rule as `deprecated=true` (new field in RuleDescriptor)
2. AlertRegistry still accepts it; existing alerts continue working
3. New alert registrations cannot use deprecated rules (validation rejects them)
4. After 30 days, admin can permanently revoke (calls `revoke_rule()`)

#### Rule Semantic Design Patterns

**Rule Naming Convention:**

- **Built-in rules:** `rule:<descriptor>` (e.g., `rule:transfer`, `rule:mint`)
- **Custom rules:** `rule:custom:<descriptor>` (e.g., `rule:custom:nft_transfer`)
- **SEP patterns:** `rule:sep<number>:<descriptor>` (future; e.g., `rule:sep0053:mint`)
- **Protocol patterns:** `rule:protocol:<name>` (e.g., `rule:protocol:soroban_deploy`)

**Reserved Prefixes:**

Do not use these prefixes for new custom rules:
- `sep0041:*`, `sep0053:*` — Reserved for official SEP standards
- `soroban:*` — Reserved for Soroban protocol events
- `protocol:*` — Reserved for Stellar protocol events

**Global Uniqueness Constraint:**

Every rule ID must be globally unique. Violations are caught during registration:
```rust
pub fn register_rule(..., rule_id: String, ...) {
    if get_rule(&rule_id).is_some() {
        panic_with_error!(env, ContractError::RuleAlreadyExists);
    }
    // ... proceed
}
```

**Multiple Rules Per Alert (OR Logic):**

When an alert has multiple rules: `rules: ["rule:transfer", "rule:mint"]`
- Rule matching uses **OR** logic: **Any** rule firing triggers the alert
- Example: Alert fires if EITHER a transfer OR a mint event is detected
- All rules must be validated during registration (fail if any rule is invalid)

**Event Matching Semantics:**

For a single rule with complex schema:
- Schema fields are AND'd together: **All** required fields must match
- Optional fields can be omitted
- Example: `rule:custom:nft_transfer` matches events with:
  - `from` address AND `to` address AND `token_id` (required)
  - Optional: `contract` address

**Upgrade Path from v0.3.0**

**Timeline:**

1. **Deploy RuleRegistry to testnet** (1 week development + 1 week testing)
2. **Integrate AlertRegistry with RuleRegistry** (1 week)
3. **Community Rule Submissions** (2 weeks; collect NFT, custom contract examples)
4. **Integration Tests on Testnet** (1 week)
5. **Security Audit** (2–4 weeks, 3rd party)
6. **Deploy to Mainnet as v0.4.0** (post-audit)

**Data Migration:**

- No migration needed; RuleRegistry is additive
- AlertRegistry can operate with or without RuleRegistry configured
- Existing alerts on mainnet continue to work
- New alerts can use builtin rules (unchanged) or custom rules (if RuleRegistry enabled)

### Rollout Timeline and Watcher Upgrade Requirements

**Phase 1: AlertRegistry v0.3.0 (Mainnet, without RuleRegistry)**

- AlertRegistry launches with hardcoded VALID_RULE_DESCRIPTORS (transfer/mint/burn/approve/clawback)
- RuleRegistry is NOT deployed or optional (if deployed, custom rules are rejected)
- Watchers continue using existing rule matching logic
- Timeline: Mainnet launch (Week 1–2)

**Phase 2: RuleRegistry Deployment and Integration (v0.4.0, Mainnet)**

- RuleRegistry deployed to mainnet
- AlertRegistry updated to call RuleRegistry::validate_rule for custom rule validation
- New custom rules submitted via RuleRegistry (e.g., NFT transfers, liquidations)
- Watchers updated to support new rule types (e.g., `rule:custom:nft_transfer`)
- Timeline: 4–6 weeks post-mainnet launch (to allow watcher dev time)

**Watcher Compatibility Matrix:**

| Watcher Version | AlertRegistry v0.3.0 | AlertRegistry v0.4.0 (w/ RuleRegistry) |
|---|---|---|
| v1.0 (builtin rules only) | ✅ Works | ⚠️ Works but can't match custom rules |
| v1.1 (custom rule support) | ✅ Works | ✅ Works; matches builtin + custom rules |

**Watcher Upgrade Path:**

Watcher operators MUST update to v1.1 before new custom rules are approved. Recommended timeline: Update during 2-week pre-launch window (Phase 2 preparation).

**Breaking Changes Between Versions:**

- **v0.3.0 → v0.4.0:** `register_alert` adds cross-contract call to RuleRegistry
  - If RuleRegistry is unavailable, custom rule validation fails
  - Builtin rules always work (fallback)
  - Watchers without custom rule support continue to function

#### Authorization Model

Three roles:

1. **Rule Owner:** Registers a custom rule; can propose updates; must have signature
2. **Approver (Admin/DAO):** Decides which rules are safe for AlertRegistry to use
3. **Watcher/Observer:** Reads rule schema to implement matching

**Authorization Flows:**

| Function | Caller | Requirement | Success | Failure |
|---|---|---|---|---|
| `register_rule` | Any | No auth required; open registration | Rule created, marked `approved=false` | Max rules reached |
| `propose_rule_update` | Owner | `caller.require_auth()` and caller == rule.owner | Update staged, old rule still active | Unauthorized |
| `approve_rule` | Admin | `caller.require_auth()` and caller is admin | Rule marked `approved=true` | Unauthorized, rule not found |
| `revoke_rule` | Admin | `caller.require_auth()` and caller is admin | Rule marked `approved=false`; AlertRegistry reads see it as invalid | Unauthorized |
| `get_rule` | Any | None (read-only) | Return RuleDescriptor | Rule not found |
| `validate_rule` | Any | None (read-only) | Return true if rule is approved; false otherwise | None |

**Governance Pattern (Recommended for Mainnet):**

- **Bootstrap:** Hardcoded builtin rules (transfer, mint, burn, approve, clawback) are pre-approved
- **Custom Rules:** Open registration (anyone can propose), but only approved rules are usable in AlertRegistry
#### Approval Mechanism (v0.3.0)

**DECISION: Single-admin approval with future governance upgrade path.**

Rationale:
- v0.3.0 launches with minimal governance overhead (single trusted admin)
- Approval is deterministic: admin calls `approve_rule(rule_id)`, rule is immediately usable
- Governance upgrade path: v0.4.0 or later can transition to multi-sig or DAO (out of scope for this upgrade)

**Approval Flow:**

1. **Proposal:** Any caller calls `register_rule(owner, rule_id, name, schema)` → rule is created but marked `approved=false`
   - No auth required; open registration
   - Rule is stored but AlertRegistry rejects it during validation

2. **Review Period:** Off-chain community (GitHub RFC) reviews rule semantics (5-7 days)
   - Community members propose test vectors and edge cases
   - RFC author (rule owner) iterates on schema/semantics
   - Core team decides: approve or request changes

3. **Approval:** Admin (single address, hardcoded or configurable) calls `approve_rule(rule_id)` with `admin.require_auth()`
   - Admin authenticates; rule marked `approved=true`
   - AlertRegistry can now validate alerts using this rule

4. **Revocation:** Admin can revoke approval with `revoke_rule(rule_id)` → `approved=false`
   - Existing alerts using the rule are unaffected (backward-compatible)
   - New alert registrations cannot use the rule (rejected during validation)

**Error Handling:**

| Scenario | Error Code | Behavior |
|---|---|---|
| Register duplicate rule ID | `RuleAlreadyExists` | Panic; prevent re-registration |
| Propose update on non-existent rule | `RuleNotFound` | Panic |
| Approve non-existent rule | `RuleNotFound` | Panic |
| Non-admin attempts approval | `Unauthorized` | Panic; only admin can approve |
| Register rule with invalid schema | `InvalidSchema` | Panic; schema must be valid JSON |

**Cross-Contract Call Failures (AlertRegistry → RuleRegistry):**

If AlertRegistry is configured with a RuleRegistry address but the cross-contract call fails:

```rust
pub fn validate_rule(env: &Env, rule: &String) -> Result<(), ContractError> {
    // Check hardcoded builtins first (fast path)
    if VALID_RULE_DESCRIPTORS.contains(&rule.as_str()) {
        return Ok(());
    }
    
    // If RuleRegistry is configured, query it
    if let Some(registry) = get_rule_registry(&env) {
        // Cross-contract call; may fail for several reasons
        match registry.validate_rule(&rule) {
            Ok(is_valid) => {
                if is_valid {
                    return Ok(());
                } else {
                    return Err(ContractError::InvalidRuleDescriptor);
                }
            }
            Err(e) => {
                // RuleRegistry call failed (network, contract panic, etc.)
                // Decision: Fail-closed (reject rule) or fail-open (accept rule)?
                // Recommendation: Fail-closed (security-by-default)
                return Err(ContractError::ExternalRegistryError);
            }
        }
    }
    
    // No registry configured; only builtins are valid
    Err(ContractError::InvalidRuleDescriptor)
}
```

**Future Upgrade (v0.4.0+):**
- Add `propose_approval(rule_id)` and multi-admin voting (out of scope for v0.3.0)
- Document transition path in docs/governance.md

#### Error Handling and Validation

**Schema Validation:**

Rules can be registered with custom schemas. The schema format must be JSON for interoperability with SDKs.

| Decision | Pros | Cons | Recommendation |
|---|---|---|---|
| **No validation** — Accept any `Bytes` | Flexible; watchers validate locally | Unclear format; SDK code generation difficult | Not recommended |
| **JSON Schema format** — Require valid JSON object | Standard; widely tooled; clear semantics | Slightly larger storage; requires JSON parsing | Recommended |
| **Custom binary format** — Require specific byte structure | Compact storage | Non-standard; harder to debug | Not recommended |

**Recommendation:** Require JSON format. Validation pseudocode:

```rust
fn validate_schema(schema: &Bytes) -> Result<(), ContractError> {
    // Attempt to parse as JSON
    let json_str = String::from_slice(env, schema)?;
    if serde_json::from_str::<serde_json::Value>(&json_str).is_ok() {
        Ok(())
    } else {
        Err(ContractError::InvalidSchema)
    }
}
```

**Error Codes (RuleRegistry and AlertRegistry):**

| Error Code | Component | Scenario | Panic Text |
|---|---|---|---|
| `RuleAlreadyExists` | RuleRegistry | `register_rule` called with duplicate rule_id | "Rule with this ID already registered" |
| `RuleNotFound` | RuleRegistry | `propose_rule_update`, `approve_rule`, `revoke_rule`, `get_rule` called with non-existent rule_id | "Rule not found" |
| `Unauthorized` | RuleRegistry | Non-admin attempts `approve_rule`, `revoke_rule` | "Only admin can approve rules" |
| `InvalidSchema` | RuleRegistry | `register_rule` called with non-JSON schema | "Schema must be valid JSON" |
| `ExternalRegistryError` | AlertRegistry | Cross-contract call to RuleRegistry failed | "External rule registry call failed" |
| `InvalidRuleDescriptor` | AlertRegistry | Rule is not recognized (builtin or approved custom) | "Rule descriptor not recognized" |

**Instance Storage (unique keys):**

```
enum DataKey {
    Admin,                  // Single admin address (1 entry)
    BuiltinRuleVersion,     // Version counter for builtins (1 entry)
}
```

**Persistent Storage (variable size):**

```
DataKey::Rule(rule_id)              // One entry per custom rule
DataKey::OwnerRules(address)        // One entry per rule owner
```

**Estimated Costs:**

- Builtin rule set (5 rules): 1.5 KB on instance storage (cached, cheap)
- Per custom rule: ~500 bytes (name + schema + metadata)
- Per rule owner: 32 bytes × rule_count (address index)

**Storage Budget:** Conservative budget allows ~100 custom rules without hitting Soroban state limits. If exceeded, prune deprecated rules (marked `approved=false` for 30 days).

#### Cross-Contract Integration with AlertRegistry

**AlertRegistry Changes:**

1. **New Configuration:**
   - `set_rule_registry(rule_registry_address)` — admin configures which RuleRegistry to use
   - Optional; if unset, uses hardcoded builtins only

2. **New Validation:**

```rust
pub fn validate_rule(env: Env, rule: String) -> bool {
    // Check hardcoded builtins first (fast path)
    if VALID_RULE_DESCRIPTORS.contains(&rule.as_str()) {
        return true;
    }
    
    // If RuleRegistry is configured, query it
    if let Some(registry) = get_rule_registry(&env) {
        return registry.validate_rule(&rule);
    }
    
    // No registry configured; only builtins are valid
    false
}

pub fn register_alert(
    env: Env,
    owner: Address,
    target_contract: Address,
    label: String,
    webhook_hash: BytesN<32>,
    rules: Vec<String>,
) -> u64 {
    owner.require_auth();
    
    // Validate each rule
    for rule in &rules {
        if !validate_rule(&env, rule.clone()) {
            panic_with_error!(env, ContractError::InvalidRule);
        }
    }
    
    // ... rest of register_alert logic
}
```

3. **ABI-Breaking Change:**
   - `set_rule_registry` is a new admin function
   - `validate_rule` is a new public read function
   - `register_alert` logic changes (now calls external registry)
   - **Backward Compatibility:** If no RuleRegistry is set, behavior is identical to v0.3.0

#### File Structure

```
contracts/
├── alert-registry/                 (unchanged, except new validate_rule call)
│   └── src/lib.rs
├── watcher-registry/               (unchanged)
│   └── src/lib.rs
└── rule-registry/                  (NEW)
    ├── src/
    │   ├── lib.rs                 (contract entry point)
    │   ├── types.rs               (RuleId, RuleDescriptor, etc.)
    │   ├── storage.rs             (DataKey enum)
    │   ├── errors.rs              (RuleRegistry errors)
    │   └── tests.rs               (unit tests)
    ├── Cargo.toml                 (new workspace member)
    └── README.md
```

#### Interface Sketch

```rust
// Entry points

#[contractimpl]
impl RuleRegistry {
    /// Initialize RuleRegistry with admin and builtin rules pre-approved
    pub fn initialize(env: Env, admin: Address) { }
    
    /// Register a new custom rule descriptor (open; not auto-approved)
    pub fn register_rule(
        env: Env,
        owner: Address,
        rule_id: String,  // "rule:custom:nft_transfer"
        name: String,     // "SEP-0053 NFT Transfer"
        schema: Bytes,    // JSON or custom encoding of expected event fields
    ) -> bool { } // true if registered; false if already exists
    
    /// Propose an update to a rule (owner-only)
    pub fn propose_rule_update(
        env: Env,
        owner: Address,
        rule_id: String,
        new_schema: Bytes,
    ) { }
    
    /// Approve a rule (admin-only; makes it usable in AlertRegistry)
    pub fn approve_rule(env: Env, admin: Address, rule_id: String) { }
    
    /// Revoke approval from a rule (admin-only)
    pub fn revoke_rule(env: Env, admin: Address, rule_id: String) { }
    
    /// Query rule descriptor by ID (read-only)
    pub fn get_rule(env: Env, rule_id: String) -> RuleDescriptor { }
    
    /// Check if a rule is registered and approved (read-only)
    pub fn validate_rule(env: Env, rule_id: String) -> bool { }
    
    /// List all approved custom rules (read-only, paginated)
    pub fn list_rules(env: Env, offset: u32, limit: u32) -> Vec<(String, RuleDescriptor)> { }
    
    /// Transfer admin role (2-phase: propose + accept)
    pub fn propose_admin_transfer(env: Env, admin: Address, new_admin: Address) { }
    pub fn accept_admin_transfer(env: Env, new_admin: Address) { }
}
```

#### Upgrade Path from v0.3.0

**Timeline:**

1. **Deploy RuleRegistry to testnet** (1 week development + 1 week testing)
2. **Integrate AlertRegistry with RuleRegistry** (1 week)
3. **Community Rule Submissions** (2 weeks; collect NFT, custom contract examples)
4. **Integration Tests on Testnet** (1 week)
5. **Security Audit** (2–4 weeks, 3rd party)
6. **Deploy to Mainnet as v0.4.0** (post-audit)

**Data Migration:**

- No migration needed; RuleRegistry is additive
- AlertRegistry can operate with or without RuleRegistry configured
- Existing alerts on mainnet continue to work
- New alerts can use builtin rules (unchanged) or custom rules (if RuleRegistry enabled)

#### Testing Strategy

- **Unit Tests:** Each function validated independently with mock data
- **Integration Tests:** AlertRegistry + RuleRegistry together; rule validation chain
- **Property Tests:** Rule registry consistency (no orphaned references)
- **Fuzz Tests:** Custom rule schema parsing (if schema format is complex)

---

### HIGH-003: Python and Go SDKs

#### Problem Statement

TypeScript bindings exist and are published to npm. No official Python, Go, Rust, or Kotlin SDKs; developers on these platforms must hand-craft calls or use generic Soroban tools.

**Impact:** Platform barriers; adoption concentrated in JavaScript ecosystem.

#### Design: Multi-Language SDK Generation and Maintenance

**Architecture:**

```
Soroban Contracts (WASM)
    ↓ (stellar contract bindings <lang>)
XDR Specs / ABI JSON
    ↓ (custom codegen scripts)
Language-Specific SDKs
    ├─ Python: overstand-py (PyPI)
    ├─ Go: overstand-go (pkg.go.dev)
    ├─ Rust: overstand-rs (crates.io) [later]
    └─ Kotlin: overstand-kt (Maven) [later]
```

**Source of Truth:**

Stellar CLI's `stellar contract bindings <lang>` generates language-specific code from compiled WASM. These are the single source of truth for ABI correctness.

**Toolchain:**

1. **Generated Code:** `stellar contract bindings typescript/python/go` produces base client
2. **Custom Wrapper:** Hand-write async helpers, error handling, type refinements (not generated)
3. **CI Integration:** Regenerate on every contract version bump; compare against golden file to detect ABI drift
4. **Publishing:** Auto-publish to PyPI (Python) and pkg.go.dev (Go) on GitHub release

#### Python SDK: `overstand-py`

**Structure:**

```
sdks/python/
├── overstand/
│   ├── __init__.py
│   ├── client.py                # Main AsyncClient wrapper
│   ├── types.py                 # Dataclass definitions (generated, then extended)
│   ├── errors.py                # SDK-level error handling
│   ├── networks.py              # Testnet/Mainnet configuration
│   └── _generated/
│       ├── __init__.py
│       └── alert_registry.py    # Auto-generated from stellar CLI
├── tests/
│   ├── test_client.py           # Integration tests with testnet
│   ├── test_types.py            # Type serialization
│   └── test_errors.py
├── pyproject.toml               # Poetry or setuptools config
├── README.md
└── CHANGELOG.md
```

**Key Modules:**

| Module | Responsibility | Example |
|---|---|---|
| `client.py` | AsyncClient wrapping Stellar SDK; retry logic; rate limiting | `async def get_alert(config_id: int) -> AlertConfig` |
| `types.py` | Type definitions; serialization/deserialization of Soroban data | `@dataclass class AlertConfig: rules: List[str]` |
| `errors.py` | Error decoding from Soroban; custom exception hierarchy | `raise OverStandError("Rule validation failed")` |
| `networks.py` | Configuration for testnet/mainnet | `testnet = Network(rpc_url="https://soroban-testnet.stellar.org", ...)` |

### Python SDK: Error Type Hierarchy

```python
class OverStandError(Exception):
    """Base exception for all OverStand SDK errors."""
    pass

class ContractError(OverStandError):
    """Error returned by on-chain contract."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
    def __str__(self):
        return f"Contract Error {self.code}: {self.message}"

class NotAWatcher(ContractError):
    """Querier is not an authorized watcher."""
    pass

class InvalidRuleDescriptor(ContractError):
    """Rule descriptor is not recognized."""
    pass

class AlertLimitExceeded(ContractError):
    """Owner or contract alert limit exceeded."""
    pass

class NetworkError(OverStandError):
    """Network or RPC error."""
    pass

class AuthenticationError(OverStandError):
    """Caller signature invalid or missing."""
    pass
```

### Type Mapping: Python

| Rust / Soroban | Python | Notes |
|---|---|---|
| `Address` | `str` | Stellar public key (e.g., "GXXX...") |
| `BytesN<32>` | `bytes` | Fixed 32-byte hash |
| `Vec<u64>` | `list[int]` | Dynamic list |
| `String` | `str` | UTF-8 string |
| `Option<T>` | `Optional[T]` | None or value |
| `AlertConfig` (struct) | `AlertConfig` (dataclass) | Auto-generated from contract |

### Transaction Building (Python Example)

```python
import asyncio
from stellar_sdk import (
    Keypair, TransactionBuilder, Server, Network as StellarNetwork,
)
from overstand import AsyncClient, networks

async def register_alert_example():
    # Keypair for transaction signing
    owner_keypair = Keypair.random()
    owner_address = owner_keypair.public_key
    
    # Stellar account
    server = Server(networks.testnet.rpc_url)
    account = await server.get_account(owner_address)
    
    # Build transaction (handled by SDK in async context)
    client = AsyncClient(
        contract_id="CXXX...",
        network=networks.testnet,
    )
    
    # SDK builds the transaction internally, caller signs
    alert_id = await client.register_alert(
        owner=owner_address,
        target_contract="CXXX...",
        label="My Alert",
        webhook_hash=bytes.fromhex("abc123..."),
        rules=["rule:transfer"],
        # Signer passed separately (keypair used to sign TX)
        signer_keypair=owner_keypair,
    )
    print(f"Registered alert {alert_id}")
```

**Key Modules:**

| Module | Responsibility | Example |
|---|---|---|
| `client.py` | AsyncClient wrapping Stellar SDK; retry logic; rate limiting | `async def get_alert(config_id: int) -> AlertConfig` |
| `types.py` | Type definitions; serialization/deserialization of Soroban data | `@dataclass class AlertConfig: rules: List[str]` |
| `errors.py` | Error decoding from Soroban; custom exception hierarchy | `raise OverStandError("Rule validation failed")` |
| `networks.py` | Configuration for testnet/mainnet | `testnet = Network(rpc_url="https://soroban-testnet.stellar.org", ...)` |

**API Design:**

```python
# Async usage
import asyncio
from overstand import AsyncClient, networks, AlertConfig

async def main():
    client = AsyncClient(
        contract_id="CXXX...",
        network=networks.testnet,
    )
    
    # Query a single alert
    alert = await client.get_alert(querier_address, config_id=1)
    print(alert.rules)  # ["rule:transfer", "rule:mint"]
    
    # Register a new alert
    alert_id = await client.register_alert(
        owner=owner_address,
        target_contract=target_address,
        label="My Alert",
        webhook_hash=webhook_hash_bytes,
        rules=["rule:transfer"],
    )
    print(f"Registered alert {alert_id}")
    
    # Paginated query
    alerts = await client.get_alerts_by_owner_paginated(
        querier=querier_address,
        owner=owner_address,
        offset=0,
        limit=10,
    )
    for alert_id, alert_config in alerts:
        print(f"Alert {alert_id}: {alert_config.label}")

asyncio.run(main())
```

**Dependencies:**

- `stellar-sdk>=12.0.0` (Stellar Python SDK for account management, TX building)
- `stellar-base` (for XDR serialization, re-exported by stellar-sdk)
- `pydantic>=2.0` (optional, for validation if we enhance types)
- `httpx>=0.25.0` (async HTTP client for Soroban RPC)

**Publishing:**

- Package name: `overstand-py`
- PyPI: https://pypi.org/project/overstand-py/
- Documentation: ReadTheDocs with Sphinx
- Version: Track contract version; semver'd (e.g., `0.3.0.post1` for SDK-only patch)

#### Go SDK: `overstand-go`

**Structure:**

```
sdks/go/
├── client.go              # Main client wrapper
├── types.go               # Type definitions (generated, then extended)
├── errors.go              # Error handling
├── networks.go            # Testnet/Mainnet configuration
├── *_generated.go         # Auto-generated from stellar CLI
├── internal/
│   ├── rpc/               # Low-level RPC client (generated)
│   └── types/
├── examples/
│   ├── register_alert/main.go
│   └── query_alerts/main.go
├── go.mod                 # Module definition
├── go.sum
├── README.md
├── CHANGELOG.md
└── [CI workflows: go test, go lint, etc.]
```

**Key Packages:**

| Package | Responsibility | Example |
|---|---|---|
| `Client` | Main entry point; wraps SorobanRpc; async (Go goroutines) | `client.GetAlert(ctx, querierAddr, configID)` |
| `types` | Type definitions; struct marshaling | `type AlertConfig struct { Rules []string }` |
| `errors` | Error types from contract | `type ContractError struct { Code uint32 }` |
| `networks` | Configuration | `var Testnet = &Network{RpcURL: "..."}` |

### Type Mapping: Go

| Rust / Soroban | Go | Notes |
|---|---|---|
| `Address` | `string` | Stellar public key |
| `BytesN<32>` | `[32]byte` | Fixed 32-byte array |
| `Vec<u64>` | `[]uint64` | Slice |
| `String` | `string` | UTF-8 |
| `Option<T>` | `*T` | Pointer (nil if empty) |
| `AlertConfig` | `struct AlertConfig` | Auto-generated |

### Transaction Building (Go Example)

```go
import (
    "context"
    "github.com/stellar/go/clients/horizonclient"
    "github.com/stellar/go/keypair"
    "github.com/QingQosh/overstand-go"
)

func registerAlertExample(ctx context.Context) {
    ownerKeypair, _ := keypair.FromSeed("SXXX...")
    ownerAddr := ownerKeypair.Address()
    
    hClient := &horizonclient.Client{}
    account, _ := hClient.AccountDetail(horizonclient.AccountRequest{
        AccountID: ownerAddr,
    })
    
    client := overstand.NewClient("CXXX...", overstand.Testnet)
    
    alertID, err := client.RegisterAlert(ctx, &overstand.RegisterAlertRequest{
        Owner:           ownerAddr,
        TargetContract:  "CXXX...",
        Label:           "My Alert",
        WebhookHash:     webhookHashBytes,
        Rules:           []string{"rule:transfer"},
        SignerKeypair:   ownerKeypair, // SDK uses this to sign TX
    })
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Registered alert %d\n", alertID)
}
```

**Key Packages:**

| Package | Responsibility | Example |
|---|---|---|
| `Client` | Main entry point; wraps SorobanRpc; async (Go goroutines) | `client.GetAlert(ctx, querierAddr, configID)` |
| `types` | Type definitions; struct marshaling | `type AlertConfig struct { Rules []string }` |
| `errors` | Error types from contract | `type ContractError struct { Code uint32 }` |
| `networks` | Configuration | `var Testnet = &Network{RpcURL: "..."}` |

**API Design:**

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    "github.com/QingQosh/overstand-go"
)

func main() {
    ctx := context.Background()
    
    client := overstand.NewClient(
        "CXXX...",
        overstand.Testnet,
    )
    
    // Query a single alert
    alert, err := client.GetAlert(ctx, querierAddr, 1)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Alert rules: %v\n", alert.Rules)
    
    // Register a new alert
    alertID, err := client.RegisterAlert(ctx, &overstand.RegisterAlertRequest{
        Owner:          ownerAddr,
        TargetContract: targetAddr,
        Label:          "My Alert",
        WebhookHash:    webhookHashBytes,
        Rules:          []string{"rule:transfer"},
    })
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Registered alert %d\n", alertID)
    
    // Paginated query
    alerts, err := client.GetAlertsByOwnerPaginated(ctx, &overstand.PageRequest{
        Querier: querierAddr,
        Owner:   ownerAddr,
        Offset:  0,
        Limit:   10,
    })
    if err != nil {
        log.Fatal(err)
    }
    for _, alert := range alerts {
        fmt.Printf("Alert %d: %s\n", alert.ID, alert.Config.Label)
    }
}
```

**Dependencies:**

- `github.com/stellar/go/clients/horizonclient` (Stellar Go SDK)
- `github.com/stellar/go/support/errors`
- Built-in context (stdlib) for cancellation/timeouts

**Publishing:**

- Module name: `github.com/QingQosh/overstand-go`
- pkg.go.dev: Auto-indexed from GitHub
- Versioning: Git tags matching contract versions (e.g., `v0.3.0`)

#### Retry and Timeout Strategy

**Python SDK (`AsyncClient`):**

```python
class AsyncClient:
    def __init__(
        self,
        contract_id: str,
        network: Network,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ):
        self.contract_id = contract_id
        self.network = network
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    async def _call_with_retry(self, coro):
        """Execute RPC call with exponential backoff retry."""
        for attempt in range(self.max_retries):
            try:
                async with asyncio.timeout(self.timeout):
                    return await coro
            except (asyncio.TimeoutError, httpx.TimeoutException) as e:
                if attempt == self.max_retries - 1:
                    raise OverStandError(f"Timeout after {self.max_retries} retries") from e
                wait_time = self.backoff_factor ** attempt
                await asyncio.sleep(wait_time)
            except httpx.ConnectError as e:
                if attempt == self.max_retries - 1:
                    raise OverStandError("Connection failed after retries") from e
                wait_time = self.backoff_factor ** attempt
                await asyncio.sleep(wait_time)
```

**Go SDK:**

```go
type ClientConfig struct {
    ContractID   string
    Network      *Network
    TimeoutSecs  int  // Default: 10
    MaxRetries   int  // Default: 3
    BackoffBase  float64 // Default: 1.5
}

func (c *Client) callWithRetry(ctx context.Context, fn func() error) error {
    for attempt := 0; attempt < c.maxRetries; attempt++ {
        // Add timeout to context
        ctxWithTimeout, cancel := context.WithTimeout(ctx, time.Duration(c.timeoutSecs)*time.Second)
        err := fn()
        cancel()
        
        if err == nil {
            return nil
        }
        
        // Check if error is retryable
        if !isRetryableError(err) {
            return err
        }
        
        if attempt < c.maxRetries-1 {
            backoff := math.Pow(c.backoffBase, float64(attempt))
            time.Sleep(time.Duration(backoff*1000) * time.Millisecond)
        }
    }
    return fmt.Errorf("failed after %d retries", c.maxRetries)
}
```

**SDK Documentation:**

Add to SDK READMEs (Python and Go):

```markdown
## Timeout and Retry Configuration

By default, the SDK retries failed RPC calls up to 3 times with exponential backoff (1.5x multiplier):
- Attempt 1: immediate
- Attempt 2: 1.5s delay
- Attempt 3: 2.25s delay
- Attempt 4: 3.375s delay

### Python Configuration
\`\`\`python
client = AsyncClient(
    contract_id="CXXX...",
    network=networks.testnet,
    timeout_seconds=5.0,  # 5s timeout per request
    max_retries=5,        # Retry up to 5 times
    backoff_factor=2.0,   # 2x backoff multiplier
)
\`\`\`

### Go Configuration
\`\`\`go
client := overstand.NewClientWithConfig(&overstand.ClientConfig{
    ContractID:  "CXXX...",
    Network:     overstand.Testnet,
    TimeoutSecs: 5,
    MaxRetries:  5,
    BackoffBase: 2.0,
})
\`\`\`

**Retryable Errors:**
- Connection timeout
- RPC endpoint unavailable (5xx error)
- Transaction pool full (temporary)

**Non-Retryable Errors (fail immediately):**
- Invalid contract address
- Authorization failure (caller not authenticated)
- Invalid rule descriptor
- Business logic errors (alert limit exceeded, etc.)
```

### TypeScript Bindings Update Workflow

**Automatic Regeneration (CI/CD):**

1. **On Contract WASM Change:**
   - `.github/workflows/regenerate-bindings.yml` detects WASM changes
   - Runs: `stellar contract bindings typescript --wasm contracts/.../alert_registry.wasm --output-dir bindings/alert-registry/src/_generated`
   - Auto-generated code committed to `bindings/alert-registry/src/_generated/`

2. **Manual Index Update:**
   - `bindings/alert-registry/src/index.ts` is hand-maintained (not auto-generated)
   - Re-export all types from `_generated/`
   - Add `networks` map (testnet/mainnet addresses)
   - Update JSDoc for breaking changes

3. **Version Bump:**
   - Bindings package version MUST match contract version
   - v0.3.0 contracts → `@QingQosh/alert-registry-bindings@0.3.0`
   - Enforced in CI: if contract bumps to v0.3.0, npm publish fails until bindings match

**Breaking Change Notification:**

All breaking changes (new querier parameter, new functions) must be documented:

- `bindings/alert-registry/CHANGELOG.md` entry (what changed in bindings)
- `bindings/alert-registry/package.json` has BREAKING CHANGES section in release notes
- npm publishes as `@version@0.3.0` with semver major bump if ABI breaking

**TypeScript Users Impact:**

```typescript
// v0.2.0 (old)
const alerts = client.getAlertsForContract(target, { offset: 0, limit: 10 });

// v0.3.0 (new) — querier parameter required
const alerts = client.getAlertsForContract(querier, target, { offset: 0, limit: 10 });
```

**Migration Guide in TypeScript Bindings README:**

```markdown
## Breaking Changes in v0.3.0

### Gated Read Functions Now Require Querier Authentication

All read functions that accept a `querier` parameter now require the querier to sign the transaction.

**Before (v0.2.0):**
\`\`\`typescript
const alert = await contract.get_alert({
  querier: Address.fromString("GXXX..."),
  config_id: 1,
});
\`\`\`

**After (v0.3.0):**
\`\`\`typescript
// Querier must sign the transaction
const querier = Address.fromString(await keypair.getPublicKey());
const alert = await contract.get_alert({
  querier,
  config_id: 1,
}, keyPair); // keyPair signs the transaction
\`\`\`

### Incremental Sync Now Requires Querier

\`\`\`typescript
// v0.2.0 (old) — no querier
const alerts = await contract.get_alerts_modified_since(since, offset, limit);

// v0.3.0 (new) — querier required
const alerts = await contract.get_alerts_modified_since(querier, since, offset, limit);
\`\`\`
```

#### CI/CD Integration

**Regeneration on ABI Change:**

```yaml
# .github/workflows/regenerate-sdks.yml
name: Regenerate SDKs on ABI Change

on:
  push:
    paths:
      - "contracts/alert-registry/src/**"
      - "contracts/watcher-registry/src/**"

jobs:
  regenerate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build WASM
        run: cargo build --release --target wasm32-unknown-unknown
      
      - name: Generate TypeScript bindings
        run: |
          stellar contract bindings typescript \
            --wasm contracts/alert-registry/target/wasm32-unknown-unknown/release/alert_registry.wasm \
            --output-dir bindings/alert-registry/src/_generated
      
      - name: Generate Python bindings
        run: |
          stellar contract bindings python \
            --wasm contracts/alert-registry/target/wasm32-unknown-unknown/release/alert_registry.wasm \
            --output-dir sdks/python/overstand/_generated
      
      - name: Generate Go bindings
        run: |
          stellar contract bindings go \
            --wasm contracts/alert-registry/target/wasm32-unknown-unknown/release/alert_registry.wasm \
            --package-name overstand \
            --output-dir sdks/go
      
      - name: Compare against golden file (detect ABI drift)
        run: |
          if ! diff -r sdks/python/overstand/_generated sdks/python/overstand/_generated.golden; then
            echo "ERROR: Python ABI changed unexpectedly"
            exit 1
          fi
      
      - name: Run SDK tests
        run: |
          cd sdks/python && python -m pytest tests/
          cd ../go && go test ./...
      
      - name: Commit and push (if changes)
        run: |
          git config user.name "CI"
          git config user.email "ci@overstand.dev"
          git add sdks/
          git commit -m "Regenerate SDKs" || true
          git push
```

**Publishing to Package Registries:**

```yaml
# .github/workflows/publish-sdks.yml
name: Publish SDKs

on:
  release:
    types: [published]

jobs:
  publish-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Build and publish to PyPI
        run: |
          cd sdks/python
          pip install poetry
          poetry version ${{ github.event.release.tag_name }}
          poetry publish --build --username __token__ --password ${{ secrets.PYPI_TOKEN }}
  
  publish-go:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}
      
      - name: Tag Go module
        run: |
          git tag -a sdks/go/${{ github.event.release.tag_name }} \
            -m "Go SDK ${{ github.event.release.tag_name }}"
          git push origin sdks/go/${{ github.event.release.tag_name }}
      
      - name: Trigger pkg.go.dev indexing
        run: |
          curl https://pkg.go.dev/github.com/QingQosh/overstand-go@${{ github.event.release.tag_name }}
```

#### SDK Publishing Coordination

**TypeScript Bindings Location:**
- Keep current location: `bindings/alert-registry/src/_generated/` (auto-generated from WASM)
- Index file: `bindings/alert-registry/src/index.ts` (hand-maintained, re-exports bindings + networks map)
- Package name: `@QingQosh/alert-registry-bindings` (unchanged)
- Published to: npm

**Unified Version Numbering:**
All SDKs version in lockstep with contract versions:
- v0.3.0 contracts → v0.3.0 SDKs (TypeScript, Python, Go, all identical version)
- v0.4.0 contracts → v0.4.0 SDKs (all updated together)

**Publishing Workflow:**

1. Create git tag (e.g., `v0.3.0`)
2. GitHub Actions workflow triggered
3. All SDKs regenerated and published atomically:
   - TypeScript: `npm publish @QingQosh/alert-registry-bindings@0.3.0`
   - Python: `poetry publish overstand-py@0.3.0`
   - Go: git tag `sdks/go/v0.3.0` (auto-indexed by pkg.go.dev)
4. If any SDK publish fails, entire release is rolled back

**SDK-Only Patch Releases:**

If SDK documentation or helpers need fixes without contract changes, use post-release versions:

- Python: `0.3.0.post1` (PyPI supports post-release identifiers)
- Go: No post-release; use manual tag (e.g., `sdks/go/v0.3.0-patch1`)
- TypeScript: `@QingQosh/alert-registry-bindings@0.3.0-patch1` (npm supports pre-release tags)

#### Documentation

**Per-SDK README:**

- `sdks/python/README.md`: Installation, quick start, async patterns, error handling
- `sdks/go/README.md`: Installation, go.mod usage, context cancellation, examples
- Unified: `docs/sdk-guide.md` linking all three

**Examples:**

- `sdks/python/examples/register_alert.py`
- `sdks/python/examples/query_paginated.py`
- `sdks/go/examples/register_alert/main.go`
- `sdks/go/examples/query_paginated/main.go`

**Changelog:**

- `sdks/python/CHANGELOG.md`
- `sdks/go/CHANGELOG.md`

---

### HIGH-004: Raise Hard Limits

#### Current Limits (from source)

| Limit | Current Value | Storage/Gas Reason | File |
|---|---|---|---|
| Max rules per alert | 5 | O(5) rules validated per alert; 5 easily fits in a single storage entry | `contracts/alert-registry/src/lib.rs:VALID_RULE_DESCRIPTORS.len()` |
| Max watchers in registry | 100 | O(n) watcher scan on each `register_watcher`; 100 is comfortable within Soroban's per-transaction CPU budget | `contracts/watcher-registry/src/lib.rs:MAX_WATCHERS` |
| Max admins in registry | 10 | Same as watchers; admin set is typically small | `contracts/watcher-registry/src/lib.rs:MAX_ADMINS` |
| Per-owner alert limit | Configurable (admin sets) | No hardcoded limit; configurable storage constraint | `contracts/alert-registry/src/lib.rs` instance storage `per_owner_alert_limit` |
| Per-contract active alerts | Configurable (admin sets) | Same as per-owner | `contracts/alert-registry/src/lib.rs` instance storage `per_contract_active_alert_limit` |
| Global alert limit | Configurable (admin sets) | Same as above | `contracts/alert-registry/src/lib.rs` instance storage `global_alert_limit` |
| Max page size (pagination) | 100 | Memory/CPU per query; larger pages risk timeout | `contracts/alert-registry/src/lib.rs:MAX_PAGE_SIZE` |
| Max deactivations per call | 50 | Resumable bulk operation; safety limit to avoid timeout | `contracts/alert-registry/src/lib.rs:MAX_DEACTIVATIONS_PER_CALL` |
| Max prune operations per call | 50 | Same | `contracts/alert-registry/src/lib.rs:MAX_PRUNE_PER_CALL` |

#### Proposed New Limits

| Limit | Old Value | New Value | Version | Reasoning | Risk |
|---|---|---|---|---|---|
| Max rules per alert | 5 | 5 | v0.3.0 (NO CHANGE) | Keep at 5 with RuleRegistry; mixing builtin+custom rules within 5-rule limit | None; custom rules support within existing limit |
| Max rules per alert | 5 | 10 | v0.4.0+ (DEFERRED) | Support monitoring of multi-event patterns (e.g., approve + transfer). Requires Soroban gas/storage validation on testnet. | DoS and timeout risk; defer pending empirical testing on mainnet v0.3.0 |
| Max watchers in registry | 100 | 250 | v0.4.0+ (DEFERRED) | Scale to support multiple competing watcher services. Recent Soroban gas upgrades allow larger Vec scans. | DoS: O(n) register_watcher call increases. Defer pending gas analysis. |
| Max admins in registry | 10 | 20 | v0.4.0+ (DEFERRED) | Support decentralized governance (multi-sig with >10 signers). | Minor; defer with other limits. |
| Max page size | 100 | 250 | v0.4.0+ (DEFERRED) | Reduce pagination round-trips for large alert queries. | Memory/CPU per query increases; risk of timeout. Defer pending empirical testing. |
| Max deactivations per call | 50 | 100 | v0.4.0+ (DEFERRED) | Faster bulk operations (fewer TX required to deactivate all). | Timeout risk; defer pending stress-test validation. |
| Max prune per call | 50 | 100 | v0.4.0+ (DEFERRED) | Same | Same. |

#### Rule Limit Evolution and RuleRegistry

**v0.2.x:** MAX_RULES_PER_ALERT = 5 (derived from VALID_RULE_DESCRIPTORS.len())

**v0.3.0 (RuleRegistry Introduction):** MAX_RULES_PER_ALERT = 5 (UNCHANGED)
- Custom rules are added to RuleRegistry, but total rules per alert remains 5
- This allows mixing builtin and custom rules (e.g., 2 builtin + 3 custom)
- Limitation explicitly documented in RuleRegistry README: "You can use up to 5 rules total per alert (any combination of builtin and custom)"
- Watchers should guide users: validate `alert.rules.len() <= 5` before registration

**v0.4.0+ (Future Upgrade):** Raise MAX_RULES_PER_ALERT to 10 (if Soroban gas/storage permits)
- Requires empirical gas/storage analysis on testnet v0.3.0 (post-mainnet launch)
- Only proceed if stress tests confirm no timeout/gas issues
- Defer to Phase 4 (Ecosystem Growth); not included in v0.3.0 scope

#### Implementation (v0.3.0 – Do NOT Change Limits)

**File Changes:**

- `contracts/alert-registry/src/lib.rs:`
  - NO CHANGES to limit constants in v0.3.0
  - Verify: `pub const VALID_RULE_DESCRIPTORS: [&str; 5]` remains unchanged

- `contracts/watcher-registry/src/lib.rs:`
  - NO CHANGES in v0.3.0

**Testing:**

- [ ] Unit test: Verify 5-rule limit enforced; 6 rules rejected
- [ ] Integration test: Mix builtin and custom rules (e.g., 2 builtin + 3 custom) succeeds

**Future (v0.4.0+ – When Limits Are Increased):**

Stress-test on mainnet v0.3.0 for 2 weeks post-launch. If no issues observed, propose v0.4.0 with new limits:

**Proposed v0.4.0 Changes:**

- `contracts/alert-registry/src/lib.rs:`
  - Line ~XX: Change `pub const MAX_PAGE_SIZE: u32 = 100;` → `pub const MAX_PAGE_SIZE: u32 = 250;`
  - Line ~XX: Change `pub const MAX_DEACTIVATIONS_PER_CALL: u32 = 50;` → `pub const MAX_DEACTIVATIONS_PER_CALL: u32 = 100;`
  - Line ~XX: Change `pub const MAX_PRUNE_PER_CALL: u32 = 50;` → `pub const MAX_PRUNE_PER_CALL: u32 = 100;`
  - Consider: `pub const MAX_RULES_PER_ALERT: u32 = 10;` (only if stress tests pass)

- `contracts/watcher-registry/src/lib.rs:`
  - Consider: Change `pub const MAX_WATCHERS: u32 = 250;` and `pub const MAX_ADMINS: u32 = 20;` (if demand justifies)

**Recommendation:** Document this deferral in `docs/roadmap.md` (Phase 4) and `CHANGELOG.md` so community understands 5-rule limit is temporary in v0.3.0.

---

### HIGH-005: Rule Semantics Documentation

#### Problem Statement

Five rule descriptors are listed (transfer, mint, burn, approve, clawback), but the README and docs do not specify exact conditions under which each fires. Watcher implementers must infer from contract code. This leads to inconsistencies.

Example ambiguities:
- Does `rule:transfer` fire on zero-value transfers?
- Does `rule:approve` fire on approvals to the zero address?
- Does `rule:clawback` fire only on clawbacks from untrusted accounts, or all clawbacks?

#### Design: Structured Rule Semantics Documentation

**Location:** `docs/rule-semantics/` (new directory)

**Structure:**

```
docs/rule-semantics/
├── README.md                       (overview)
├── rule_transfer.md               (detailed spec for rule:transfer)
├── rule_mint.md
├── rule_burn.md
├── rule_approve.md
├── rule_clawback.md
├── rule_schema.json               (JSON Schema for rule validation)
├── watcher_reference_impl/        (reference implementation)
│   ├── rust/
│   │   └── lib.rs                (rule matching engine)
│   └── go/
│       └── main.go               (same logic in Go)
└── examples/
    ├── transfer_event.json        (sample Horizon TX matching rule:transfer)
    ├── mint_event.json
    └── ...
```

**Per-Rule Markdown Spec:**

Each rule gets a detailed markdown file with:

1. **Semantic Definition:** Precise English description
2. **Event Pattern:** How the rule manifests in Stellar (operation type, account changes)
3. **Example:** Real Horizon TX showing the rule firing
4. **Edge Cases:** Boundary conditions (zero amounts, self-transfers, etc.)
5. **SDK Usage:** How to use the rule in TypeScript, Python, Go

**Example: `docs/rule-semantics/rule_transfer.md`**

```markdown
# rule:transfer

Matches Stellar *payment* operations that transfer native or asset balances between accounts.

## Semantic Definition

A rule:transfer event fires when:
1. A [Payment](https://developers.stellar.org/docs/learn/fundamentals/transactions/list-of-operations#payment) operation succeeds
2. Either:
   - (Native XLM) The amount >= 0.00001 lumens (dust threshold), OR
   - (Asset) The amount > 0 stroops (no dust threshold for assets)
3. The source and destination are different accounts (no self-payments)

## Event Pattern

Stellar Horizon representation:

```json
{
  "type": "payment",
  "source_account": "GABC...XYZ",
  "asset_type": "native",        // or "credit_alphanum4" / "credit_alphanum12"
  "amount": "100.0000000",
  "from": "GABC...XYZ",
  "to": "GDEF...123"
}
```

## Examples

### Example 1: Native XLM Transfer

**TX:** https://horizon-testnet.stellar.org/transactions/abc123...

```json
{
  "type": "payment",
  "amount": "50.0000000",
  "asset_type": "native",
  "from": "GABC...XYZ",
  "to": "GDEF...123"
}
```

**Matches?** YES — native XLM, amount > 0.

### Example 2: Asset Transfer

```json
{
  "type": "payment",
  "amount": "1000.0000000",
  "asset_type": "credit_alphanum4",
  "asset_code": "USD",
  "asset_issuer": "GBBM...",
  "from": "GABC...XYZ",
  "to": "GDEF...123"
}
```

**Matches?** YES — asset transfer, amount > 0.

## Edge Cases

| Scenario | Matches | Rationale |
|---|---|---|
| Amount = 0.00001 XLM | YES | Above dust threshold |
| Amount = 0 XLM | NO | Below dust threshold (network rejects anyway) |
| Self-transfer (from == to) | NO | Not a "transfer" if not moving value |
| Clawback (via clawback op, not payment) | NO | Different operation type; use rule:clawback |
| Path payment with intermediaries | YES | Still a payment; end result is transfer |

## SDK Usage

### TypeScript

```typescript
import { networks } from "@QingQosh/alert-registry-bindings";

const client = new Client({ ... });

// Register alert for any transfer of USD on MyContract
await client.registerAlert({
  owner: ownerAddr,
  targetContract: myContractAddr,
  rules: ["rule:transfer"],
  webhookHash: webhookHash,
});
```

### Python

```python
from overstand import AsyncClient

async def monitor_transfers():
    alert_id = await client.register_alert(
        owner=owner_addr,
        target_contract=my_contract_addr,
        rules=["rule:transfer"],
        webhook_hash=webhook_hash,
    )
```

### Go

```go
alertID, err := client.RegisterAlert(ctx, &overstand.RegisterAlertRequest{
    Rules: []string{"rule:transfer"},
})
```

## Watcher Reference Implementation

See `rule_semantics/watcher_reference_impl/` for a runnable reference:

```rust
// Pseudocode from rule:transfer matching
fn matches_transfer(tx: &Transaction) -> bool {
    for op in &tx.operations {
        if op.type != "payment" { continue; }
        
        let amount: f64 = op.amount.parse()?;
        if op.asset_type == "native" && amount < 0.00001 { continue; }
        if amount <= 0.0 { continue; }
        if op.from == op.to { continue; }  // self-transfer
        
        return true;  // Matched!
    }
    false
}
```

---

## See Also

- [rule:mint](rule_mint.md)
- [rule:burn](rule_burn.md)
- [rule:approve](rule_approve.md)
- [rule:clawback](rule_clawback.md)
- [Rule Schema (JSON Schema)](rule_schema.json)
```

**JSON Schema (`docs/rule-semantics/rule_schema.json`):**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "OverStand Rule Descriptor",
  "type": "object",
  "properties": {
    "rule_id": {
      "type": "string",
      "enum": ["rule:transfer", "rule:mint", "rule:burn", "rule:approve", "rule:clawback"],
      "description": "Built-in rule identifier"
    },
    "name": {
      "type": "string",
      "description": "Human-readable rule name"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semantic version of rule semantics"
    },
    "event_type": {
      "type": "string",
      "description": "Stellar operation type(s) this rule matches"
    },
    "conditions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Required conditions for a match (e.g., 'amount > 0')"
    },
    "edge_cases": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "scenario": { "type": "string" },
          "matches": { "type": "boolean" },
          "reason": { "type": "string" }
        }
      }
    }
  },
  "required": ["rule_id", "name", "event_type", "conditions"]
}
```

**Watcher Reference Implementation:**

```rust
// sdks/rust/src/rules/mod.rs (or docs/rule-semantics/watcher_reference_impl/rust/lib.rs)

pub mod transfer;
pub mod mint;
pub mod burn;
pub mod approve;
pub mod clawback;

pub trait RuleMatcher {
    fn matches(&self, tx: &OperationBody) -> bool;
}

impl RuleMatcher for TransferRule {
    fn matches(&self, tx: &OperationBody) -> bool {
        if let OperationBody::Payment(op) = tx {
            op.amount > 0 && op.from != op.to
        } else {
            false
        }
    }
}

// Similar for other rules...
```

#### SDK Integration

Both Python and Go SDKs include `rule_matcher` modules:

- `sdks/python/overstand/rule_matcher.py` — re-exports reference implementation
- `sdks/go/rule_matcher.go` — same logic in Go

**Usage in Watcher:**

```python
from overstand.rule_matcher import matches_rule

for tx in horizon_transactions:
    for rule in alert_rules:
        if matches_rule(rule, tx):
            send_webhook(webhook_url, tx)
```

#### Implementation

- [ ] Create `docs/rule-semantics/` directory
- [ ] Write detailed markdown for each rule (transfer, mint, burn, approve, clawback)
- [ ] Generate JSON Schema from rule specs
- [ ] Implement Rust reference matcher in `sdks/rust/src/rules/` (or docs/)
- [ ] Implement Go reference matcher in `sdks/go/rule_matcher.go`
- [ ] Add examples: `docs/rule-semantics/examples/*.json`
- [ ] Link from README and TypeScript/Python/Go SDK docs

---

## SECTION 3: TIER 2 MEDIUM-PRIORITY (Target: 6+ months post-mainnet)

### Overview

With security fixes deployed, mainnet live, and extensibility in place, Tier 2 focuses on governance processes, operational maturity, and ecosystem hardening. These are valuable for long-term sustainability but not blockers for production use.

---

### Governance Process

#### Problem Statement

No formal process for:
- Proposing new rule descriptors or raising hard limits
- Voting on feature requests
- Managing emergency contract pauses or rollbacks
- Handling security incidents

This leaves important decisions to ad-hoc GitHub discussions.

#### Design: Tiered Governance

**Tier 1 (Immediate):** Simple single-admin decision-making

- Admin (multisig on mainnet) has authority to:
  - Deploy contract upgrades (via Stellar's `UpgradeContractData` operation)
  - Approve custom rules in RuleRegistry
  - Adjust per-owner/per-contract alert limits
  - Suspend/revoke alerts in emergency
- Decisions are logged as contracts-emitted events (auditable on-chain)
- Changes are announced via GitHub releases (off-chain)

**Tier 2 (Post-Mainnet):** Multi-sig governance

- Replace single admin with Stellar account-level multisig (threshold signature)
- Example: 3-of-5 maintainers sign admin actions
- Requires Stellar account setup (not contract-level); low development overhead

**Tier 3 (1+ years):** DAO governance

- On-chain DAO contract (managed separately) holds admin role in AlertRegistry/RuleRegistry
- Community token holders vote on proposals
- Executors implement voted decisions
- Long-term project; outside scope of this upgrade spec

#### Implementation (Tier 1 + Early Tier 2)

**For Mainnet (v0.3.0):**

1. **Admin Key Management:**
   - Document in `docs/governance.md`: How to safeguard admin key(s)
   - Recommend hardware wallet (Ledger/Trezor) for mainnet admin
   - Use time-locked transactions for sensitive operations (e.g., contract upgrades)

2. **Proposal Process:**
   - GitHub Discussions or Issues for proposals
   - Voting via comment reactions (+1 / -1)
   - Admin evaluates consensus and implements via transaction
   - Event logged on-chain; CHANGELOG updated

3. **Emergency Procedures:**
   - Admin can call `suspend_alert(admin, config_id)` to lock problematic alerts
   - Owners can call `unlock_admin(admin, config_id)` only if admin calls it first
   - For critical bugs: deploy v0.3.1 patch, coordinate community migration

**Document: `docs/governance.md`**

```markdown
# OverStand Governance Process

## Current Model (v0.3.0 – v0.4.0)

Single admin (multisig account on mainnet) manages:
- Contract upgrades
- Rule registry approvals
- Alert limit configuration
- Emergency suspensions

## Admin Responsibilities

- Monitor Soroban events for anomalies
- Review rule registry submissions (GitHub issues)
- Approve/revoke rules based on community consensus
- Deploy timely security patches
- Communicate changes via GitHub releases

## How to Propose

1. **Feature Request:** GitHub Discussions → tag @maintainers
2. **Rule Submission:** GitHub Issue with rule spec (name, semantics, examples) → DAO approval (majority reaction)
3. **Limit Adjustment:** Propose via Discussions → stress-test on testnet → admin deploys to mainnet

## How to Vote

- Proposals use GitHub emoji reactions
- 👍 = Support
- 👎 = Oppose
- 🚀 = Critical (needs immediate attention)

Consensus = 70%+ thumbs-up (qualified majority).

## Future: Multi-Sig Governance (v0.5.0+)

Replace single admin with Stellar account-level 3-of-5 multisig:
- 5 maintainers (elected or appointed)
- 3 signatures required for any admin action
- Increases trust and decentralization

## Future: DAO Governance (v1.0.0+)

Community-controlled DAO contract holds admin role.
- Token holders vote
- Proposals time-locked for transparency
- No single point of failure
```

---

### Operational Runbook

#### Problem Statement

No documented procedures for:
- Monitoring and alerting on anomalies (e.g., spike in alert removals, watcher churn)
- Responding to contract failures or unexpected behavior
- Rotating admin keys safely

#### Design: Operations Manual

**Document: `docs/operations-runbook.md`**

```markdown
# OverStand Operations Runbook

## Monitoring

### Key Metrics (via Soroban Event Indexing)

| Metric | Source | Threshold | Action |
|---|---|---|---|
| Alert registration rate | `alert.register` events | >1000/day | Investigate spam |
| Alert removal rate | `alert.remove` events | >50% of registrations/day | Check for instability |
| Watcher churn | `WatcherRegistry` events | >10%/day | Review watcher SLAs |
| Webhook errors | `alert.update` with empty webhook | >5%/day | Alert owners to check webhook endpoints |
| Exceeds per-owner limit | `RegisterAlertFailed` with code 6 | >100/day | Review limit configuration |

### Monitoring Setup

1. **Indexer Service:** Run Soroban event indexer (TBD)
2. **Alerting:** Send Slack/email if thresholds exceeded
3. **Dashboard:** Real-time metrics via Grafana (optional, v1.0.0+)

### Example Queries

```bash
# Count alert registrations in last 24h (using Horizon)
stellar contract events \
  --contract-id <ALERT_REGISTRY_ID> \
  --network mainnet \
  | grep alert.register | wc -l

# Get alert removal rate
stellar contract events \
  --contract-id <ALERT_REGISTRY_ID> \
  --network mainnet \
  | jq '[.[] | select(.topic == "alert.remove")] | length'
```

## Incident Response

### Scenario 1: High Alert Removal Rate (>50%)

**Symptoms:** Many owners suddenly removing their alerts.

**Diagnosis Steps:**
1. Check if a major watche node went down (community reports?)
2. Check RPC latency spike (Stellar API issues?)
3. Check contract logs for errors in recent TX

**Response:**
- Post-mortem in GitHub Discussion
- If watcher issue: recommend alternative watchers
- If RPC issue: inform Stellar SDF
- If contract bug: prepare patch

### Scenario 2: Contract Upgrade Failed

**Symptoms:** Upgrade TX rejected; AlertRegistry stuck at old version.

**Diagnosis:**
- Check TX receipt for error message
- Verify WASM binary hash matches expected

**Response:**
- Retry with corrected deployment parameters
- If unsalvageable: deploy new contract address
- Coordinate community migration

### Scenario 3: Admin Key Compromised

**Symptoms:** Unauthorized admin actions observed (e.g., suspension of all alerts).

**Response (Immediate):**
1. Pause all admin actions (notify community)
2. Revoke compromised key from Stellar account multisig
3. Deploy emergency contract version with security fix (if needed)

**Response (Post-Incident):**
- Root-cause analysis (how was key exposed?)
- Update key management docs
- Schedule security audit

## Key Rotation

### Admin Key Update (Mainnet)

**Precondition:** Current admin is multisig-capable account.

**Steps:**
1. Create new Stellar account (e.g., on hardware wallet)
2. Test new account on testnet (deploy test TX, verify signing)
3. On mainnet: Call `propose_admin_transfer(old_admin, new_admin)`
4. Wait for 1 ledger (confirm events)
5. New admin calls `accept_admin_transfer(new_admin)` with their key
6. Verify via `get_admin()` query
7. Securely archive old key (or destroy if single-use)

**Rollback:** If new admin key is lost, old admin calls `cancel_admin_transfer()` (reverts proposal).

---

### Webhook Hardening

#### Current Webhook Design

1. Owner registers alert with SHA-256 hash of webhook URL
2. Watcher fetches URL from off-chain registry (not in contract; TBD)
3. Watcher signs webhook payload with HMAC-SHA256
4. Endpoint validates HMAC and processes alert

**Gap:** No HMAC signing is currently enforced by the contract. Watcher implementations vary.

#### Proposed Enhancements (Tier 2)

##### HMAC Signing for Webhook Payloads

**Design:**

1. Owner registers alert with:
   - Webhook URL hash (SHA-256)
   - Webhook secret hash (SHA-256 of a shared secret)
2. Watcher stores (off-chain) the plain URL and secret
3. Watcher constructs JSON payload and signs it:
   ```
   signature = HMAC-SHA256(secret, json_payload)
   ```
4. Watcher POSTs to endpoint with header:
   ```
   X-OverStand-Signature: sha256=<base64-encoded signature>
   X-OverStand-Timestamp: <unix-timestamp>
   ```
5. Endpoint validates:
   - Timestamp is within 5 minutes (replay prevention)
   - Signature matches HMAC-SHA256(secret, body)
   - Payload schema matches rule descriptor

**Contract Changes:**

```rust
pub fn register_alert(
    env: Env,
    owner: Address,
    target_contract: Address,
    label: String,
    webhook_hash: BytesN<32>,
    webhook_secret_hash: BytesN<32>,  // NEW
    rules: Vec<String>,
) -> u64 { }

pub fn update_webhook(
    env: Env,
    caller: Address,
    config_id: u64,
    webhook_hash: BytesN<32>,
    webhook_secret_hash: BytesN<32>,  // NEW
) { }
```

**Off-Chain Changes:**

- Watcher polls AlertRegistry, fetches alert config (includes hashes)
- Watcher maintains local mapping: config_id → (url, secret)
- On webhook dispatch, watcher includes HMAC header

##### Retry Logic and Dead-Letter Queue

**Problem:** Webhook may be temporarily unavailable (network blip, endpoint restart).

**Design:**

1. **Retry Policy:**
   - Immediate retry: 1st failure, retry after 10 seconds
   - Exponential backoff: 10s, 60s, 300s, 1800s (max 30 minutes)
   - Max retries: 5 attempts over ~2.5 hours

2. **Dead-Letter Queue:**
   - After max retries, webhook is moved to DLQ
   - DLQ entries are queryable off-chain (not on-chain)
   - Watcher emits event: `watcher.webhook_failed(alert_id, attempt_count)`
   - Owner can monitor DLQ and re-trigger manually

3. **Exponential Backoff Configuration (Optional):**
   - Owner can set retry policy via `update_alert_retry_policy(config_id, base_delay_seconds, max_retries)`
   - Contract stores policy in persistent storage
   - (Adds complexity; may be v1.0.0+ feature)

**Contract Changes (Optional):**

```rust
pub fn update_alert_retry_policy(
    env: Env,
    caller: Address,
    config_id: u64,
    base_delay_seconds: u32,
    max_retries: u32,
) { }

pub struct AlertConfig {
    // ...
    pub retry_policy: Option<RetryPolicy>,  // NEW
}

pub struct RetryPolicy {
    pub base_delay_seconds: u32,
    pub max_retries: u32,
}
```

##### Rate Limiting Per Watcher

**Problem:** Malicious watcher could fire the same webhook 1000x in rapid succession (DoS).

**Design:**

1. **Per-Watcher Limit:** Admin configures max webhook calls per watcher per hour
   ```
   Example: 1000 webhooks/hour/watcher = ~0.28 calls/second
   ```

2. **Enforcement (Off-Chain in Watcher):**
   - Watcher maintains token bucket per alert
   - Before dispatching webhook, check if quota allows
   - If exceeded, queue for next hour (or discard with logging)

3. **On-Chain Validation:**
   - Contract can optionally emit events with dispatch counts
   - Owner/admin can monitor via events to detect rate anomalies

**Recommendation:** Start with off-chain rate limiting in watcher nodes. Revisit on-chain enforc

ement if spam becomes an issue.

---

## SECTION 4: CROSS-CUTTING CONCERNS

### Test Coverage Requirements

| Tier | Feature | Unit Tests | Integration Tests | Property Tests | Fuzz Tests | Coverage Target |
|---|---|---|---|---|---|---|
| 0 | Fix #197 (Gated Reads Auth) | ✅ 8 test cases (one per function) | ✅ Gating enabled/disabled scenarios | ✅ For-all authorized querier checks | — | >95% |
| 0 | Fix #198 (Incremental Sync) | ✅ 2 test cases (both functions) | ✅ Sync consistency across ledger resets | ✅ Tombstone retention properties | — | >95% |
| 1 | RuleRegistry | ✅ Register, approve, validate | ✅ AlertRegistry + RuleRegistry integration | ✅ Rule consistency invariants | ✅ Schema parsing | >90% |
| 1 | Python SDK | ✅ Type marshaling | ✅ Testnet queries end-to-end | — | — | >80% |
| 1 | Go SDK | ✅ Type marshaling | ✅ Testnet queries end-to-end | — | — | >80% |
| 1 | Raise Limits | ✅ Per-limit unit tests | ✅ Stress test at new limits | ✅ Invariants hold at scale | — | >90% |
| 2 | Webhook Hardening | ✅ HMAC validation | ✅ End-to-end webhook dispatch | — | ✅ Malformed payloads | >85% |
| 2 | Governance | — | ✅ Admin transfer flow | — | — | — |

### Breaking-Change Communication Plan

#### CHANGELOG

Update `CHANGELOG.md` per release with:

```markdown
## [0.3.0] - 2025-02-XX

### BREAKING CHANGES
- **Gated Read Functions:** All gated reads now require `querier.require_auth()`.
  - Affected: `get_alert`, `get_alert_active`, `get_alerts_for_contract`, ...
  - Migration: Update CLI examples with `--source` flag; update SDK calls to authenticate querier.
- **Incremental Sync:** `get_alerts_modified_since` and `get_alerts_modified_since_ledger` now require `querier: Address` parameter.
  - Migration: Provide watcher address as querier; ensure authentication.

### Security
- Fixed #197: Gated reads now validate querier signature (was unauthenticated).
- Fixed #198: Incremental sync now enforces watcher-gating (was public).

### New Features
- None (0.3.0 is security-focused)

### Bug Fixes
- None

### Dependencies
- Soroban SDK: 25.3.0 (unchanged)
- Rust: 1.88+ (unchanged)
```

#### Migration Guide

Create `docs/upgrading-v0.2-to-v0.3.md`:

```markdown
# Upgrading from v0.2.0 to v0.3.0

## Summary

v0.3.0 fixes two critical security vulnerabilities (#197 and #198).
Read function signatures now require authentication, making them breaking changes for CLI and SDK users.

## Affected Functions

All 10 gated read functions now require `querier` authentication:

1. `get_alert(querier, config_id)` — querier must now sign
2. `get_alert_active(querier, config_id)` — querier must now sign
3. ... [list all 8]
4. `get_alerts_modified_since(querier, since, offset, limit)` — querier NEW parameter
5. `get_alerts_modified_since_ledger(querier, since_ledger, offset, limit)` — querier NEW parameter

## Update Steps

### CLI Users

**Old Command:**
```bash
stellar contract invoke \
  --id <ALERT_REGISTRY_CONTRACT_ID> \
  --network testnet \
  -- get_alert \
  --querier <QUERIER_ADDRESS> \
  --config_id 1
```

**New Command:**
```bash
stellar contract invoke \
  --id <ALERT_REGISTRY_CONTRACT_ID> \
  --source <QUERIER_IDENTITY> \           # NEW: must provide source
  --network testnet \
  -- get_alert \
  --querier <QUERIER_ADDRESS> \
  --config_id 1
```

**What Changed:** Added `--source <QUERIER_IDENTITY>`. The `--source` must match the signer (i.e., the account holding the private key for `querier`).

### TypeScript SDK Users

**Old Code:**
```typescript
const alert = await client.getAlert(
  "GABC...XYZ",  // querier (unauthenticated)
  1               // config_id
);
```

**New Code:**
```typescript
const alert = await client.getAlert(
  "GABC...XYZ",  // querier (must be the signer)
  1               // config_id
);
// No SDK-level change; authentication is handled by TransactionBuilder
// Just ensure the querier address matches the signer address
```

### Python SDK Users

```python
# Update to overstand-py >= 0.3.0

from overstand import AsyncClient

alert = await client.get_alert(
    querier_address,  # must be the signer
    config_id=1
)
```

### Go SDK Users

```go
// Update to github.com/QingQosh/overstand-go >= v0.3.0

alert, err := client.GetAlert(ctx, querierAddr, 1)
// Querier must be the signer; context is authenticated by stellar-sdk
```

### Watchers (Off-Chain)

If your watcher queries AlertRegistry, update your polling code:

**Before:**
```javascript
const alerts = await client.getAlertsForContract(anyAddress, targetAddr);
```

**After:**
```javascript
const alerts = await client.getAlertsForContract(watcherAddress, targetAddr);
// watcherAddress must sign the TX; matches the watcher's Stellar account
```

## Contract Upgrade

No data migration is required. v0.3.0 contracts have a new address on testnet; alert owners must:

1. Note the new contract address from GitHub release
2. Re-register alerts on the new contract (1-ledger operation per alert, no cost)
3. Update watcher configuration to poll the new contract address

**Old Alert:** Contract address `CABC...` (v0.2.0) — data remains but is no longer used  
**New Alert:** Contract address `CXYZ...` (v0.3.0) — register and activate

## FAQ

**Q: Why require authentication for read operations?**
A: It prevents unauthorized queriers from impersonating watchers. Without auth, any caller could fake being a watcher and read protected alerts.

**Q: Is this a mainnet breaking change?**
A: No mainnet v0.2.0 is deployed yet. v0.3.0 is the first mainnet deployment.

**Q: Can I still read without watcher-gating?**
A: Yes, if the admin hasn't called `set_watcher_registry()`, reads are open to anyone (no gating enforced). However, querier still must authenticate themselves (call `require_auth()`).
```

#### Semver & npm Versioning

- **Contract:** v0.2.0 → v0.3.0 (minor version bump for breaking semantics change)
- **TypeScript Bindings:** @QingQosh/alert-registry-bindings@0.3.0 (match contract)
- **Python SDK:** overstand-py 0.3.0 (match contract)
- **Go SDK:** github.com/QingQosh/overstand-go@v0.3.0 (match contract)

All SDK package managers should highlight breaking changes:

```
npm: npm notice [BREAKING] alert-registry-bindings@0.3.0 requires authentication for gated reads
pip: WARNING: overstand-py 0.3.0 has breaking changes in querier authentication
go:  Note: v0.3.0 breaking change in GetAlert() signature
```

---

### CI/CD Additions

#### Mutation Testing Gate

Currently runs nightly. Add as blocking gate before release:

```yaml
# .github/workflows/mutation-testing-gate.yml (update existing or new)
name: Mutation Testing Gate

on:
  pull_request:
    paths:
      - "contracts/**"

jobs:
  mutants:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: wasm32-unknown-unknown
      
      - name: Run cargo-mutants
        run: |
          cargo install cargo-mutants
          cargo mutants --package alert-registry --in-place -- --lib
      
      - name: Check mutation score
        run: |
          score=$(cargo mutants --list | grep -c "MISSED")
          if [ $score -gt 5 ]; then
            echo "ERROR: >5 missed mutations detected"
            exit 1
          fi
```

#### WASM Size Budget Check

Enhance existing check:

```yaml
# .github/workflows/build-wasm.yml (update existing)
- name: Check WASM size
  run: |
    size=$(stat -f%z contracts/alert-registry/target/wasm32-unknown-unknown/release/alert_registry.wasm)
    if [ $size -gt 61440 ]; then
      echo "ERROR: WASM size $size bytes > 60KB budget"
      exit 1
    fi
    echo "WASM size: $((size / 1024))KB ✓"
```

#### SDK Regeneration Job

```yaml
# .github/workflows/regenerate-sdks.yml (new)
name: Regenerate SDKs on Contract Change

on:
  push:
    paths:
      - "contracts/*/src/**"
    branches:
      - main

jobs:
  regenerate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: wasm32-unknown-unknown
      
      - name: Build WASM
        run: cargo build --release --target wasm32-unknown-unknown
      
      - name: Generate bindings
        run: |
          # TypeScript
          stellar contract bindings typescript \
            --wasm contracts/alert-registry/target/wasm32-unknown-unknown/release/alert_registry.wasm \
            --output-dir bindings/alert-registry/src/_generated
          
          # Python
          stellar contract bindings python \
            --wasm contracts/alert-registry/target/wasm32-unknown-unknown/release/alert_registry.wasm \
            --output-dir sdks/python/overstand/_generated
          
          # Go
          stellar contract bindings go \
            --wasm contracts/alert-registry/target/wasm32-unknown-unknown/release/alert_registry.wasm \
            --package-name overstand \
            --output-dir sdks/go
      
      - name: Commit regenerated code
        run: |
          git config user.name "CI"
          git config user.email "ci@overstand.dev"
          git add bindings/ sdks/
          git commit -m "Regenerate SDKs from updated contracts" || true
          git push
```

---

### Security Audit Scope

#### Recommended Firms

1. **Stellar SDF Internal Audit** (free for Stellar ecosystem projects)
2. **CertiK** (known for Soroban contracts)
3. **Trail of Bits** (comprehensive security)
4. **Halborn** (blockchain security)

#### Scope (Pre-Mainnet v0.3.0)

| Component | Depth | Estimated Cost | Timeline |
|---|---|---|---|
| AlertRegistry contract | Full code review + test coverage | $15K–25K | 2–3 weeks |
| WatcherRegistry contract | Full code review | $5K–10K | 1 week |
| Cross-contract interaction (AlertRegistry ↔ WatcherRegistry) | Medium (focused on auth) | Included | — |
| CI/CD pipeline | Light (ensure no secrets leaked) | $2K–5K | 3–5 days |
| **Total** | — | **$22K–40K** | **3–4 weeks** |

#### Pre-Audit Checklist

- [ ] All Tier 0 fixes (197, 198) implemented and tested
- [ ] Code coverage >90% (cargo-llvm-cov)
- [ ] No security warnings (cargo-audit, clippy pedantic)
- [ ] Fuzzing has run for ≥1 week with no crashes
- [ ] Testnet deployment successful and stable for 1 week

#### Audit Report Handling

- Public report published on GitHub (transparency)
- Any findings categorized by severity and addressed
- Remediation commits reviewed before mainnet deployment
- Audit sign-off required before mainnet approval

---

## SECTION 5: IMPLEMENTATION TIMELINE & SUCCESS CRITERIA

### Gantt Timeline

```
2025-02 (Weeks 1–4): Tier 0 Security Fixes
│
├─ Week 1-2: Fix #197 + #198 implementation & unit tests
├─ Week 2-3: Integration tests, TypeScript binding updates
├─ Week 3-4: Testnet deployment, smoke tests
│
2025-03 (Weeks 1–2): Tier 0 Validation & Mainnet Deployment
│
├─ Week 1: Security audit (concurrent with weeks 1-4 above)
├─ Week 2: Audit remediation, mainnet deployment, post-launch monitoring
│
2025-03–04 (Weeks 5–12): Tier 1.1 RuleRegistry
│
├─ Week 5-6: RuleRegistry contract design & implementation
├─ Week 7-8: Integration with AlertRegistry, testing
├─ Week 9-10: Testnet deployment, community rule submissions
├─ Week 11-12: Mainnet deployment as v0.4.0
│
2025-04–05 (Weeks 13–20): Tier 1.2 Python & Go SDKs
│
├─ Week 13-14: Python SDK generation & async API design
├─ Week 15-16: Python SDK tests, documentation, PyPI publication
├─ Week 17-18: Go SDK generation & context-based API design
├─ Week 19-20: Go SDK tests, documentation, pkg.go.dev publication
│
2025-05–06 (Weeks 21–24): Tier 1.3 Raise Limits & Rule Semantics
│
├─ Week 21-22: Stress-test new limits (250 watchers, 10 rules/alert, etc.)
├─ Week 23: Rule semantics documentation (transfer, mint, burn, approve, clawback)
├─ Week 24: Watcher reference implementations in Rust/Go
│
2025-06+ (Ongoing): Tier 2 & Maintenance
│
├─ Governance process documentation
├─ Operations runbook & monitoring setup
├─ Webhook hardening (HMAC, retries, rate limiting)
└─ Incident response & key rotation procedures
```

**Compressed Timeline (Critical Path Only):**

- **Feb 15** – Tier 0 fixes merged & tested (2 weeks)
- **Mar 1** – Mainnet v0.3.0 deployed (post-audit)
- **Apr 15** – Tier 1: RuleRegistry + SDKs deployed (6 weeks)
- **Jun 1** – Tier 1: Documentation complete
- **Jun 30+** – Tier 2: Governance & Operations

### Success Criteria

#### Tier 0 (Critical)

| Criterion | Target | Measurement | Pass/Fail |
|---|---|---|---|
| Fix #197 merged | Week 2 | GitHub PR merged | ✓ When merged |
| Fix #198 merged | Week 2 | GitHub PR merged | ✓ When merged |
| Unit test coverage (fixes) | >95% | cargo-llvm-cov report | ✓ If coverage > 95% |
| Integration tests pass | 100% | CI workflow success | ✓ If all pass |
| Testnet v0.3.0 stable | 7 days | No errors in liveness checks | ✓ If <1% error rate |
| Security audit complete | Pre-mainnet | Signed report | ✓ If no CRITICAL findings |
| Mainnet deployed | Mar 1 | Contract address recorded | ✓ If TX successful |

#### Tier 1 (High-Priority)

| Criterion | Target | Measurement | Pass/Fail |
|---|---|---|---|
| RuleRegistry contract live | Apr 15 | Testnet + mainnet deployed | ✓ If deployed |
| ≥5 custom rules registered | Jun 1 | Via on-chain queries | ✓ If count ≥ 5 |
| Python SDK published | May 1 | PyPI package available | ✓ If pip install works |
| Go SDK published | May 15 | pkg.go.dev indexed | ✓ If `go get` works |
| SDK tests pass (Python + Go) | 100% | CI workflow success | ✓ If all pass |
| New limits stress-tested | Jun 1 | 250 watchers + 10 rules/alert work | ✓ If latency < 3s |
| Rule semantics docs complete | Jun 1 | All 5 rules documented | ✓ If 5 markdown files exist |

#### Tier 2 (Medium-Priority)

| Criterion | Target | Measurement | Pass/Fail |
|---|---|---|---|
| Governance docs published | Jul 1 | `docs/governance.md` exists | ✓ If merged |
| Operations runbook published | Jul 1 | `docs/operations-runbook.md` exists | ✓ If merged |
| Webhook HMAC hardening | Aug 1 | Reference impl + tests | ✓ If code merged |
| Zero data-loss incidents | Ongoing | Post-mortems review | ✓ If none |

#### Overall Adoption Metrics (Post-Mainnet)

| Metric | Target | Timeline | Owner |
|---|---|---|---|
| Mainnet alert count | ≥100 active | Q2 2025 | Community |
| Watcher node count | ≥5 | Q2 2025 | Community |
| SDK downloads (PyPI) | ≥1K/month | Q3 2025 | Community |
| Go module clones | ≥500/month | Q3 2025 | Community |
| GitHub stars | ≥500 | Q3 2025 | Community |

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Audit finds CRITICAL vulnerability** | Medium | Catastrophic (blocks mainnet) | Pre-audit code review by maintainers; address findings before launch |
| **Testnet resets and alerts lost** | High | Medium (recreate on new testnet) | Expected behavior; maintain alert config backups; use mainnet for production |
| **Watcher node ecosystem slow to adopt** | Medium | Medium (lower ecosystem value) | Published Python/Go SDKs make integration easier; community outreach in Discord |
| **New limits trigger gas/storage DoS** | Low | High (mainnet halt) | Stress-test on testnet with 250 watchers, 10 rules/alert; empirical validation before deployment |
| **Admin key compromised** | Low | Catastrophic | Use hardware wallet for mainnet admin; multisig (3-of-5) in v0.5.0 |
| **RuleRegistry governance stalls** | Medium | Medium (delayed custom rules) | Simple 1-admin approval process in v0.4.0; DAO in v1.0.0+ if needed |
| **SDK generation diverges from contract** | Low | Medium (bindings broken) | CI golden file checks; run regeneration job on every contract change |

---

## Document Status & Next Steps

**This specification is complete and ready for implementation.**

**Next Steps:**

1. **Immediate (This Week):**
   - Review this document in team meeting
   - Assign developers to Tier 0 (Fix #197 + #198)
   - Open GitHub milestone for v0.3.0

2. **Tier 0 (Next 2–3 weeks):**
   - Implement fixes
   - Update CLI examples and bindings
   - Testnet deployment & smoke tests

3. **Audit & Mainnet (1–2 weeks after Tier 0):**
   - Engage audit firm
   - Prepare mainnet infrastructure
   - Execute deployment post-audit

4. **Tier 1 (Post-Mainnet, 1–3 months):**
   - Start RuleRegistry contract
   - Parallelize SDK generation (Python, Go)
   - Begin stress-testing new limits

5. **Tier 2 & Beyond (6+ months):**
   - Stabilize governance & operations
   - Community feedback loop
   - Plan v1.0.0 with DAO governance

---

## Appendix: File Modification Summary

### Tier 0 Changes

| File | Type | Change | Breaking |
|---|---|---|---|
| `contracts/alert-registry/src/lib.rs` | Modify | Add `querier.require_auth()` to 10 functions | [BREAKING] |
| `contracts/alert-registry/src/lib.rs` | Modify | Update `Cargo.toml` version v0.2.0 → v0.3.0 | — |
| `bindings/alert-registry/src/index.ts` | Regenerate | Update from new WASM ABI | — |
| `bindings/alert-registry/README.md` | Modify | Add authentication requirements to examples | — |
| `README.md` | Modify | Update CLI examples with `--source` flag | — |
| `docs/alert-registry.md` | Modify | Document querier authentication requirement | — |
| `CHANGELOG.md` | Modify | Add v0.3.0 entry with breaking changes | — |
| `docs/upgrade-guide.md` | Create | Migration guide v0.2 → v0.3 | — |

### Tier 1 Changes

| File | Type | Change | Breaking |
|---|---|---|---|
| `contracts/rule-registry/src/lib.rs` | Create | New RuleRegistry contract | — |
| `contracts/rule-registry/Cargo.toml` | Create | New workspace member | — |
| `contracts/alert-registry/src/lib.rs` | Modify | Add RuleRegistry integration, `validate_rule` function | — |
| `sdks/python/` | Create | Python SDK with async client | — |
| `sdks/go/` | Create | Go SDK with context-based API | — |
| `docs/rule-semantics/` | Create | Markdown specs for all 5 rule descriptors | — |
| `docs/sdk-guide.md` | Create | Unified SDK documentation | — |
| `CHANGELOG.md` | Modify | Add v0.4.0 entry (RuleRegistry + SDKs) | — |

### Tier 2 Changes

| File | Type | Change | Notes |
|---|---|---|---|
| `docs/governance.md` | Create | Governance process documentation | Policy document |
| `docs/operations-runbook.md` | Create | Operational procedures | Policy document |
| `docs/webhook-hardening.md` | Create | HMAC signing + retry logic | Design document |
| `.github/workflows/mutation-testing-gate.yml` | Update | Add as blocking gate | CI/CD |
| `.github/workflows/regenerate-sdks.yml` | Create | Auto-regenerate on contract change | CI/CD |
| `.github/workflows/publish-sdks.yml` | Create | Auto-publish to PyPI/pkg.go.dev | CI/CD |

---

## Design Decisions: Review Findings Resolution

This section documents decisions made in response to the design review findings (see `design-verdict.json`).

### FINDING 1: Incremental Sync Fix References Ambiguous Parameter Type

**Finding:** Design table provided without final decision; recommendation contradicts table. Implementers cannot proceed without explicit choice.

**Resolution:** ADDRESSED. Section "Fix #198" now includes definitive decision: `querier: Address` (required parameter). Added migration deadline (2 weeks on testnet) and breaking change notice. Decision rationale documented explicitly.

### FINDING 2: RuleRegistry Approval Mechanism Underspecified

**Finding:** No decision made for v0.3.0 approval flow. Missing error handling for failed rule approvals and rule revocation impact.

**Resolution:** ADDRESSED. Added explicit "Approval Mechanism (v0.3.0)" section with:
- Single-admin approval model (definitive for v0.3.0)
- 4-step approval flow (proposal → review → approval → revocation)
- Error handling table with error codes and behaviors
- Cross-contract failure handling (fail-closed semantics)
- Future upgrade path to multi-sig/DAO (v0.4.0+)

### FINDING 3: Mainnet Deployment Success Criteria Undefined

**Finding:** Success criteria are vague metrics with no measurable thresholds or failure conditions defined.

**Resolution:** ADDRESSED. Updated "Testnet Stress-Test Checklist" with:
- Quantified acceptance criteria (e.g., "All 1000 alerts stored without rejection")
- Explicit failure thresholds for each scenario (e.g., ">0 rejections → BLOCK mainnet")
- Sign-off checklist requiring all 10 tests to pass and security audit approved
- Clear go/no-go decision rule

### FINDING 4: Error Handling for Rule Validation and Cross-Contract Calls Not Specified

**Finding:** Unclear what happens if RuleRegistry call fails, schema is invalid, or non-admin attempts approval. Contract behavior is non-deterministic for error cases.

**Resolution:** ADDRESSED. Added "Error Handling and Validation" section with:
- Error codes table (RuleAlreadyExists, RuleNotFound, Unauthorized, InvalidSchema, ExternalRegistryError, InvalidRuleDescriptor)
- Cross-contract failure handling pseudocode (fail-closed recommendation)
- Schema validation strategy (JSON format recommended, validation logic provided)

### FINDING 5: Contradictory Rule Limit Specifications

**Finding:** HIGH-004 proposes raising MAX_RULES_PER_ALERT from 5 to 10 in v0.4.0, but HIGH-002 (RuleRegistry, v0.3.0) makes no mention of this change. User experience unclear if rules are limited to 5 while RuleRegistry allows unlimited registration.

**Resolution:** ADDRESSED. Completely restructured limit discussion with:
- "Rule Limit Evolution and RuleRegistry" section clarifying v0.3.0 keeps 5-rule limit (NO CHANGE)
- v0.4.0+ defers limit increase pending stress-test validation on mainnet v0.3.0
- Explicit documentation: RuleRegistry README will state "5-rule limitation" clearly
- Removed rule limit increase from v0.3.0 scope
- Implementation section updated: no changes to limit constants in v0.3.0

### FINDING 6: Python and Go SDK Retry and Timeout Logic Not Specified

**Finding:** No guidance on transient error handling, RPC timeout configuration, fallback endpoints, exponential backoff strategy, or retryable error classification.

**Resolution:** ADDRESSED. Added "Retry and Timeout Strategy" section with:
- Python AsyncClient retry logic (pseudocode with asyncio.timeout)
- Go SDK retry logic (context timeout, isRetryableError check)
- Default configuration (10s timeout, 3 retries, 1.5x backoff)
- Retryable vs non-retryable error classification
- SDK README examples for configuration

### FINDING 7: Version Strategy Contradictory

**Finding:** Specification says 'Deploy v0.2.1 with fixes' then immediately says 'This should be v0.3.0'. Unclear if v0.2.1 is mainnet or testnet-only. Watcher upgrade path ambiguous.

**Resolution:** ADDRESSED. Completely restructured version strategy in Section 1:
- Definitive decision: Use v0.3.0 for BOTH testnet and mainnet (no v0.2.1)
- Clear timeline: Week 1 deploy v0.3.0 to testnet; Week 2-3 deploy to mainnet
- 2-week grace period for v0.2.0 on testnet; then v0.2.0 address deprecated
- Single upgrade path: watchers upgrade once from v0.2.0 → v0.3.0 across all networks

### FINDING 8: TypeScript Bindings Regeneration Process Not Clarified

**Finding:** Unclear if bindings remain in current location or move. Version numbering consistency across SDKs undefined. Publishing coordination (atomic vs separate) not specified.

**Resolution:** ADDRESSED. Added new "SDK Publishing Coordination" section with:
- TypeScript location: Keep in `bindings/alert-registry/src/_generated/` (current)
- Unified version numbering: All SDKs version in lockstep (v0.3.0 contracts → v0.3.0 SDKs)
- Publishing workflow: Atomic release via git tag; all SDKs published together
- SDK-only patch releases: post-release versions (e.g., 0.3.0.post1)

### FINDING 9 (NIT): Implementation Checklist Uses Vague Line References

**Finding:** Line number references ('Line ~XX') instead of specific line ranges. Makes it hard for implementers to locate exact spots.

**Resolution:** NOTED FOR FUTURE. This finding is a NIT (not blocking). Concrete line numbers require reading source files (which will be done during implementation, not design). The pseudocode provided is sufficiently detailed for implementers to locate functions by name and add code accordingly. Recommend implementers use IDE search (Ctrl+F) to find function definitions.

### FINDING 10 (NIT): Aspirational Language About Version Storage

**Finding:** Statement about contractmeta version storage uses present tense ('already use') but refers to v0.3.0 (not yet deployed).

**Resolution:** ADDRESSED. Changed language from "already use" to "will use" in version governance section to reflect forward-looking nature of v0.3.0.

---

**End of Specification**

