# RFC: [Title of Proposal]

**Author**: [Your Name/GitHub Handle]  
**Type**: Feature / Rule Descriptor / Hard Limit Change / Breaking Change / Other  
**Created**: [YYYY-MM-DD]  
**Target Release**: v[X.Y.Z] or TBD  
**Status**: Proposal (Submitted for Review)

## Summary

Provide a 2-3 sentence executive summary of the proposal. What problem does it solve? What outcome is expected?

## Problem Statement

Describe the problem or gap this RFC addresses:

- What is the current limitation or issue?
- Who is affected and how?
- What use cases are blocked or hampered?
- Is this a critical issue or a nice-to-have improvement?

**Example**:
> Currently, alerts can only monitor 5 types of events (transfer, mint, burn, approve, clawback). Integrators building sophisticated DEX monitoring tools need to track liquidity pool events, but no rule descriptor exists for this use case.

## Proposed Solution

Describe the solution in sufficient detail for readers to understand the change:

### For New Rule Descriptors

- **Rule name**: `rule:liquidity-pool`
- **Rule semantics**: Fires when liquidity pool `deposit`, `withdrawal`, or `rebalance` operations occur
- **Parameters**: Optional `min_liquidity=<amount>` to filter by pool value
- **Examples**:
  ```
  rule:liquidity-pool              # Any LP operation
  rule:liquidity-pool:min=1000000  # LP operations on pools >= 1M units
  ```

### For Hard Limit Changes

- **Current limit**: [Current value and key]
- **Proposed limit**: [New value]
- **Rationale**: Why is this change necessary?
- **Impact on storage**: How much on-chain storage does this add?
- **Impact on performance**: Will queries or transactions be slower?

**Example**:
> Current: `MAX_RULES_PER_ALERT = 10`
> Proposed: `MAX_RULES_PER_ALERT = 20`
> Rationale: Integrators building complex alert policies need more than 10 rules per alert to express their logic.

### For Breaking Contract Changes

- **Current interface**: [Show existing function signatures or data structures]
- **Proposed interface**: [Show new signatures/structures]
- **Migration path**: How will existing deployments migrate?
- **Deprecation timeline**: When is the old interface removed?

**Example**:
> Current:
> ```rust
> pub fn update_webhook(env: Env, config_id: u64, webhook_hash: BytesN<32>)
> ```
> Proposed:
> ```rust
> pub fn update_webhook(env: Env, config_id: u64, webhook_hash: BytesN<32>, signature: BytesN<64>)
> ```

### For Other Changes

Adapt the above sections to your proposal type. Include mockups, diagrams, or pseudocode if helpful.

## Alternatives Considered

List other approaches you considered and explain why this proposal is better:

1. **Alternative A**: [Description and why it was rejected]
2. **Alternative B**: [Description and why it was rejected]
3. **Alternative C**: [Description and why it was rejected]

**Example**:
> 1. **Hardcode specific LP addresses**: Would require contract updates for each new pool. Rejected because it doesn't scale.
> 2. **Monitor all `invoke` operations**: Too broad; would fire on unrelated contract calls. Rejected because of noise.
> 3. **Proposed: Add `rule:liquidity-pool`**: Scoped to LP events, allows parameter filtering, maintainable. Selected.

## Impact Analysis

### User Impact

- **Backward Compatibility**: Is this change backward compatible?
  - ✅ Compatible (no breaking changes)
  - ⚠️ Soft deprecation (old interface still works but discouraged)
  - ❌ Breaking (old code will fail)
- **Migration effort**: How much work is required for integrators to adopt this change?
  - None / Minimal / Moderate / Significant
- **Behavioral changes**: Will integrators see different alert behavior?

### Operational Impact

- **Deployment effort**: How much work to deploy this change?
  - Testnet / Mainnet / Both
- **Infrastructure changes**: Do operators need new tooling or monitoring?
- **Performance impact**: Will this slow down queries or transactions?
  - **Worst case**: [e.g., "paginated reads with 20 rules may take up to 500ms instead of 200ms"]
