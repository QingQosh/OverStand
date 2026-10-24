# OverStand Project Analysis Report

**Project:** OverStand (Soroban Smart Contracts for On-Chain Alert Configuration)  
**Organization:** [QingQosh](https://github.com/QingQosh)  
**Repository:** https://github.com/QingQosh/OverStand  
**License:** MIT (root) / Apache-2.0 (contracts)  
**Last Updated:** Analysis reflects current main branch state  

---

## 1. Executive Summary

**OverStand** is a production-grade Soroban smart contract platform that enables decentralized, on-chain alert configuration and watcher registry management on the Stellar network. It serves as the foundational infrastructure layer for the tx-watch ecosystem—a system designed to allow token issuers, protocol developers, and transaction monitors to register alerts for specific contract events and have authorized watcher nodes poll and deliver webhooks when those events occur.

### Current State
- **Active Development:** v0.2.0 (AlertRegistry) with v0.1.0 WatcherRegistry, both deployed on Stellar Testnet
- **Production-Ready Architecture:** Mature security model with Stellar `require_auth()` enforcement, 2-phase transfers, timelock governance, and pause/guardian circuit-breaker controls
- **Comprehensive CI/CD:** 14 GitHub Actions workflows covering full build, test, fuzz, mutation testing, property-based testing, MSRV validation, WASM size constraints, golden file specifications, and end-to-end deployment
- **TypeScript Bindings Published:** npm packages `@QingQosh/alert-registry-bindings` and `@QingQosh/watcher-registry-bindings` published to npm; post-publish smoke tests validate live testnet deployments
- **Storage-Optimized:** Contracts maintain WASM binary under 60KB post-optimization; support incremental sync with `get_alerts_modified_since_ledger`

### Global Recognition Potential
OverStand has the **technical foundation** for ecosystem-wide adoption: it solves a core problem (federated alert configuration), uses proven Stellar patterns, and includes robust testing and security infrastructure. However, **three critical gaps** block broader adoption:

1. **Security Issues Unresolved:** Issues #197 and #198 expose authentication bypasses in read operations that must be fixed before production mainnet deployment
2. **Limited Rule Extensibility:** Only 5 hardcoded rule descriptors (transfer/mint/burn/approve/clawback) with no extensibility path—new event types require contract upgrades
3. **Mainnet Deployment Blocked:** ContractId fields remain empty in TypeScript bindings; mainnet deployment has not yet occurred

Fixing these three, completing mainnet deployment with proper governance documentation, and adding SDKs for Python/Go would position OverStand as the **de facto standard** for decentralized event monitoring on Stellar.

---

## 2. Architecture Overview

### On-Chain Components

#### AlertRegistry (v0.2.0, Soroban SDK 25.3.0)
**Primary Role:** Stores alert configurations on-chain, keyed by watched contract address.

**Core Features:**
- **Alert Lifecycle Management:** Register, update (rules/label/webhook/target contract), deactivate, remove, renew TTL
- **CRUD Operations:** Full ownership semantics with owner-authenticated mutations; admin-gated suspension/unlock
- **Query APIs:** Single-alert lookups; paginated queries by contract or owner; incremental sync via ledger sequence
- **Rule Validation:** 5 fixed descriptors (rule:transfer, rule:mint, rule:burn, rule:approve, rule:clawback); max 5 rules per alert; no duplicates
- **TTL Management:** Default 24-hour TTL; configurable bump (max 31 days); tombstone retention for 7 days (incremental sync safety)
- **Per-Owner Limits:** Configurable owner alert ceiling; per-contract active-alert ceilings (v0.2.0)
- **Webhook Rotation:** 2-phase propose/confirm for zero-downtime webhook migration
- **Admin Transfers:** 2-phase (propose/accept) with 7-day expiry for admin role handoff
- **Alert Ownership Transfers:** 2-phase (propose/accept) pending transfer with expiry
- **Pagination:** All list getters support offset/limit (max page size 100)
- **Event Emission:** Full event catalog (topics: alert.{register, update, remove, renew, bump, deactivate, unlock_admin, suspend_admin, transfer_own, transfer_new, wh_prop, wh_conf, expire})

**Storage Layout:**
- `DataKey::Alert(id)` → full `AlertConfig`
- `DataKey::AlertActive(id)` → bool (separate for lightweight active-flag checks)
- `DataKey::AlertTarget(id)` → target contract (used by prune operations)
- `DataKey::OwnerIndex(owner)` → Vec<u64> (alert IDs)
- `DataKey::OwnerLiveCount(owner)` → count of non-removed alerts
- `DataKey::OwnerActiveCount(owner)` → count of active (non-removed, active=true) alerts
- `DataKey::ContractIndex(target)` → Vec<u64> (alert IDs watching target)
- `DataKey::ContractLiveCount(target)` → count of non-removed alerts for target
- Incremental sync support: `get_alerts_modified_since_ledger` backed by `RemovedAlert` tombstones
- Instance storage: admin address, pending admin transfer, optional WatcherRegistry address, per-owner/per-contract/global alert limits

#### WatcherRegistry (v0.1.0, Soroban SDK 25.3.0)
**Primary Role:** Maintains authorized watcher node addresses; optional gating layer for AlertRegistry reads.

**Core Features:**
- **Multi-Admin Set:** Support co-admins; add/remove admins
- **Admin Transfers:** 2-phase (propose/accept) with 7-day expiry
- **Watcher Management:** Register, remove, replace watchers; bulk clear
- **Authorization Checks:** Deterministic `is_watcher_authorized(watcher)` for on-chain gating
- **Deprecated Alias:** `is_authorized` kept for backwards compatibility; scheduled removal in v0.3.0

**Storage Layout:**
- Instance storage: primary admin, co-admin set, pending admin transfer, watchers set
- Minimal; optimized for read-heavy queries

### Optional Cross-Contract Integration
When AlertRegistry admin calls `set_watcher_registry(watcher_registry_address)`, gated read queries (`get_alert`, `get_alert_active`, `get_alerts_for_contract`, `get_active_alerts_for_contract`, `get_alerts_by_owner`, `get_contract_alerts_paginated`, `get_alerts_by_owner_paginated`, `get_active_contract_alerts_paged`) invoke `WatcherRegistry::is_watcher_authorized(querier)`. Unauthenticated queries fail with `NotAWatcher`. (This is the "watcher-gating" feature; it is optional and not enabled by default.)

**Critical Caveat (Open Issue #198):** `get_alerts_modified_since` and `get_alerts_modified_since_ledger` do NOT perform watcher gating—they bypass the check entirely, allowing any querier to fetch recently modified alert list. This is a security gap.

### Off-Chain Components (Not in This Repository)
- **tx-watch-core** (https://github.com/Tx-wat/stellar-txwatch-core): Watcher node engine; polls Horizon, matches rules, fires webhooks
- **stellar-txwatch-web** (https://github.com/Tx-wat/stellar-txwatch-web): Web dashboard for alert management and monitoring

### Data Flow Diagram

```
Owner/Admin
    ├─ register_alert(target, rules, webhook_hash)
    │  └─ [stored in AlertRegistry]
    │
Admin (WatcherRegistry)
    ├─ register_watcher(watcher_address)
    │  └─ [stored in WatcherRegistry]
    │
Watcher Node (off-chain)
    ├─ poll Horizon: GET /accounts/{target}/transactions
    ├─ fetch gated read: AlertRegistry::get_alerts_for_contract(watcher_addr, target)
    │  └─ [cross-contract call: is_watcher_authorized(watcher_addr) if gating enabled]
    ├─ match rules locally (transfer/mint/burn/approve/clawback)
    └─ POST webhook URL to downstream integration
       └─ [downstream: webhook receiver processes event]
```

---

## 3. Current Capabilities Matrix

| Capability | AlertRegistry | WatcherRegistry | Status | Notes |
|---|---|---|---|---|
| **Alert Registration** | ✅ | — | Production | `register_alert` with owner auth, rules validation, TTL setup |
| **Alert Updates** | ✅ | — | Production | Update rules, label, webhook, target contract; deactivate; remove |
| **Webhook Rotation** | ✅ | — | Production | 2-phase propose/confirm; 7-day expiry on proposal |
| **Ownership Transfer** | ✅ | — | Production | 2-phase propose/accept with 7-day expiry |
| **Admin Transfer** | ✅ | ✅ | Production | 2-phase propose/accept with 7-day expiry (both contracts) |
| **Per-Owner Alert Limit** | ✅ | — | Production | Configurable by admin; enforced on register/transfer |
| **Per-Contract Active Limit** | ✅ | — | v0.2.0 New | Configurable by admin; enforced on register |
| **Global Alert Limit** | ✅ | — | v0.2.0 New | Configurable by admin; enforced on register |
| **Watcher Registration** | — | ✅ | Production | Multi-admin, co-admin support |
| **Watcher Authorization Check** | — | ✅ | Production | Fast O(1) lookup; read-only |
| **Read Gating (Optional)** | ✅ | — | Partial | Enabled by `set_watcher_registry`; gated reads check `is_watcher_authorized` (**but see issue #198**) |
| **Incremental Sync** | ✅ | — | Production | `get_alerts_modified_since_ledger`; tombstone retention for 7 days |
| **Pagination** | ✅ | — | Production | offset/limit on all list getters; max page size 100 |
| **TTL Management** | ✅ | — | Production | Owner-authenticated renew; permissionless keeper bump (max 31 days) |
| **Admin Suspend/Unlock** | ✅ | — | v0.2.0 New | Admin can suspend alert; owner cannot reactivate until admin unlocks |
| **Bulk Deactivation** | ✅ | — | Production | `deactivate_all_alerts` (owner-authenticated); resumable with cursor |
| **Bulk Watcher Registration** | — | ✅ | Production | `register_watchers` (batched, admin-authenticated) |
| **Event Emission** | ✅ | ✅ | Production | Full event catalog; enables off-chain indexing |
| **Cross-Contract Auth** | ✅ | ✅ | Production | Soroban `require_auth()` for all mutations; protocol-level re-entrancy safety |
| **Rule Extensibility** | ❌ | N/A | Not Supported | Only 5 hardcoded descriptors; new event types require contract upgrade |
| **Custom Rule Patterns** | ❌ | N/A | Not Supported | No support for NFTs (SEP-0053), custom contracts, or arbitrary patterns |

---

## 4. Existing Strengths

### Security & Authorization
1. **Protocol-Level Auth:** Stellar `require_auth()` enforces all mutations; no custom signature verification needed
2. **Re-Entrancy Safety:** Soroban atomic execution prevents classic callback re-entrancy
3. **2-Phase Transfers:** Admin, ownership, and webhook rotations use propose/accept to prevent key loss from accidents
4. **Timelock Governance:** 7-day expiry windows on pending transfers; cancellable at any time
5. **Admin Suspend/Lock Circuit-Breaker:** Admin can immediately suspend an alert; owner cannot reactivate until admin unlocks
6. **Principle of Least Privilege:** Read operations unchecked until watcher-gating is enabled; mutations require owner/admin auth

### Code Quality & Testing
1. **Comprehensive Test Suite:**
   - Unit tests (happy path, rejection cases, edge cases) in `tests.rs`
   - Property-based tests (proptest) in `proptests.rs` at 10,000 cases
   - Regression tests (`regression_tests.rs`)
   - Error code tests (`error_codes.rs`)
   - libFuzzer fuzz targets for `validate_rule` and `register_alert`
   - Integration tests in `contracts/integration-tests`

2. **CI/CD Rigor:** 14 GitHub Actions workflows covering
   - WASM build optimization (target <60KB)
   - Cargo test + Clippy (warnings as errors)
   - rustdoc link validation
   - Code formatting check
   - Doc comment check
   - MSRV verification (Rust 1.88)
   - Instance storage key audit
   - README snippet validation
   - TypeScript bindings build/test
   - Weekly mutation testing (cargo-mutants)
   - Nightly proptest at 10,000 cases
   - Daily libFuzzer runs
   - Semantic specification golden file check (detects silent ABI breakage)
   - Link checking (lychee)
   - Testnet deployment monitoring
   - End-to-end bindings tests
   - Deployment automation (testnet + mainnet)

3. **Code Coverage:** cargo-llvm-cov integrated; badge on README; results pushed to Codecov

4. **Linting & Style:** Clippy pedantic warnings as errors; custom allow-list for Soroban-generated code

### Developer Experience
1. **TypeScript Bindings:** Auto-generated from WASM; hand-maintained index re-exporting types + networks map
2. **Comprehensive CLI Cheatsheet:** Extensive `stellar contract invoke` examples for every function in README
3. **JavaScript SDK Examples:** Full Transaction builder patterns shown
4. **Deployment Automation:** `scripts/deploy.sh` and `scripts/verify.sh` for testnet/mainnet
5. **Well-Organized Documentation:** Docs directory with architecture guides, compatibility matrix, event catalog, TTL rationale
6. **Clear Upgrade Path:** Documented in CONTRIBUTING.md and `docs/compatibility.md`

### Storage & Performance
1. **Storage Efficient:** BytesN<32> for webhook hashes; TTL culling; event emission for off-chain indexing
2. **WASM Size Budget:** Contracts stay <60KB post-optimization (enforced in CI)
3. **Incremental Sync:** `get_alerts_modified_since_ledger` enables watcher resumption from last known ledger
4. **Pagination:** All list queries support offset/limit to cap memory/CPU per call

### Deployment & Governance
1. **Testnet Deployed & Verified:** Both contracts live on Stellar Testnet with daily liveness checks
2. **Mainnet Readiness Checklist:** CONTRIBUTING.md includes release sequence (git tag → testnet deploy → GitHub release → npm publish)
3. **CHANGELOG Discipline:** Kept up-to-date; linked diff per release
4. **Semantic Versioning:** Contract versions tracked in `contractmeta!`; npm bindings semver'd

---

## 5. Identified Gaps & Weaknesses

### Security Issues (CRITICAL)

#### #197: Gated Reads Trust an Unauthenticated `querier` Parameter
**Severity:** HIGH  
**Description:** When watcher-gating is enabled via `set_watcher_registry`, read queries (`get_alert`, `get_alert_active`, `get_alerts_for_contract`, etc.) accept a `querier` address parameter and check if it is an authorized watcher via cross-contract call to `WatcherRegistry::is_watcher_authorized`. However, the `querier` parameter is **not authenticated by Stellar**—the caller can pass any address. A malicious caller could impersonate an authorized watcher, pass its address as `querier`, and receive protected alert data without owning that watcher key.

**Implication:** Read gating is ineffective; any querier can read any alert by knowing a watcher's address or guessing.

**Mitigation:** Require the querier to authenticate itself (call `require_auth()` on querier), making the impersonation impossible.

#### #198: `get_alerts_modified_since` Bypasses Watcher-Gating
**Severity:** HIGH  
**Description:** The incremental sync functions `get_alerts_modified_since` and `get_alerts_modified_since_ledger` do NOT perform watcher-gating checks. An unauthenticated caller can fetch the full list of recently modified alerts (with timestamps and ledger sequences) without any authorization check, even if `set_watcher_registry` is configured.

**Implication:** Incremental sync leaks alert metadata (existence, modification timing) to the public; watcher-gating is incomplete.

**Mitigation:** Add `querier` parameter to both functions; perform watcher-gating check before returning results.

### Extensibility Issues (HIGH)

#### Closed Rule Descriptor List
**Description:** Only 5 hardcoded rule descriptors are supported: `rule:transfer`, `rule:mint`, `rule:burn`, `rule:approve`, `rule:clawback`. All are Stellar SEP-0041 (fungible token) event patterns. To add monitoring for:
- NFT (SEP-0053) events
- Custom contract events
- Cross-protocol event patterns

...a new contract version and testnet/mainnet redeploy are required. There is no extensibility mechanism (e.g., registry pattern, ruleset versioning, custom predicate expressions).

**Implication:** OverStand cannot monitor the full Stellar ecosystem without repeated contract upgrades; it is **not suitable for long-lived, community-driven alert systems**.

**Desired Approach (Post-Mainnet):** Introduce a `RuleRegistry` contract that stores user-defined or community-curated rule patterns; AlertRegistry reads rule metadata from it at query time. Requires contract upgrade but enables ecosystem participation.

#### Max Rules Per Alert (5) and Max Watchers (100)
**Description:** Hard limits of 5 rules per alert and 100 watchers per registry (derived from storage/gas constraints in Soroban).

**Implication:** Monitoring complex multi-contract systems may require multiple alert registrations. At >100 watchers, the registry must fork or the ecosystem adopts a different platform.

**Mitigation:** Document limits clearly; plan v0.3.0 with higher thresholds if gas/storage improvements occur in Soroban SDK.

### Deployment & Versioning Gaps (HIGH)

#### Mainnet Deployment Blocked
**Description:** `DEPLOYMENTS.md` shows contract addresses deployed on Stellar Testnet; mainnet columns are placeholders ("CXXXXXXX..."). TypeScript bindings' `networks.mainnet.contractId` is empty string.

**Implication:** No production-grade OverStand on mainnet yet; enterprises cannot use for real monitoring. Testnet resets periodically, making testnet deployments unsuitable for production pilots.

**Root Cause:** Likely awaiting security fixes (#197, #198) and stakeholder coordination.

#### Version Mismatch
**Description:** AlertRegistry is v0.2.0; WatcherRegistry is v0.1.0. TypeScript bindings have matching versions, but the mismatch signals incomplete synchronization.

**Implication:** Unclear if WatcherRegistry has received v0.2.0 feature parity. Compatibility matrix in README shows v0.2.0 as "Active Development" but does not clarify WatcherRegistry stability.

### Ecosystem Integration Gaps (HIGH)

#### No SDK Beyond TypeScript
**Description:** TypeScript bindings exist and are published to npm. No official Python, Go, Rust, or Kotlin SDKs; developers on other platforms must hand-craft calls or use generic Soroban tools.

**Implication:** Platform barriers; limits adoption outside JavaScript/TypeScript ecosystem.

#### Off-Chain Infrastructure Not in Repo
**Description:** tx-watch-core (watcher engine) and stellar-txwatch-web (dashboard) are separate repos under Tx-wat organization. OverStand repo does not include or reference them tightly; sister repo links are in README and CONTRIBUTING but no integration tests or version pinning.

**Implication:** OverStand is a building block without full end-to-end example; new integrators must clone, configure, and deploy three separate repos.

#### No GraphQL or REST API
**Description:** Users must invoke contracts directly via Stellar SDK or CLI; no abstraction layer. No official indexer/subgraph for Stellar.

**Implication:** High barrier for web/mobile integrators; they must understand Soroban, TX building, and Stellar auth.

#### No On-Chain Event Indexer
**Description:** Events are emitted but there is no dedicated indexer contract or ecosystem service that aggregates them. Watchers rely on Horizon transaction feeds and local rule matching.

**Implication:** Reduces real-time responsiveness; tight coupling to Horizon API; no cross-contract event query language.

### Developer Experience Gaps (MEDIUM)

#### No Webhook Verification
**Description:** Contract stores SHA-256 hash of webhook URL; watcher fetches the URL and fires POST. No built-in mechanism to verify the webhook URL is authentic or to rotate certificates/auth tokens.

**Implication:** Webhook endpoints are static; if one is compromised, attackers can intercept alerts. No TLS/signature verification.

#### No Rate Limiting at Contract Level
**Description:** No per-alert webhook rate limit or per-owner webhook quota. A malicious watcher could fire the same webhook 1000x in one ledger.

**Implication:** Webhook endpoints are exposed to potential DDoS from watchers; owners must implement their own rate-limiting middleware.

#### No Governance Documentation
**Description:** No formal process for adding new rule descriptors, updating limits, or deprecating functions. README mentions removal of `is_authorized` in v0.3.0, but there is no EIP-like structured governance proposal process.

**Implication:** Unclear how ecosystem consensus is reached on feature decisions.

#### Deprecated Functions Not Yet Removed
**Description:** `is_authorized` in WatcherRegistry and unbounded list getters in AlertRegistry (`get_alerts_for_contract`, `get_alerts_by_owner`) are marked as deprecated but not removed. They remain in the contract and get emitted in TypeScript bindings.

**Implication:** Legacy surface area increases maintenance burden; bindings are cluttered with deprecated APIs.

#### Limited Documentation on Rule Semantics
**Description:** Five rule descriptors are listed (transfer/mint/burn/approve/clawback), but the README does not explain the exact conditions under which each rule fires (e.g., does `rule:transfer` fire on zero-value transfers?). Watcher implementers must infer from contract code.

**Implication:** Rules are under-specified; watcher implementations may diverge.

### Operational Gaps (MEDIUM)

#### No Formal Security Audit
**Description:** SECURITY.md outlines incident response procedures and vulnerability reporting; however, no public record of a third-party security audit. Codebase is well-tested but not vetted by external firm.

**Implication:** Enterprises deploying to mainnet may demand audit before use.

#### Testnet Ephemeral State
**Description:** Stellar Testnet resets periodically; `DEPLOYMENTS.md` includes a daily liveness check script, but contract state is wiped on reset. Not suitable for long-running pilots.

**Implication:** Organizations running production-like pilots on testnet face data loss.

#### No Monitoring/Alerting Runbook
**Description:** SECURITY.md includes incident response for key compromise, but no operational runbook for detecting anomalies (e.g., unusual alert registration spikes, watcher churn, webhook failure cascades).

**Implication:** Operators lack visibility into ecosystem health.

---

## 6. Open Issues Summary

| Issue | Severity | Category | Status |
|---|---|---|---|
| #197: Gated Reads Trust Unauthenticated `querier` | CRITICAL | Security | Open |
| #198: `get_alerts_modified_since` Bypasses Watcher-Gating | CRITICAL | Security | Open |
| Mainnet Deployment Blocked | CRITICAL | Deployment | Waiting for Security Fixes |
| Version Mismatch (AR v0.2.0 vs WR v0.1.0) | HIGH | Versioning | Undocumented |
| Closed Rule Descriptor List | HIGH | Extensibility | Design Limitation |
| No Rule Semantics Documentation | MEDIUM | Documentation | Gap |
| Deprecated Functions Not Removed | MEDIUM | Technical Debt | Planned (v0.3.0) |
| No Official SDKs Beyond TypeScript | HIGH | Ecosystem | Gap |
| No Governance Process Documented | MEDIUM | Governance | Gap |
| No Third-Party Security Audit | MEDIUM | Trust | Gap |

---

## 7. CI/CD Assessment

### Covered
✅ **Full WASM Build & Optimization** — Release profile with LTO, codegen-units=1, symbol stripping; binary size <60KB enforced  
✅ **Comprehensive Testing** — Unit, property-based, fuzz, regression, error codes, integration tests all passing  
✅ **Linting & Format** — Clippy pedantic (warnings as errors), rustfmt, doc link validation  
✅ **MSRV Verification** — Rust 1.88 validation on every push  
✅ **Specification Golden Files** — ABI interface check catches silent breaking changes  
✅ **TypeScript Bindings** — Auto-generated, built, tested, published on release  
✅ **Deployment Automation** — `deploy-testnet.yml`, `deploy-mainnet.yml` with versioning, WASM hash tracking  
✅ **Post-Publish Smoke Test** — Bindings tested against live testnet after npm publish  
✅ **Code Coverage** — cargo-llvm-cov integrated; coverage badge on README  
✅ **Security Audit Tools** — cargo-audit (enforced in CI), dependency-review, shellcheck, actionlint, spell check  
✅ **Link Checking** — Lychee validates all README and docs links  
✅ **Testnet Liveness Monitoring** — Daily check-testnet-deployments job validates deployed addresses  

### Gaps
❌ **No Manual Security Audit Results** — No third-party audit report attached to releases  
❌ **No Load Testing** — No benchmarks for query latency under high watcher count  
❌ **No Soak Testing** — Long-running contract behavior not tested over weeks/months  
❌ **No Upgrade Migration Testing** — No CI step that tests upgrade path from older contract version  
❌ **Limited Alerting** — No automatic notification to maintainers if testnet deployment goes stale  

---

## 8. Dependency Analysis

### Rust Dependencies
| Crate | Version | Purpose | Audit Status |
|---|---|---|---|
| `soroban-sdk` | 25.3.0 | Core Soroban contract framework | ✅ Audited by Stellar SDF |
| `proptest` | 1.6.x | Property-based testing | ✅ Active, well-maintained |
| `arbitrary` | 1.3.2 | Fuzz test input generation | ✅ Active |

**MSRV:** Rust 1.88 (enforced in CI)  
**Toolchain:** 1.90.0 (current; allows security patches)  

### TypeScript/Node Dependencies
| Package | Version | Purpose |
|---|---|---|
| `@stellar/stellar-sdk` | ^17.0.1 | Core Stellar SDK for bindings |
| `typescript` | ^7.0.2 | TypeScript compiler |
| `vitest` | ^5.0.0 | Test runner |

**Build System:** npm scripts in `package.json`; generated code via `stellar contract bindings typescript`  

### CI Tooling
- Stellar CLI: v28.0.0 (pinned in `DEPLOYMENTS.md` note)
- cargo-llvm-cov: For code coverage
- cargo-mutants: Weekly mutation testing
- lychee: Link validation
- typos: Spell checking

### Known Vulnerabilities
**Active** (as of analysis):
- **RUSTSEC-2026-0009** (time crate): Addressed in Rust 1.88+ toolchain; no longer fixable with earlier MSRV

**None reported** in root Cargo.lock as of last CI run (audited every push).

---

## 9. Stellar Ecosystem Positioning

### Competitive Landscape

**OverStand's Niche:**
- **On-chain alert configuration storage** — contracts own their alert config data; no off-chain third-party service holds it
- **Watcher registry + gating** — decentralized authorization for who can query alerts
- **Incremental sync support** — efficient resumption for watcher nodes

**Comparable Tools:**
1. **Horizon Event Stream + Custom Webhook Service** — Simple; real-time, but centralized; no on-chain alert config
2. **Stellar Soroban-based Event Indexing Proposals** — Academic; no production release; focus on indexing not alerts
3. **Traditional Crypto Monitoring (Alchemy, Defender, QuickNode)** — Robust; multi-chain; built-in webhooks; centralized; requires custody/API key
4. **Stellar-Specific Monitors (Lumerin, StellarChain)** — Limited to Stellar; may focus on DEX activity, not custom contracts

### Advantages
- ✅ **Decentralized Config Storage** — No platform dependency; alerts live on-chain
- ✅ **Auditable Rules** — All alert definitions on-chain; cryptographically verifiable
- ✅ **Watcher Decoupling** — Multiple watchers can compete; owners not locked to one service
- ✅ **Stellar-Native** — Uses Stellar auth, contracts, storage; no bridge/wrapper needed

### Disadvantages
- ❌ **Limited Rule Vocabulary** — 5 hardcoded descriptors; cannot monitor arbitrary contract events or custom logic
- ❌ **No Mainnet Yet** — Testnet only; no production track record
- ❌ **Manual Watcher Operation** — No hosted watcher service; operators must run and maintain their own nodes
- ❌ **Webhook Delivery Guarantees** — Watcher nodes are responsible; no SLA or retry logic at contract level
- ❌ **No SDK Diversity** — TypeScript only; other languages face integration friction

### Positioning for Global Recognition

**Tier 1 (Current):** Stella ecosystem development tool  
**Tier 2 (1-3 months, post-security fixes + mainnet):** de facto standard for decentralized on-chain alerts on Stellar  
**Tier 3 (6-12 months, with SDK expansion + governance docs):** Ecosystem standard adopted by major Stellar projects (token issuers, DEXs, protocols)  

**To reach Tier 3:**
1. Fix security issues #197, #198
2. Deploy mainnet with versioning governance
3. Publish Python, Go, Kotlin SDKs
4. Add extensible rule registry (v0.3.0)
5. Document rule semantics and watcher reference implementation
6. Run formal security audit

---

## 10. Upgrade Priority Matrix

### Tier 0: Blockers for Mainnet (Fix Immediately)

**🔴 CRITICAL-001: Fix #197 — Authenticate `querier` Parameter**
- **Scope:** AlertRegistry contract + TypeScript bindings
- **Change:** Add `require_auth(querier)` to all gated read functions
- **Rationale:** Without authentication, watcher-gating is a false security measure; any caller can impersonate authorized watchers
- **Effort:** 4 hours
- **Testing:** New unit tests for each gated read; regression tests for backward-compatible signature (should be safe since only authenticated queriers are valid)
- **Mainnet Blocking:** YES — do not deploy gated reads without this fix
- **Affected Functions:** `get_alert`, `get_alert_active`, `get_alerts_for_contract`, `get_active_alerts_for_contract`, `get_alerts_by_owner`, `get_contract_alerts_paginated`, `get_alerts_by_owner_paginated`, `get_active_contract_alerts_paged`

**🔴 CRITICAL-002: Fix #198 — Add Watcher-Gating to Incremental Sync**
- **Scope:** AlertRegistry contract + TypeScript bindings
- **Change:** Add `querier` parameter to `get_alerts_modified_since` and `get_alerts_modified_since_ledger`; perform watcher-gating check before returning results
- **Rationale:** Incremental sync must obey the same gating rules as other reads; leaking modification metadata is a privacy breach
- **Effort:** 4 hours
- **Testing:** Property-based tests that verify gating is enforced; integration tests with watcher-gating enabled and disabled
- **Mainnet Blocking:** YES
- **Affected Functions:** `get_alerts_modified_since`, `get_alerts_modified_since_ledger`

**🔴 CRITICAL-003: Plan Mainnet Deployment & Versioning Governance**
- **Scope:** DEPLOYMENTS.md, docs/compatibility.md, CONTRIBUTING.md release sequence
- **Change:** Define mainnet go-live criteria (security fixes, audit, stress-test); reserve mainnet contract addresses; document admin key custody
- **Rationale:** Mainnet deployment is an organizational milestone; must be coordinated with stakeholders (Tx-wat, SDF, ecosystem partners)
- **Effort:** 8 hours (planning, coordination, documentation)
- **Testing:** Dry-run testnet deployment with real-world alert volume simulation
- **Mainnet Blocking:** YES — blocks entire mainnet push
- **Prerequisite:** CRITICAL-001, CRITICAL-002

### Tier 1: High Priority (Pre-Mainnet or Immediately Post-Mainnet)

**🟡 HIGH-001: Security Audit by Third Party**
- **Scope:** Full contract audit (AlertRegistry + WatcherRegistry)
- **Effort:** 2-4 weeks (external firm)
- **Rationale:** Mainnet launches demand external validation; identifies design gaps and edge cases internal review misses
- **Cost:** $15k–$50k (typical Soroban contract audit)
- **Mainnet Blocking:** Optional but strongly recommended; many enterprises will not adopt without it

**🟡 HIGH-002: Add Extensible Rule Descriptor Registry**
- **Scope:** New contract (`RuleRegistry`) + AlertRegistry integration
- **Change:** Separate rule definitions from hardcoded list; allow community to register new rule types; AlertRegistry reads rule metadata at query time
- **Rationale:** Long-term sustainability; ecosystem cannot grow with fixed 5-rule cap
- **Effort:** 40 hours (design, implementation, tests, docs)
- **Breaking:** YES — requires AlertRegistry upgrade; gated by mainnet deployment timeline
- **Version:** v0.3.0
- **Design Sketch:**
  - `RuleRegistry` contract stores rule definitions (descriptor, type, validation logic, metadata)
  - AlertRegistry caches rule metadata in instance storage; refreshes periodically
  - New alert registration queries RuleRegistry to validate rules
  - Admin can propose new rule types; community vote (off-chain or via governance DAO) approves
  - Initial rules pre-populated on deployment

**🟡 HIGH-003: Publish Python and Go SDKs**
- **Scope:** New packages `overstand-py`, `overstand-go`
- **Change:** Auto-generate from ABI JSON; provide idiomatic examples for each language
- **Rationale:** Opens adoption beyond TypeScript; Python is dominant in data/monitoring tooling; Go dominates backend services
- **Effort:** 20 hours each (generation + testing + docs)
- **Mainnet Blocking:** NO, but blocks broader adoption; recommended for Tier 2

**🟡 HIGH-004: Raise Hard Limits (Rules, Watchers)**
- **Scope:** Contract constants + storage layout
- **Change:** Increase `MAX_RULES_PER_ALERT` from 5 to 10; increase watcher count limit from 100 to 500 (if Soroban SDK gas/storage improves)
- **Rationale:** Eliminates artificial constraints; supports complex multi-contract monitoring
- **Effort:** 4 hours (design) + 8 hours (testing under new limits)
- **Mainnet Blocking:** NO, but improves usability
- **Prerequisite:** Stress-test on mainnet to confirm gas costs remain acceptable

**🟡 HIGH-005: Document Rule Semantics**
- **Scope:** docs/rules.md (new file)
- **Change:** Specify exact conditions for each rule descriptor (transfer/mint/burn/approve/clawback); provide test vectors; explain interaction with SEP-0041
- **Rationale:** Watcher implementers must have unambiguous spec; prevents divergent behavior
- **Effort:** 8 hours (spec + examples)
- **Mainnet Blocking:** NO, but critical for watcher compatibility

### Tier 2: Medium Priority (1-3 Months Post-Mainnet)

**🟠 MEDIUM-001: Governance & Feature Proposal Process**
- **Scope:** docs/governance.md (new file)
- **Change:** Define RFC process for rule additions, limit changes, major upgrades; establish decision-making body (e.g., SDF + core integrators)
- **Rationale:** Ecosystem-wide tool needs community input; formal process reduces politics
- **Effort:** 6 hours (docs + process definition)

**🟠 MEDIUM-002: Webhooks Security Hardening**
- **Scope:** Off-chain guidelines + contract docs
- **Change:** Document best practices for webhook verification (TLS, HMAC signing, rate limiting); consider contract-side rate-limit fields (v0.3.0)
- **Rationale:** Reduces webhook endpoint compromise risk
- **Effort:** 4 hours (docs)

**🟠 MEDIUM-003: Operational Runbook & Monitoring Guide**
- **Scope:** docs/operations.md (new file)
- **Change:** Document mainnet health checks, anomaly detection (alert spike, watcher churn), incident response; provide sample monitoring queries
- **Effort:** 12 hours

**🟠 MEDIUM-004: TypeScript Bindings Cleanup**
- **Scope:** Bindings package.json + generated code
- **Change:** Remove `is_authorized` alias (deprecated); remove unbounded list getters if paginated variants are mature
- **Rationale:** Reduces surface area; signals migration path to users
- **Effort:** 2 hours (update generation template; test)
- **Breaking:** YES; bumps to v1.0.0

**🟠 MEDIUM-005: Deprecation Timelines & Removal Cadence**
- **Scope:** docs/compatibility.md + CONTRIBUTING.md
- **Change:** Define schedule: deprecation warning (1 release), removal in (N releases); explicit dates for v0.3.0 removals
- **Rationale:** User expectations; prevents shock removals
- **Effort:** 2 hours

### Tier 3: Low Priority (Nice-to-Have, 6+ Months)

**🟢 LOW-001: GraphQL API / REST Wrapper**
- **Scope:** Optional off-chain service (not in repo)
- **Change:** Provide containerized service that wraps contract calls in GraphQL/REST
- **Rationale:** Reduces barrier for web/mobile integrators
- **Effort:** 60 hours (API design, implementation, docs)

**🟢 LOW-002: Web Dashboard (UI) for Alert Management**
- **Scope:** Companion to stellar-txwatch-web; owned by integrators or community
- **Rationale:** Visual interface for non-technical users
- **Effort:** 100+ hours (out of scope for core OverStand)

**🟢 LOW-003: Soroban Event Indexer / Subgraph**
- **Scope:** Optional off-chain indexer (not in repo)
- **Change:** Index AlertRegistry + WatcherRegistry events; expose via GraphQL
- **Rationale:** Near-real-time event queries; independent of Horizon API
- **Effort:** 80 hours

**🟢 LOW-004: Stress & Load Testing Suite**
- **Scope:** Integration tests + performance benchmarks
- **Change:** Deploy to testnet; run load test (1000 alerts, 50 watchers, 100 concurrent queries); measure latency/gas
- **Effort:** 16 hours

---

## 11. Key Files Reference

### Critical Implementation Files

| File Path | Purpose | Change Impact |
|---|---|---|
| `contracts/alert-registry/src/lib.rs` | AlertRegistry main logic | CRITICAL-001, CRITICAL-002, HIGH-002, HIGH-004 |
| `contracts/watcher-registry/src/lib.rs` | WatcherRegistry main logic | CRITICAL-001 (indirectly), HIGH-004 |
| `bindings/alert-registry/src/index.ts` | TS bindings entry point | CRITICAL-001, CRITICAL-002, MEDIUM-004 |
| `bindings/alert-registry/package.json` | TS bindings metadata | Version bump tracking |
| `contracts/alert-registry/src/tests.rs` | AlertRegistry unit tests | All feature changes |
| `contracts/alert-registry/src/proptests.rs` | Property-based tests | Regression prevention |
| `.github/workflows/ci.yml` | Main CI pipeline | All quality gates |
| `.github/workflows/deploy-mainnet.yml` | Mainnet deploy automation | CRITICAL-003 |

### Configuration & Deployment

| File Path | Purpose | Change Impact |
|---|---|---|
| `Cargo.toml` | Workspace dependencies | Soroban SDK version updates |
| `rust-toolchain.toml` | Rust toolchain pin | MSRV bumps |
| `DEPLOYMENTS.md` | Contract addresses by network | CRITICAL-003 (mainnet addresses) |
| `CONTRIBUTING.md` | Release process | CRITICAL-003 (governance) |
| `scripts/deploy.sh` | Testnet/mainnet deploy | CRITICAL-003 (mainnet workflow) |
| `scripts/verify.sh` | Contract verification | Mainnet deployment step |

### Documentation

| File Path | Purpose | Change Impact |
|---|---|---|
| `docs/alert-registry.md` | AlertRegistry API reference | HIGH-005, MEDIUM-001 |
| `docs/watcher-registry.md` | WatcherRegistry API reference | All changes |
| `docs/compatibility.md` | Compatibility matrix & versioning | CRITICAL-003, MEDIUM-005 |
| `docs/events.md` | Event catalog | Event schema changes |
| `docs/testing.md` | Testing strategy | Test infrastructure updates |
| `docs/ttl.md` | TTL & storage cleanup rationale | Storage design changes |
| `SECURITY.md` | Vulnerability reporting & incident response | HIGH-001 (audit), NEW: docs/operations.md |
| `README.md` | Overview, quick-start, CLI examples | CRITICAL-001/002 (signature changes) |
| `CHANGELOG.md` | Release notes | All releases |

### Test Infrastructure

| File Path | Purpose | Change Impact |
|---|---|---|
| `contracts/integration-tests/src/lib.rs` | Cross-contract integration tests | All feature changes |
| `contracts/test-utils/src/lib.rs` | Test helper utilities | Test suite refactors |
| `.github/workflows/fuzz.yml` | libFuzzer CI job | Fuzz target additions |

---

## 12. Implementation Strategy Roadmap

### Phase 1: Security Fixes + Mainnet Readiness (2–3 weeks)
**Goal:** Ship v0.2.1 with security patches; unblock mainnet

1. **Week 1:** Implement CRITICAL-001 (#197 fix) + CRITICAL-002 (#198 fix)
   - Update AlertRegistry contract functions
   - Verify property-based tests still pass
   - Update TypeScript bindings
   - Push testnet deployment
   - Tag v0.2.1

2. **Week 2:** Security Audit Procurement (parallel)
   - RFP to 3–5 firms
   - Select auditor
   - Begin audit

3. **Week 2–3:** Mainnet Deployment Planning (CRITICAL-003)
   - Draft deployment runbook
   - Coordinate with stakeholders
   - Reserve mainnet contract IDs
   - Prepare admin key custody procedures
   - Plan deployment timing

### Phase 2: Mainnet Launch (1–2 weeks)
**Goal:** Deploy AlertRegistry + WatcherRegistry to Stellar Mainnet with versioning governance

1. Update DEPLOYMENTS.md with mainnet addresses
2. Publish v0.2.1 GitHub release
3. Publish npm bindings
4. Announce mainnet availability

### Phase 3: Post-Mainnet Enhancements (1–2 months)
**Goal:** Ship v0.3.0 with extensibility and SDK diversity

1. **Week 4–5:** Implement HIGH-002 (Extensible Rule Registry)
   - Design RuleRegistry contract
   - Implement + test
   - Update AlertRegistry to consume rule metadata
   - Deploy to testnet; monitor

2. **Week 6:** Publish Python + Go SDKs (HIGH-003)
3. **Week 7:** Documentation Sprint (HIGH-005, MEDIUM-001)
4. **Week 8:** Tag + release v0.3.0

### Phase 4: Ecosystem Growth (3–6 months)
1. Establish governance process (MEDIUM-001)
2. First ecosystem rule proposal via RFC
3. Operational runbook v1.0 (MEDIUM-003)
4. Community integrators join; grow watcher network

---

## 13. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Security audit uncovers additional #197/#198-class issues | Medium | CRITICAL | Engage experienced auditor early; internal pre-audit code review |
| Mainnet smart contract upgrade complexity (storage layout changes) | Medium | HIGH | Test upgrades on testnet first; document migration path |
| Ecosystem adopts fork/competitor after delays | Medium | MEDIUM | Communicate roadmap transparently; deliver security fixes on schedule |
| Gas/storage limits prevent rule extensibility (RuleRegistry too expensive) | Low | MEDIUM | Stress-test on testnet early; design fallback (simpler registry) |
| Watcher node incompatibility (off-chain code diverges) | Medium | MEDIUM | Publish watcher reference implementation; document rule semantics clearly |
| Mainnet deployment key compromise | Low | CRITICAL | Multi-sig or hardware wallet for admin key; incident response runbook |

---

## 14. Success Metrics

### By End of Phase 1 (Mainnet Unblocked)
- [ ] Issues #197 and #198 fixed and deployed to testnet
- [ ] v0.2.1 released
- [ ] Security audit underway
- [ ] Mainnet deployment date committed publicly

### By End of Phase 2 (Mainnet Live)
- [ ] AlertRegistry + WatcherRegistry live on Stellar Mainnet
- [ ] npm bindings updated with mainnet addresses
- [ ] First production alert registered on mainnet
- [ ] Daily liveness monitoring active

### By End of Phase 3 (v0.3.0)
- [ ] RuleRegistry contract deployed to testnet
- [ ] Python + Go SDKs published (PyPI, pkg.go.dev)
- [ ] Rule semantics documented; watcher reference implementation shared
- [ ] Governance RFC process documented

### By 6–12 Months (Tier 3 Ecosystem Status)
- [ ] 3+ major Stellar projects (token issuers, DEXs) using OverStand
- [ ] 500+ alerts registered on mainnet
- [ ] 10+ community watchers running
- [ ] 5+ rule types extended via RuleRegistry
- [ ] SDK adoption >100k downloads/month (across languages)

---

## Conclusion

**OverStand is a technically sound, production-quality foundation for decentralized on-chain alert infrastructure on Stellar.** Its security model is mature, testing is comprehensive, and CI/CD is robust. However, **three critical blockers** prevent broader adoption:

1. **Security Issues #197 & #198** must be fixed before mainnet deployment.
2. **Mainnet deployment and versioning governance** are required for enterprise adoption.
3. **Rule extensibility and SDK diversity** are needed for ecosystem-wide growth.

The **12-month roadmap** outlined above prioritizes these blockers, then progressively unlocks ecosystem participation through extensibility, governance, and tooling. If executed, OverStand will establish itself as the **de facto standard for decentralized, on-chain alerts on Stellar**—a critical infrastructure piece as the network scales.

**Recommendation:** Commit resources to Phase 1 (security fixes + mainnet) immediately. Delay on these items is the primary risk to ecosystem adoption.
