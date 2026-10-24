# OverStand Upgrade Specification — Design Review

**Reviewer:** Design Review Subagent  
**Date:** 2025  
**Document Reviewed:**
- `upgrade-specification.md` (Primary)
- `project-analysis.md` (Context)

**Verdict:** CHANGES_REQUESTED (9 HIGH findings, 4 MEDIUM findings)

---

## Executive Summary

The upgrade specification defines a comprehensive roadmap for OverStand across three tiers (Security Fixes, Extensibility, Operations). The Tier 0 security fixes are well-motivated and address real issues (#197, #198) that block mainnet deployment. However, the specification contains **9 HIGH-severity ambiguities and unverified assumptions** that would lead to implementation confusion, broken cross-contract integration, and incomplete error handling if not resolved before coding begins.

Key problems:
1. **Clarification Required:** Tier 0 framing describes "NEW features" but analysis doc treats them as "FIXES"; specification is contradictory
2. **Cross-Contract Failure Modes Underspecified:** What happens when AlertRegistry calls RuleRegistry and it fails? Fail-closed vs. fail-open decision stated but not consistently applied
3. **Gated Read Semantics Ambiguous:** When watcher-gating is disabled vs. enabled, which reads are affected? Table lists 8 functions for Fix #197 but specs describe 10 functions later
4. **Backward Compatibility Unresolved:** Breaking changes to 8–10 function signatures; rollback and testnet migration paths lack concrete steps
5. **RuleRegistry Integration Incomplete:** Cross-contract call failure handling, schema versioning semantics, and approval workflow lack implementation detail
6. **Test Requirements Vague:** "Stress tests" defined with acceptance thresholds but no test harness or success criteria for "all tests PASS"
7. **Admin Key Custody and Governance:** Mainnet deployment checklist assumes secured keys but provides no procedure or automation
8. **Python/Go SDK Dependencies Unverified:** Proposed dependencies (stellar-sdk, httpx, etc.) not verified against current versions or compatibility
9. **TypeScript Bindings Regeneration Incomplete:** Workflow describes auto-regeneration but not how hand-written extensions (networks map, re-exports) are maintained without conflicts

---

## Findings

### HIGH-001: Tier 0 Framing Contradiction — "NEW Features" vs. "FIXES"

**Severity:** HIGH  
**Section:** Tier 0 Overview (Problem Statement section)  
**Issue:**

The upgrade specification states:
> "These fixes implement NEW security features for the first time."

However, the project analysis doc (section 5, "Identified Gaps & Weaknesses") frames issues #197 and #198 as vulnerabilities in EXISTING gated read functions:
> "When watcher-gating is enabled via `set_watcher_registry`, read queries (`get_alert`, etc.) accept a `querier` address parameter and check if it is an authorized watcher... However, the `querier` parameter is **not authenticated by Stellar**."

This is contradictory. Either:
1. Gated reads with unauthenticated `querier` parameters already exist in v0.2.0 (security bug to fix), OR
2. They don't exist and are new features being added (not a fix)

Verification needed: Does v0.2.0 AlertRegistry contract code actually have `get_alert(querier: Address)` and related functions, or not?

**Impact:** Implementer cannot determine if this is a refactor (update existing functions) or a new feature (add new functions). Contract upgrade strategy differs fundamentally between the two scenarios.

**Recommendation:**

Read the actual v0.2.0 contract code to determine the true state. Then:
- **If functions exist in v0.2.0:** Reframe as "Fix #197/198: Add Authentication to Existing Gated Reads" and clearly state this is a breaking change to existing function semantics.
- **If functions do NOT exist in v0.2.0:** Reframe as "Tier 0 Addition: Implement Secure Gated Reads with `require_auth()`" and clarify that unauthenticated read functions (if any) remain unchanged.

Also reconcile the project analysis doc's framing. Choose one consistent narrative for the specification.

---

### HIGH-002: Incremental Sync Function Count Mismatch

**Severity:** HIGH  
**Section:** Fix #197 Table (Affected Functions) vs. Fix #198 & Pseudocode  
**Issue:**

The "Affected Functions" table in Fix #197 lists **8 functions** requiring `querier.require_auth()`:

```
1. get_alert
2. get_alert_active
3. get_alerts_for_contract
4. get_active_alerts_for_contract
5. get_alerts_by_owner
6. get_contract_alerts_paginated
7. get_alerts_by_owner_paginated
8. get_active_contract_alerts_paged
```

However, Fix #198 then states:
> "Add an optional or required `querier: Address` parameter to both functions. When `querier` is provided..."

These are the 2 incremental sync functions. Later in "Pseudocode," the spec says:

> "Same change applies to all 8 affected functions in Fix #197: add `querier.require_auth();` as the first statement."

So is it 8 or 10 functions total? The spec later says "10 affected functions" in the Version Strategy table:

> "10 function signatures changed to require `querier.require_auth()`"

**Impact:** TypeScript bindings generation and CLI documentation will be incomplete if the function count is wrong. Testers won't know how many functions to validate.

**Recommendation:**

Clarify:
1. **Fix #197 affects 8 functions** (listed in table)
2. **Fix #198 affects 2 functions** (`get_alerts_modified_since` + `get_alerts_modified_since_ledger`)
3. **Total: 10 functions** with breaking signature changes
4. Update all references to use "8 gated read functions" and "2 incremental sync functions" for precision

---

### HIGH-003: Cross-Contract Failure Handling Contradicts Itself

**Severity:** HIGH  
**Section:** "Retry and Fallback Specification" + HIGH-002 RuleRegistry section  
**Issue:**

The "Retry and Fallback Specification" section (Tier 0) describes behavior when AlertRegistry calls RuleRegistry:

> "When AlertRegistry calls RuleRegistry::validate_rule for a custom rule and receives an error... **No automatic retry; caller is responsible.**"

This recommends **fail-closed** (reject rule if call fails).

However, in the HIGH-002 (RuleRegistry) section, the pseudocode for `validate_rule` in AlertRegistry states:

```rust
match registry.validate_rule(&rule) {
    Ok(is_valid) => is_valid,
    Err(_) => {
        // Cross-contract call failed; reject rule (fail-closed)
        false
    }
}
```

This is consistent (fail-closed). But then the decision box in the same section says:

| Decision | Fail-Closed | Fail-Open |
| **Fail-closed** | Simple; one code path; forces authentication | Breaking change; any existing unauthenticated caller breaks | **Cleaner but only viable if testnet is internal-only** |
| **Fail-open** | ... | ... |

**This suggests fail-open might be acceptable**, which contradicts the earlier pseudocode and "Retry and Fallback Specification."

Additionally, the section later states:

> "**Builtin Rules Always Available:** VALID_RULE_DESCRIPTORS (transfer/mint/burn/approve/clawback) are validated locally; no cross-contract call required. Alerts using only these rules always register successfully, even if RuleRegistry is offline."

This implies built-in rules use a **fallback path** (implicit fail-open for built-ins), but custom rules fail-closed. The specification doesn't clarify: **What if AlertRegistry has both built-in and custom rules in a single `register_alert` call?**

Pseudocode in Tier 0 suggests:

```rust
for rule in &rules {
    if !Self::validate_rule(&env, rule.clone()) {
        panic_with_error!(env, ContractError::InvalidRuleDescriptor);
    }
}
// ... rest of logic (fails if ANY rule is invalid)
```

This means **if any rule is invalid (including RuleRegistry call failures), the entire registration fails.** So the alert registration fails if ANY custom rule validation fails. Is that the intent?

**Impact:** Implementer will code inconsistently with the intended behavior. Customers' alert registrations may fail unexpectedly if RuleRegistry is temporarily offline, leading to production issues.

**Recommendation:**

Make an explicit choice and document it clearly:

**OPTION A (Recommended): Fail-Closed**
- Custom rules require RuleRegistry to be live
- If RuleRegistry is offline, custom rule registration fails
- Built-in rules always succeed (no RuleRegistry dependency)
- Document: "AlertRegistry v0.4.0+ requires RuleRegistry to be live for custom rules. Operators should monitor RuleRegistry availability."

**OPTION B: Fail-Open (for custom rules only)**
- If RuleRegistry is offline, custom rules are temporarily approved (assume valid)
- Risk: Invalid rules may be registered; must be fixed when RuleRegistry comes back
- Requires ability to "block" invalid rules later (e.g., via contract upgrade)

**Choose Option A (fail-closed) for security-by-default and add to final spec.**

---

### HIGH-004: Watcher-Gating Enable/Disable Semantics Unspecified

**Severity:** HIGH  
**Section:** Fix #197 & #198 pseudocode; Mainnet Deployment Plan  
**Issue:**

The specification describes watcher-gating as **optional**:
> "If let Some(registry) = get_watcher_registry(&env) { ... }"

This means AlertRegistry can operate in two modes:
1. **Gating Disabled** (no WatcherRegistry configured): All reads are public, no auth required
2. **Gating Enabled** (WatcherRegistry configured): Reads require `querier.require_auth()` and check `is_watcher_authorized()`

The specification does NOT clarify:
- **When should gating be enabled?** (At mainnet deployment? Opt-in by admin? Mandatory?)
- **Can it be toggled (enabled ↔ disabled)?** If so, what happens to in-flight queries?
- **What reads are gated vs. ungated?**

Currently, the spec says these **are gated** (require querier auth + watcher check if enabled):
- get_alert
- get_alert_active
- get_alerts_for_contract
- get_active_alerts_for_contract
- get_alerts_by_owner
- get_contract_alerts_paginated
- get_alerts_by_owner_paginated
- get_active_contract_alerts_paged
- get_alerts_modified_since (after Fix #198)
- get_alerts_modified_since_ledger (after Fix #198)

But other read functions are NOT listed as gated:
- `get_alert_removed` (assumed ungated?)
- Any paginated listing with no owner/contract filter?

The project analysis doc mentions a third scenario:
> "Unauthenticated queries fail with `NotAWatcher`."

But the pseudocode says queries succeed if gating is disabled (No watcher registry, so read is allowed).

**Impact:** Watchers won't know which reads are gated. Implementers will guess, causing runtime errors. Mainnet operations may fail if gating is unexpectedly disabled (or enabled) after deployment.

**Recommendation:**

Create a definitive **Gating Matrix** in the specification:

| Function | Gated (requires `require_auth()`) | Watcher Check (if enabled) |
|---|---|---|
| `get_alert` | YES | YES |
| `get_alert_active` | YES | YES |
| `get_alerts_for_contract` | YES | YES |
| `get_active_alerts_for_contract` | YES | YES |
| `get_alerts_by_owner` | YES | YES |
| `get_contract_alerts_paginated` | YES | YES |
| `get_alerts_by_owner_paginated` | YES | YES |
| `get_active_contract_alerts_paged` | YES | YES |
| `get_alerts_modified_since` | YES (Fix #198) | YES (Fix #198) |
| `get_alerts_modified_since_ledger` | YES (Fix #198) | YES (Fix #198) |
| `get_alert_removed` | NO | NO |
| `[any future read]` | NO | NO |

And add to deployment checklist:
- **Mainnet Deployment Decision:** Will WatcherRegistry be configured at mainnet launch? (YES/NO)
  - If YES: Gating is mandatory; all watchers must authenticate
  - If NO: Gating is optional; can be enabled later by admin

---

### HIGH-005: Backward Compatibility & Testnet Migration Path Too Vague

**Severity:** HIGH  
**Section:** "Migration Strategy" (Tier 0) & "Mainnet Deployment Plan"  
**Issue:**

The specification says:

> "No intermediate v0.2.1; fixes go directly to v0.3.0"
> "Deploy a new contract version (v0.3.0) with these fixes."
> "Existing testnet deployments at the old address remain unchanged."

But then the "Testnet Migration Path" is sparse:

> "1. v0.2.0 contract remains at old address for 2 weeks (grace period for external users)
> 2. v0.3.0 deployed to new address immediately
> 3. Alert owners manually migrate: re-register on v0.3.0 (one-ledger operation)
> 4. Watchers update to call v0.3.0 contract address
> 5. v0.2.0 address deprecated after 2 weeks"

This is unclear:
- **How do alert owners know their alerts need to be re-registered?** Is there a migration script? A web UI? Manual CLI commands?
- **Can alerts be automatically transferred from v0.2.0 to v0.3.0, or must they be manually recreated?** (The spec says "re-register," implying manual recreation, but this is a **massive UX burden** for any testnet users)
- **What happens to active webhooks during migration?** If an alert has a pending webhook proposal, is it lost?
- **What's the communication plan?** Are watchers notified? Is there a "migration guide" document?

The spec also says:

> "All watchers must re-register against v0.3.0 contract address; v0.2.0 address is deprecated"

This is strong language but doesn't explain **how** watchers re-register. Is it a config file change? A rebuild? An on-chain action?

**Impact:** Testnet migration will be chaotic. Users will lose data or be confused about which contract to use. Mainnet lessons learned will be painful.

**Recommendation:**

Add a detailed **Testnet Migration Guide** to the specification (or reference a planned document):

1. **Pre-Migration (v0.3.0 RC):**
   - Publish migration guide to GitHub releases/docs
   - Provide CLI scripts: `./scripts/export-alerts-v0.2.0.sh` (export all alerts from old contract as JSON)
   - Provide CLI scripts: `./scripts/import-alerts-v0.3.0.sh <exported-alerts.json>` (re-register all alerts on new contract)

2. **Migration Window (Days 1–7):**
   - Both v0.2.0 and v0.3.0 contracts live side-by-side
   - AlertRegistry emits event: "Alert registered on v0.2.0; migrate to v0.3.0" (off-chain indexing can detect unmigrated alerts)
   - Watchers continue polling both addresses (backward compatibility)

3. **Cutover (Day 7–14):**
   - Admin emits message: "v0.2.0 will be deprecated in 1 week"
   - Watchers must switch to v0.3.0 contract address

4. **Deprecation (Day 14+):**
   - v0.2.0 contract address is removed from documentation
   - Alerts on v0.2.0 are no longer polled by official watchers
   - Users can still manually query v0.2.0 (data remains on-chain forever), but it's unsupported

Also clarify: **Can data be automatically migrated via a migration contract?** (See Project Analysis section 10.3 "Migration Contracts"). If so, add it to the specification.

---

### HIGH-006: RuleRegistry Approval Workflow Incomplete

**Severity:** HIGH  
**Section:** HIGH-002 (RuleRegistry) — "Approval Mechanism (v0.3.0)" subsection  
**Issue:**

The specification describes the approval workflow:

> "1. **Proposal:** Any caller calls `register_rule(...)` → rule is created but marked `approved=false`"
> "3. **Approval:** Admin calls `approve_rule(rule_id)` with `admin.require_auth()`"

But several gaps exist:

1. **What if a rule is proposed but never approved?** The spec doesn't describe:
   - Garbage collection: Do unapproved rules expire after N days? Or do they accumulate forever?
   - Storage limits: If 1000 unapproved rules exist, does this cause Soroban storage to bloat?

2. **What if the admin is compromised?** The spec says:
   > "Transfer admin role (2-phase: propose + accept)"

   But only mentions this for RuleRegistry in passing. Does AlertRegistry's admin role transfer use the same 2-phase logic? The spec is inconsistent.

3. **What if the community disagrees with an admin decision?** The spec says:
   > "No appeal mechanism in v0.3.0; consider for v0.4.0+"

   But doesn't describe what happens if a rule is rejected. Can the owner re-propose with a different schema? Or is the rule ID permanently blacklisted?

4. **Version updates:** The spec describes `propose_rule_update(owner, rule_id, new_schema)` but doesn't specify:
   - Can the owner update a rule without re-approval? (Implied: yes, but not explicit)
   - If a rule is updated, does AlertRegistry automatically accept the new schema, or must admin re-approve?

5. **Semantic Versioning:** The spec says rules use semver (MAJOR.MINOR.PATCH), but the "auto-bump" logic is unclear:
   > "When `propose_rule_update` is called with a new schema: If new fields are added: bump MINOR version"

   **Who decides if a field is "new"?** Is it automatic (diff the schemas), or manual (owner specifies in the `propose_rule_update` call)?

**Impact:** Implementers won't know how to handle unapproved rules, rule updates, or versioning. Mainnet governance will be ad-hoc and error-prone.

**Recommendation:**

Add these clarifications to the RuleRegistry section:

1. **Garbage Collection Policy:**
   ```
   Unapproved rules (approved=false) are automatically pruned if:
   - Rule is >30 days old (updated_at < now - 30 days), AND
   - Rule has never been approved (approved was never true), AND
   - Rule is not being queried by AlertRegistry
   
   Pruning happens once weekly via a keeper function. (Or: pruning happens on-demand by admin call.)
   ```

2. **Admin Role Transfer:**
   ```
   Transfer admin role using 2-phase (propose + accept) with 7-day expiry, same as AlertRegistry.
   Implement: propose_admin_transfer(new_admin), accept_admin_transfer() with require_auth().
   ```

3. **Rule Update Approval:**
   ```
   When a rule owner calls propose_rule_update(rule_id, new_schema):
   - If rule is already approved: New schema is staged; requires admin approval to activate
   - If rule is not approved: New schema replaces old one; no admin action needed
   - Watcher implementation: Fetch updated schema periodically (every 24h or on manual refresh)
   ```

4. **Versioning Logic:**
   ```
   DECISION: Manual version bumping by owner.
   When proposing an update, owner specifies new version and justification.
   Admin approves based on whether version bump is appropriate.
   
   Implementation: Add version parameter to propose_rule_update(rule_id, new_schema, new_version)
   Contract validates: new_version > current_version (semver comparison)
   ```

5. **Rejected Rules:**
   ```
   If admin rejects a rule:
   - Rule remains in storage with approved=false
   - Owner can call propose_rule_update() to update schema and resubmit
   - No ID blacklisting; same ID can be re-proposed with different schema
   ```

---

### HIGH-007: Stress Test Acceptance Criteria Ambiguous

**Severity:** HIGH  
**Section:** "Mainnet Deployment Plan" — "1. Testnet Stress-Test Checklist"  
**Issue:**

The specification defines 10 stress tests with "Success Criteria" and "Failure Threshold" columns:

| Scenario | Success Criteria | Failure Threshold |
|---|---|---|
| **High-Volume Registration** | All 1000 alerts stored without rejection; zero storage errors | >0 rejections or storage errors → BLOCK mainnet |
| **Large Watcher Set** | Cross-contract calls succeed; zero gas limit errors | Any gas limit hit → BLOCK mainnet |

The problem: **What is "zero"?**

1. **Definition:** Is "zero errors" = 0 errors observed, or <0.01% error rate?
   - If 1 alert out of 1000 fails, is that "zero"?

2. **Measurement:** How are errors measured?
   - By instrumenting the contract (event logs)?
   - By counting transactions that panic?
   - By summing failed RPC calls?

3. **Threshold Enforcement:** The table says "→ BLOCK mainnet" but doesn't specify:
   - Who decides if threshold is met? (A maintainer manually? Automated CI script?)
   - What's the sign-off procedure? (GitHub issue? PR comment?)

4. **Test Harness:** The specification doesn't describe:
   - How to run these tests (CI script? Local tool? Load testing framework?)
   - How many times to run each test (once? thrice to check for flakiness?)
   - How long each test runs (1 hour? 24 hours?)

Example: "Incremental Sync Throughput" test says "Watchers polling `get_alerts_modified_since_ledger` continuously for 24h" but doesn't specify:
- How many watchers?
- How often each watcher polls? (Every second? Every minute?)
- What's the expected ledger advancement rate?

**Impact:** Stress tests will be run inconsistently. One maintainer might pass tests that another would reject. Mainnet deployment readiness will be subjective.

**Recommendation:**

Add a **Stress Test Harness Specification** to the document:

1. **Test Infrastructure:**
   ```
   Tests will be implemented in: contracts/integration-tests/stress_tests.rs
   Each test is a Rust async function using the Soroban test framework.
   Tests are triggered by: .github/workflows/stress-test.yml
   Tests run on every merge to main (or manually via workflow dispatch).
   Timeouts: Each test has a 1-hour timeout; tests that need 24h run nightly.
   ```

2. **Measurement & Reporting:**
   ```
   After each test:
   - Collect metrics into a JSON file: stress_test_results.json
   - Parse against defined thresholds
   - If any threshold missed: Fail the workflow; block merge to main
   - Post results as GitHub check (green checkmark or red X)
   ```

3. **Example: High-Volume Registration Test**
   ```
   - Register 1000 alerts sequentially from different owners
   - Measure: Total success count, total failure count, errors per error type
   - Success Criteria: success_count == 1000 AND failure_count == 0
   - Failure Threshold: failure_count > 0 OR error_rate > 0%
   - Latency baseline: p95 latency < 5s per registration
   ```

4. **Mainnet Sign-Off Checklist:**
   ```
   Before mainnet deployment:
   - [ ] All 10 stress tests PASS (results attached to GitHub release)
   - [ ] No test flakiness detected (each test run 3x; pass all 3x)
   - [ ] Latency baselines established (p95/p99 recorded for future comparison)
   - [ ] Maintainer manually reviewed results and approved
   ```

---

### HIGH-008: Python/Go SDK Dependencies Unverified

**Severity:** HIGH  
**Section:** HIGH-003 (Python and Go SDKs) — "Dependencies" subsections  
**Issue:**

The specification lists required dependencies:

**Python:**
- `stellar-sdk>=12.0.0`
- `stellar-base` (re-exported by stellar-sdk)
- `pydantic>=2.0` (optional)
- `httpx>=0.25.0`

**Go:**
- `github.com/stellar/go/clients/horizonclient`
- `github.com/stellar/go/support/errors`

Problems:

1. **Version Compatibility Not Verified:**
   - `stellar-sdk>=12.0.0` is very permissive; which versions have been tested?
   - `httpx>=0.25.0` was released in 2024; is it compatible with Python 3.8+?
   - Go's `horizonclient` is part of `stellar/go` monorepo; what version of the monorepo?

2. **Missing Dependencies:**
   - Python SDK needs a way to build transactions (XDR encoding). Is `stellar-base` sufficient, or is additional tooling needed?
   - Go SDK needs to serialize/deserialize Soroban data types. The spec doesn't mention this dependency.

3. **Transitive Dependency Risk:**
   - What if `httpx` or `stellar-sdk` have breaking changes? No lock file strategy mentioned.

4. **Soroban-Specific Tooling:**
   - Both SDKs need to interact with Soroban contracts (not just classic Stellar). Is `stellar-sdk` enough for this, or is separate `stellar-sdk-soroban` tooling needed?

**Impact:** SDK development will encounter version conflicts. Build failures. Maintainers will waste time debugging dependency mismatches.

**Recommendation:**

Add a **Dependency Matrix** to the specification:

```
## Python SDK Dependency Matrix

| Dependency | Min Version | Tested Against | Rationale |
|---|---|---|---|
| stellar-sdk | 12.0.0 | 12.5.x | Soroban contract support added in 12.x |
| stellar-base | N/A | Via stellar-sdk | XDR serialization for Stellar account operations |
| httpx | 0.25.0 | 0.26.x | Async HTTP client for Soroban RPC calls |
| pydantic | 2.0 | 2.5.x | (Optional) Type validation for request/response |

## Go SDK Dependency Matrix

| Dependency | Min Version | Module Path | Rationale |
|---|---|---|---|
| stellar/go | v11.3.0 | github.com/stellar/go | Transaction building, XDR support, Horizon client |
| context | stdlib | N/A | Cancelation/timeouts for RPC calls |

## Verification Procedure

1. Update all dependencies to latest compatible version
2. Run full SDK test suite (unit + integration)
3. Record versions in go.mod, pyproject.toml
4. Pin versions in CI (use lock files: requirements.txt for Python, go.sum for Go)
5. Weekly GitHub Dependabot checks for security updates
6. Monthly manual review of transitive dependency updates
```

---

### HIGH-009: TypeScript Bindings Regeneration Workflow Incomplete

**Severity:** HIGH  
**Section:** "TypeScript Bindings Update Workflow" (at end of specification)  
**Issue:**

The specification describes auto-regeneration of TypeScript bindings:

> "Runs: `stellar contract bindings typescript --wasm contracts/.../alert_registry.wasm --output-dir bindings/alert-registry/src/_generated`"
> "Auto-generated code committed to `bindings/alert-registry/src/_generated/`"

But the implementation details are missing:

1. **Hand-Written Extensions:** The project has a hand-written `networks.ts` and index re-exports (mentioned in project analysis). How are these maintained without conflicts?
   - When `_generated/index.ts` is regenerated, will it overwrite the hand-written networks map?
   - Is the hand-written code in a separate file that imports from `_generated`?

2. **Versioning Alignment:** The spec says:
   > "npm package version: Bump to `@QingQosh/alert-registry-bindings@0.3.0`"

   But doesn't specify:
   - When does the version bump happen? (After contract is tagged? Before?)
   - Who decides the SDK version? (Always match contract version, or independent?)

3. **Breaking Changes:**
   - Fix #197 adds `querier.require_auth()` to 8 functions, changing their signatures
   - Fix #198 adds `querier` parameter to 2 functions
   - **Will the generated TypeScript types reflect these changes automatically?**
   - Or must the hand-written types be updated manually?

4. **Publishing Pipeline:**
   - The spec says bindings are published on GitHub release, but doesn't describe the automation
   - Is there a `.github/workflows/publish-bindings.yml` that publishes to npm?
   - What triggers it? (Git tag? Manual dispatch?)

**Impact:** TypeScript developers will have broken or out-of-sync bindings. Manual bindings updates will be missed. npm packages will be unpublished or have stale types.

**Recommendation:**

Create a **TypeScript Bindings Management Workflow** document (or add to specification):

```markdown
## TypeScript Bindings Regeneration and Publishing

### File Structure

\`\`\`
bindings/alert-registry/
├── src/
│   ├── _generated/
│   │   ├── index.ts           (AUTO-GENERATED: stellar contract bindings typescript)
│   │   ├── alert_registry.ts  (AUTO-GENERATED)
│   │   └── types.ts           (AUTO-GENERATED)
│   ├── index.ts               (HAND-WRITTEN: re-exports + networks map)
│   ├── networks.ts            (HAND-WRITTEN: testnet/mainnet configuration)
│   ├── errors.ts              (HAND-WRITTEN: custom error handling)
│   └── types.ts               (HAND-WRITTEN: type extensions, if needed)
├── package.json               (version matches contract version)
└── CHANGELOG.md
\`\`\`

### Regeneration Workflow (CI)

**Trigger:** When AlertRegistry contract WASM changes

**Steps:**
1. Run: \`stellar contract bindings typescript --wasm contracts/alert-registry/target/wasm32-unknown-unknown/release/alert_registry.wasm --output-dir bindings/alert-registry/src/_generated\`
2. Validate: Compare \`_generated/index.ts\` against golden file (catch ABI breakage)
3. Check conflicts: Ensure no overlap between hand-written and generated code
4. Update version: Bump \`bindings/alert-registry/package.json\` to match contract version
5. Commit: \`git add bindings/alert-registry/src/_generated && git commit -m "Regenerate bindings for v0.3.0"\`

**Guard Rails:**
- If ABI changed (golden file comparison fails): Block merge, alert maintainers
- If hand-written/generated files have overlapping exports: Block merge, manual resolution needed

### Version Alignment

| Component | Version Strategy |
|---|---|
| Contract (alert-registry) | Semantic version (0.3.0) |
| TypeScript bindings (@QingQosh/alert-registry-bindings) | Match contract version |
| npm package | Publish as 0.3.0 when contract is tagged as v0.3.0 |

**Example Timeline:**
- Contract: Tag git commit as \`v0.3.0\`
- CI: Generate bindings, update package.json version to 0.3.0
- CI: Run \`npm publish\` to publish @QingQosh/alert-registry-bindings@0.3.0
- GitHub Release: Create release with contract WASM + npm package link

### Hand-Written Extensions (networks.ts, errors.ts)

These files are NOT regenerated. They import types from \`_generated\`:

\`\`\`typescript
// networks.ts
import type { AlertConfig } from './_generated/types';

export const networks = {
  testnet: {
    contractId: 'CXXX...',
    rpcUrl: 'https://soroban-testnet.stellar.org',
  },
  mainnet: {
    contractId: 'CZZZZ...',
    rpcUrl: 'https://soroban-mainnet.stellar.org',
  },
};
\`\`\`

\`\`\`typescript
// index.ts (HAND-WRITTEN re-export)
export * from './_generated/index';
export * from './_generated/types';
export { networks } from './networks';
export * from './errors';
\`\`\`

**Maintenance:**
- On contract upgrade: Manually update \`contractId\` in \`networks.ts\`
- If new errors are added: Manually add error handlers to \`errors.ts\`
- Regenerate \`_generated/\` automatically; hand-written files remain stable

### Publishing Checklist

Before npm publish:
- [ ] Contract WASM tagged as vX.Y.Z
- [ ] Bindings regenerated (\`_generated/\` updated)
- [ ] \`package.json\` version bumped to X.Y.Z
- [ ] \`networks.ts\` updated with new contract address (if mainnet)
- [ ] CHANGELOG.md updated with breaking changes (if any)
- [ ] npm publish triggered
- [ ] Post-publish smoke test validates against testnet/mainnet
```

---

### MEDIUM-001: Admin Key Custody and Governance Workflow Missing

**Severity:** MEDIUM  
**Section:** "Mainnet Deployment Plan" — "5. Success Metrics" & mainnet sign-off checklist  
**Issue:**

The specification includes this mainnet sign-off requirement:

> "- [ ] Admin key custody: SECURED and DOCUMENTED"

But doesn't describe:
1. **How should the admin key be secured?** (Multi-sig? Hardware wallet? Escrow?)
2. **How many signers?** (2-of-3? 3-of-5?)
3. **Who are the signers?** (Core maintainers? DAO members? Community vote?)
4. **Backup/Recovery:** If a signer loses their key, what's the recovery procedure?
5. **Documentation:** What should be documented? (Key derivation? Signer identities? Backup locations?)

This is a **critical operational requirement** but lacks implementation detail.

**Impact:** Mainnet deployment will stall waiting for key setup. Security practices will be ad-hoc. If a key is compromised, there's no documented recovery procedure.

**Recommendation:**

Add a **Admin Key Management Policy** section:

```markdown
## Admin Key Management (Mainnet)

### Key Setup (Bootstrap)

1. **Multi-Sig Configuration:** 2-of-3 multi-sig (recommended)
   - Signer 1: Core Maintainer A (hardware wallet)
   - Signer 2: Core Maintainer B (hardware wallet)
   - Signer 3: Community DAO Treasury (time-locked)

2. **Key Derivation:**
   - Generate keys using stellar-cli: \`stellar keys generate <name>\`
   - Keys stored in hardware wallet (Ledger/Trezor recommended)
   - Never store private keys in code or CI/CD

3. **Multi-Sig Account Setup:**
   - Create Stellar account with 2-of-3 threshold
   - Fund with minimum balance (XLM) for contract operations
   - Document account address (public): \`GXXX...\`

### Key Storage & Access Control

| Key | Storage | Access | Rotation |
|---|---|---|---|
| Admin private key (signer 1) | Hardware wallet (Ledger) | Core maintainer A only | Annual or on-demand |
| Admin private key (signer 2) | Hardware wallet (Trezor) | Core maintainer B only | Annual or on-demand |
| Admin public address | GitHub docs | Public | Never |

### Incident Response

**Scenario: Signer key is compromised**

1. Immediately notify all signers
2. Propose new admin transfer via 2-phase (require 2 of remaining signers)
3. Accept new admin on recovery key
4. Revoke compromised signer via multi-sig vote

**Scenario: Signer is unavailable (lost hardware wallet, etc.)**

1. Remaining signer proposes new admin transfer to a new multi-sig (2-of-2 with replacements)
2. Wait for 7-day expiry on the proposal
3. After expiry, if no acceptance, initiate rollback or governance process

### Documentation

Store in encrypted wiki or GitHub private repo:
- [ ] Multi-sig account setup details (threshold, signers, public address)
- [ ] Hardware wallet model and firmware versions
- [ ] Key derivation BIP32 paths
- [ ] Backup recovery seed phrases (encrypted, stored separately)
- [ ] Emergency contact info for signers
- [ ] Incident response procedure

```

---

### MEDIUM-002: RuleRegistry Governance Upgrade Path Too Vague

**Severity:** MEDIUM  
**Section:** HIGH-002 (RuleRegistry) — "Approval Mechanism (v0.3.0)"  
**Issue:**

The specification describes v0.3.0 using single-admin approval:

> "v0.3.0 launches with minimal governance overhead (single trusted admin)"

But then says:

> "Governance upgrade path: v0.4.0 or later can transition to multi-sig or DAO (out of scope for this upgrade)"

This leaves a gap:
1. **What's the trigger for v0.4.0 governance upgrade?** (N approved rules? Time elapsed? Community vote?)
2. **How will rules be migrated from single-admin to multi-sig/DAO?**
3. **What happens to pending rule approvals during the transition?**

The specification doesn't describe a versioning or upgrade path for RuleRegistry itself. Unlike AlertRegistry (which has v0.2.0, v0.3.0 plan), RuleRegistry is assumed to be deployed once and persist forever. But if governance changes, what happens to the contract?

**Impact:** After v0.3.0 mainnet launch, maintainers won't know how to transition to decentralized governance without a major, disruptive contract redeploy.

**Recommendation:**

Add a **RuleRegistry Governance Roadmap** section:

```markdown
## RuleRegistry Governance Roadmap

### v0.3.0 (Single Admin)

- Admin: Single hardcoded address
- Approval: Admin calls \`approve_rule(rule_id)\`
- No appeal or voting mechanism

**Transition Trigger to v0.4.0:** When ≥20 custom rules approved OR ≥3 months after mainnet launch

### v0.4.0 (Multi-Admin or DAO)

**Option A: Multi-Admin (Recommended)**
- 3+ admins (core team members)
- Approval requires 2-of-3 vote (multi-sig)
- Admins can be added/removed via proposal + community vote

**Option B: DAO Governance**
- Rules approved via on-chain vote (separate governance contract)
- Any token holder can vote
- Requires Stellar DAO infrastructure (to be defined)

### Migration Path (v0.3.0 → v0.4.0)

**Step 1:** Deploy new RuleRegistry v0.4.0 contract with multi-admin support

**Step 2:** Data migration (manually or via migration contract):
- Copy all approved rules from v0.3.0 to v0.4.0
- Copy all unapproved rules
- Set admin list to first multi-sig

**Step 3:** Governance transition:
- AlertRegistry admin calls \`set_rule_registry(new_contract_address)\`
- New v0.4.0 RuleRegistry becomes active
- v0.3.0 RuleRegistry is deprecated (data remains on-chain, but not polled)

**Step 4:** Community governance:
- First vote: Elect 3 multi-admins
- Second vote: Define approval voting threshold (2-of-3? 3-of-3?)

### Timeline

- v0.3.0 mainnet launch: Weeks 1–4
- Community feedback: Weeks 5–12
- v0.4.0 development: Weeks 13–16
- v0.4.0 testnet: Weeks 17–20
- v0.4.0 mainnet: Week 21+

```

---

### MEDIUM-003: Tier 1 & Tier 2 Features Not Clearly Scoped

**Severity:** MEDIUM  
**Section:** "SECTION 2: TIER 1 HIGH-PRIORITY FEATURES" overview & scope  
**Issue:**

The specification defines Tier 1 as:

> "With security fixes deployed and mainnet live, Tier 1 features unlock extensibility, multi-language support, and ecosystem participation."

But doesn't clearly state:
1. **Are Tier 1 features REQUIRED for mainnet launch, or OPTIONAL?**
   - Spec says "1–3 months post-mainnet," implying they're post-launch
   - But also says they're "ESSENTIAL for global adoption"

2. **Which Tier 1 features are blocking Tier 2?**
   - Can Python/Go SDKs (HIGH-003) ship independently of RuleRegistry (HIGH-002)?
   - Or must they all ship together in v0.4.0?

3. **What about Tier 2?**
   - The specification mentions "Tier 2 (Medium-Priority): Governance, operations, and ecosystem hardening (6+ months)"
   - But doesn't define what's in Tier 2, what's the target, or what success looks like

**Impact:** Roadmap prioritization is unclear. Developers won't know what to work on after Tier 0 lands. Community expectations won't be managed.

**Recommendation:**

Add a **Roadmap & Sequencing Table** at the top of the specification:

```markdown
## Upgrade Roadmap Summary

| Tier | Features | Timeline | Blockers | Mainnet Requirement |
|---|---|---|---|---|
| **Tier 0** | Fix #197, Fix #198, mainnet deployment | Weeks 1–4 | Security audit required | YES (mandatory) |
| **Tier 1a** | RuleRegistry (HIGH-002) | Weeks 5–12 | Tier 0 complete | NO (optional; enables custom rules) |
| **Tier 1b** | Python/Go SDKs (HIGH-003) | Weeks 5–12 | Tier 0 complete | NO (optional; improves DX) |
| **Tier 1c** | Governance documentation | Weeks 5–8 | Tier 0 complete | NO (required for transparency) |
| **Tier 2** | Scaling, monitoring, ecosystem SDKs | Weeks 13+ | Tier 1 features proven | NO (long-term hardening) |

### Sequencing

- **Weeks 1–4:** Tier 0 (security fixes, mainnet deployment)
- **Weeks 5–12:** Tier 1 features in parallel (3 concurrent workstreams)
  - Team A: RuleRegistry development & testnet integration
  - Team B: Python/Go SDK implementation
  - Team C: Governance & process documentation
- **Week 12:** Consensus decision: Merge all Tier 1 features into v0.4.0 or stagger releases
- **Weeks 13+:** Tier 2 (monitoring, advanced features)

### Tier 1 Feature Dependencies

```
Tier 0 (Mainnet)
  ├─ Tier 1a: RuleRegistry (independent)
  ├─ Tier 1b: Python/Go SDKs (independent; depends on Tier 0 TypeScript bindings)
  └─ Tier 1c: Governance docs (independent; documents Tier 0 decisions)
```

All Tier 1 features are independent of each other but depend on Tier 0.

### Tier 2 Definition (Placeholder)

Tier 2 features will be defined post-Tier 1 based on community feedback. Examples:

- [ ] GraphQL/REST API for easy web integration
- [ ] Official Stellar Watcher reference implementation
- [ ] Monitoring dashboard & alerting runbook
- [ ] Kotlin SDK (if Java ecosystem adoption emerges)
- [ ] Advanced rule patterns (regex, machine learning)
- [ ] Decentralized governance for rule approval

```

---

### MEDIUM-004: Integration Test & CI/CD Gaps for SDK Changes

**Severity:** MEDIUM  
**Section:** "Testing Strategy" (HIGH-002) & "CI Integration" (HIGH-003)  
**Issue:**

The specification describes testing for RuleRegistry and SDKs but doesn't specify:

1. **Integration Test Environment:**
   - How are Python/Go SDKs tested against live contracts?
   - Do they use a testnet deployment, or local Soroban simulator?
   - How long do integration tests take? (Can they run on every PR, or only nightly?)

2. **CI/CD Pipeline:**
   - The specification mentions `.github/workflows/regenerate-bindings.yml` but doesn't define it
   - How are Python/Go SDK tests triggered? (On every commit? Nightly? Weekly?)
   - What's the failure handling? (Block PR merge if SDK tests fail?)

3. **Cross-Contract Testing:**
   - Integration tests for AlertRegistry + RuleRegistry interaction need both contracts deployed on testnet
   - How is this managed in CI? (Deploy both contracts in a setup step? Use static deployed addresses?)

4. **SDK Backwards Compatibility:**
   - If Python SDK v0.3.0 works with AlertRegistry v0.3.0 but breaks with v0.4.0, how is this detected?
   - Should each SDK version specify compatible contract versions?

**Impact:** SDK development will be slow. Regressions will slip through. Integration failures will be discovered late.

**Recommendation:**

Add a **SDK Testing & CI/CD Strategy** section:

```markdown
## SDK Testing & CI/CD Integration

### Test Levels

1. **Unit Tests** (fast, every commit)
   - Python: \`pytest tests/test_*.py\`
   - Go: \`go test ./...\`
   - No external dependencies; mock Stellar SDK

2. **Integration Tests** (slower, on PR + nightly)
   - Test SDK against live testnet deployment of AlertRegistry + WatcherRegistry
   - Python: Use AsyncClient with testnet configured
   - Go: Use Client with testnet configured
   - Requires pre-deployed contracts; use stable addresses

3. **Contract Interaction Tests** (post-contract changes)
   - When AlertRegistry or RuleRegistry changes, re-run full integration suite
   - Verify SDKs still work with new contract versions
   - Update SDK version if breaking changes detected

### CI/CD Workflows

**.github/workflows/test-python-sdk.yml**
\`\`\`yaml
name: Python SDK Tests
on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: 3.11
      - run: pip install -r sdks/python/requirements-dev.txt
      - run: cd sdks/python && pytest tests/

  integration:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' || github.event.pull_request.draft == false
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r sdks/python/requirements-dev.txt
      - run: cd sdks/python && pytest tests/integration/ -m testnet
        env:
          TESTNET_CONTRACT_ID: CXXX...  # Stable contract address
          TESTNET_RPC_URL: https://soroban-testnet.stellar.org
\`\`\`

**.github/workflows/test-go-sdk.yml**
\`\`\`yaml
name: Go SDK Tests
on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
      - run: cd sdks/go && go test -v ./...

  integration:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' || github.event.pull_request.draft == false
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
      - run: cd sdks/go && go test -v -tags=integration ./...
        env:
          TESTNET_CONTRACT_ID: CXXX...
          TESTNET_RPC_URL: https://soroban-testnet.stellar.org
\`\`\`

### Contract Version Compatibility Matrix

Each SDK release should document compatible contract versions:

**overstand-py@0.3.0**
- AlertRegistry: v0.3.0
- WatcherRegistry: v0.1.0
- RuleRegistry: Not supported (requires v0.4.0+)

**overstand-py@0.4.0**
- AlertRegistry: v0.4.0
- WatcherRegistry: v0.1.0
- RuleRegistry: v0.1.0

Documentation: Add to SDK README or compatibility matrix.

```

---

## Verified Assumptions

Based on reading of `project-analysis.md` and `upgrade-specification.md`, the following assumptions are **verified or confirmed:**

1. ✅ **Soroban SDK Version (25.3.0)** is current and integrated with CI
2. ✅ **TypeScript Bindings Exist** and are published to npm
3. ✅ **Mainnet Deployment Has Not Yet Occurred** (testnet-only currently)
4. ✅ **Security Issues #197 and #198** are documented as authentication/gating gaps
5. ✅ **AlertRegistry v0.2.0 is Production-Ready** (comprehensive test coverage)
6. ✅ **WatcherRegistry v0.1.0 Exists** and supports multi-admin
7. ✅ **CI/CD Infrastructure is Mature** (14 workflows covering build, test, security, deploy)
8. ✅ **Storage Efficiency is a Priority** (WASM size <60KB, TTL management)

---

## Unverified / Wrong Assumptions

Based on reading of specifications, these assumptions **require verification before implementation:**

1. ⚠️ **"Gated reads with unauthenticated querier already exist in v0.2.0"** — Not verified. Project analysis describes them as security gaps, but upgrade spec frames them as new features. **ACTION:** Read v0.2.0 contract source.

2. ⚠️ **"Python SDK can use `stellar-sdk>=12.0.0` without issues"** — Version and compatibility not verified. **ACTION:** Check stellar-sdk CHANGELOG for breaking changes, Soroban support.

3. ⚠️ **"Go's `horizonclient` supports Soroban RPC calls"** — Assumed but not verified. May require separate Soroban-specific client. **ACTION:** Check stellar/go GitHub for Soroban RPC support.

4. ⚠️ **"RuleRegistry can handle 100 custom rules without hitting storage limits"** — Estimated but not validated. **ACTION:** Run storage load test on testnet (similar to stress tests).

5. ⚠️ **"Admin key multi-sig setup is standard practice in Stellar ecosystem"** — Assumed but no reference implementation provided. **ACTION:** Link to Stellar Security Guide or provide example.

6. ⚠️ **"Testnet migration with manual alert re-registration is acceptable UX"** — No user feedback provided. Could be burdensome. **ACTION:** Get feedback from testnet watcher operators.

7. ⚠️ **"Bindings regeneration via `stellar contract bindings typescript` won't overwrite hand-written code"** — Assumed but not tested. **ACTION:** Verify stellar CLI behavior; add guard rails to CI.

---

## Summary Table

| Finding ID | Severity | Issue | File Section | Recommendation |
|---|---|---|---|---|
| HIGH-001 | HIGH | Tier 0 framing contradiction (NEW vs. FIX) | Tier 0 Overview | Clarify: are gated reads new features or bug fixes to existing code? |
| HIGH-002 | HIGH | Function count mismatch (8 vs. 10) | Fix #197 & #198 | Use precise language: "8 gated reads + 2 incremental sync = 10 total" |
| HIGH-003 | HIGH | Cross-contract failure handling contradicts itself | Tier 0 & HIGH-002 | Choose fail-closed or fail-open explicitly and apply consistently |
| HIGH-004 | HIGH | Watcher-gating enable/disable semantics unspecified | Fix #197 & #198 | Create definitive Gating Matrix (which reads are gated?) |
| HIGH-005 | HIGH | Testnet migration path too vague | Migration Strategy | Provide migration scripts, communication plan, detailed cutover procedure |
| HIGH-006 | HIGH | RuleRegistry approval workflow incomplete | HIGH-002 Approval | Clarify: rule expiration, updates, versioning, approval reversal |
| HIGH-007 | HIGH | Stress test acceptance criteria ambiguous | Mainnet Deployment | Define test harness, measurements, thresholds, sign-off procedure |
| HIGH-008 | HIGH | Python/Go SDK dependencies unverified | HIGH-003 Dependencies | Create dependency matrix with tested versions and compatibility rules |
| HIGH-009 | HIGH | TypeScript bindings regeneration workflow incomplete | TS Bindings Workflow | Document hand-written extensions, version alignment, conflict resolution |
| MEDIUM-001 | MEDIUM | Admin key custody missing | Mainnet Sign-Off | Add key management policy, recovery procedures, documentation |
| MEDIUM-002 | MEDIUM | RuleRegistry governance upgrade path vague | RuleRegistry Approval | Define v0.4.0 governance transition (multi-admin/DAO) and migration |
| MEDIUM-003 | MEDIUM | Tier 1 & Tier 2 features not clearly scoped | Tier 1 Overview | Create roadmap table with sequencing, blockers, mainnet requirements |
| MEDIUM-004 | MEDIUM | Integration test & CI/CD gaps for SDKs | Testing Strategy | Define SDK test levels, CI workflows, contract version compatibility |

---

## Verdict

**CHANGES_REQUESTED**

**Rationale:** 9 HIGH-severity findings require resolution before implementation. These are not minor clarifications; they address fundamental design decisions (fail-open vs. fail-closed), scope ambiguities (which functions are affected?), and operational gaps (how are watchers migrated?). Proceeding without resolution would result in inconsistent implementation, incomplete testing, and brittle mainnet deployment.

**Recommended Next Steps:**

1. **Address all HIGH findings** (HIGH-001 through HIGH-009) with concrete clarifications
2. **Prioritize HIGH-001 and HIGH-003** first (they cascade to other decisions)
3. **Verify unverified assumptions** (check v0.2.0 source, SDK versions, storage limits)
4. **Create detailed sub-specifications** for:
   - Gating Matrix (HIGH-004)
   - Testnet Migration Guide (HIGH-005)
   - RuleRegistry Workflow (HIGH-006)
   - Stress Test Harness (HIGH-007)
   - SDK Dependency & CI/CD Strategy (HIGH-008, MEDIUM-004)
   - Admin Key Management (MEDIUM-001)
   - Governance Roadmap (MEDIUM-002)
   - Feature Roadmap (MEDIUM-003)
5. **Re-submit specification for review** after changes are incorporated

---

**End of Design Review**