- **Storage impact**: How much additional on-chain storage?
  - **Per alert**: [e.g., "~64 bytes"]
  - **Per registry**: [e.g., "~6.4 KB at 100 max alerts"]

### Security Impact

- **New attack vectors**: Does this proposal introduce security concerns?
  - No new concerns / Minimal / Requires mitigation
- **Mitigations**: If concerns exist, describe how they are addressed
- **Security review**: Has this been reviewed by [mention security reviewer if applicable]?

## Implementation

### Implementation Plan

Outline the steps to implement this proposal:

1. **Step 1**: [e.g., "Update Rust contract to add `rule:liquidity-pool` to VALID_RULE_DESCRIPTORS"]
2. **Step 2**: [e.g., "Add tests to cover LP event monitoring"]
3. **Step 3**: [e.g., "Update TypeScript, Python, Go bindings with new rule"]
4. **Step 4**: [e.g., "Deploy to testnet and run integration tests"]
5. **Step 5**: [e.g., "Gather community feedback and update documentation"]
6. **Step 6**: [e.g., "Deploy to mainnet"]

### Timeline

Estimate the implementation timeline:

- **Design & Review**: X days
- **Implementation**: X days
- **Testing & QA**: X days
- **Testnet Deployment**: X days
- **Community Feedback Window**: X days
- **Mainnet Deployment**: X days

**Total**: Approximately X weeks from RFC approval

### Success Metrics

Define how success will be measured:

- [ ] All tests pass (unit, integration, regression)
- [ ] Documentation updated (examples, guides, API reference)
- [ ] Bindings updated and published
- [ ] Testnet deployment stable for 2+ weeks
- [ ] Zero critical security issues found during review
- [ ] At least 2 integrators have tested on testnet
- [ ] [Add project-specific metrics]

### Risks & Mitigations

Identify potential risks:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| [Risk 1] | Low / Medium / High | Low / Medium / High | [Mitigation plan] |
| [Risk 2] | Low / Medium / High | Low / Medium / High | [Mitigation plan] |

## Discussion

### Design Decisions

Explain key design decisions and tradeoffs:

1. **Decision 1**: Why was this chosen over alternatives?
2. **Decision 2**: What tradeoff was accepted and why?

### Open Questions

List any questions or uncertainties:

- [ ] Question 1: [Details]
- [ ] Question 2: [Details]

(Council will help answer during review phase)

## Appendices

### A. Code Examples

Show how users will interact with this change:

```go
// Go SDK example
rules := []string{
    "rule:liquidity-pool",
    "rule:liquidity-pool:min=1000000",
}

registry.RegisterAlert(ctx, owner, "LP Monitor", webhookHash, rules, target, kp)
```

```typescript
// TypeScript example
const rules = [
    "rule:liquidity-pool",
    "rule:liquidity-pool:min=1000000",
];

await contract.register_alert({
    owner: keypair.publicKey(),
    label: "LP Monitor",
    webhook_hash: webhookHash,
    rules,
    target_contract: targetContract,
});
```

### B. Related Issues

- Closes: [GitHub issue #XXX]
- Related: [GitHub issue #XXX]
- Implements: [If this RFC was requested in a previous issue]

### C. References

- [Link to related documentation](https://example.com)
- [Link to related standard or spec](https://example.com)
- [External system or project doing something similar](https://example.com)

---

## RFC Process Checklist

- [ ] Title is clear and specific
- [ ] Summary explains the proposal in 2-3 sentences
- [ ] Problem statement is concrete and evidence-based
- [ ] Proposed solution is detailed enough to understand
- [ ] Alternatives considered are listed with justification
- [ ] Impact analysis covers users, operators, and security
- [ ] Implementation plan is realistic and time-bound
- [ ] Success metrics are measurable
- [ ] Code examples are provided
- [ ] RFC follows the template structure

**Before submitting**: Have you checked for duplicate RFCs? Have you discussed your idea in Discord or forums?

---

**Submission Note**: Copy this entire template into a new GitHub issue (not PR) and fill out all sections. Add the `rfc` label. A maintainer will acknowledge your proposal within 2 business days.
