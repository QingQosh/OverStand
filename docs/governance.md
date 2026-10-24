# OverStand Governance Framework

This document establishes the governance process for OverStand, enabling the community to propose and decide on new features, rule descriptors, hard limit changes, and contract upgrades in a transparent and inclusive manner.

## Table of Contents

1. [Governance Philosophy](#governance-philosophy)
2. [Decision Authority](#decision-authority)
3. [RFC Process](#rfc-process)
4. [What Requires Governance](#what-requires-governance)
5. [Decision Timeline](#decision-timeline)
6. [Dispute Resolution](#dispute-resolution)
7. [Community Participation](#community-participation)

## Governance Philosophy

OverStand is a community-driven project. While the core maintainers (QingQosh organization) steward the codebase and infrastructure, major decisions that affect users and integrators should involve the broader community.

Key principles:

- **Transparency**: All proposals and decisions are documented publicly
- **Inclusivity**: Community members can propose RFCs and participate in discussion
- **Deliberation**: Sufficient time is allocated for community review and feedback
- **Traceability**: All decisions link back to their RFC and discussion thread
- **Stability**: Breaking changes follow a clear deprecation timeline

## Decision Authority

### Decision Body Composition

The **OverStand Governance Council** is responsible for approving RFCs and accepting/rejecting proposals:

- **Core Maintainers** (2-3): QingQosh organization members (e.g., @QingQosh-maintainer, @lead-dev)
- **Community Representatives** (2-3): Ecosystem projects using OverStand (e.g., Stellar validators, payment processors, monitoring tools)
- **Rotating Guest**: Optional seat for prominent community contributor or active RFC author (1 term per decision)

### Voting Rules

- Decisions require **majority approval** (>50% of active council members)
- All members have **equal vote** regardless of role
- **2-week public comment period** is mandatory before voting
- Quorum: At least 3/5 council members must vote

### Role-Specific Responsibilities

**Core Maintainers** are responsible for:
- Maintaining the RFC queue and ensuring timely reviews
- Implementing approved RFCs or coordinating implementation
- Ensuring decisions comply with security and performance constraints
- Enforcing the deprecation timeline for breaking changes

**Community Representatives** are responsible for:
- Representing the interests of their ecosystem or use case
- Identifying gaps and advocating for features
- Testing and providing feedback on implementations
- Suggesting alternative approaches when needed

## RFC Process

### Overview

An **RFC (Request for Comments)** is a structured proposal document that describes a change, its rationale, implications, and implementation plan. All governance-level decisions start as RFCs.

### RFC Stages

```
1. Proposal       ← Author opens GitHub issue with RFC template
2. Review         ← Initial feedback from maintainers (1 week)
3. Public Comment ← 2-week period for community feedback
4. Council Vote   ← Governance council votes (1 week)
5. Accepted/Rejected
   ├─ Accepted    → Moves to implementation track
   └─ Rejected    → Issue is closed with summary
```

### Submitting an RFC

1. **Check for duplicates**: Search [GitHub Issues](https://github.com/QingQosh/OverStand/issues) for similar RFCs
2. **Use the template**: Copy [rfc-template.md](./rfc-template.md) into a new GitHub issue
3. **Fill out all sections**: Include motivation, proposal, alternatives, and implementation notes
4. **Label the issue**: Add label `rfc` and optionally `type:feature`, `type:upgrade`, etc.
5. **Post in community channels**: Announce in Discord or forums (optional but recommended)

### RFC Review Phases

#### Phase 1: Initial Review (Days 1-7)

Maintainers will:
- Acknowledge the proposal within 2 business days
- Identify any missing information or clarifications needed
- Flag any immediate blockers (security, performance, incompatibility)
- Assign one RFC champion (maintainer or community rep) to shepherd the process

#### Phase 2: Public Comment (Days 8-21)

- The RFC label and link are shared on community channels (Discord, forums, email)
- Anyone can comment and raise concerns
- RFC author responds to questions and refines the proposal
- Maintainers synthesize feedback and prepare council summary

#### Phase 3: Council Vote (Days 22-28)

- Governance council meets (asynchronously) to review the RFC
- Members vote: Approve / Request Changes / Reject
- At least 3 council members must vote
- Result is posted publicly within 48 hours of vote completion

### RFC Approval Criteria

An RFC is approved if it:

1. ✅ Solves a real problem or addresses a gap identified by users
2. ✅ Is technically sound and doesn't introduce security vulnerabilities
3. ✅ Is compatible with the project roadmap and vision
4. ✅ Has an implementable design (not vaporware)
5. ✅ Includes a clear timeline and success metrics
6. ✅ Addresses concerns raised during public comment or plans follow-up RFCs

### RFC Rejection Criteria

An RFC may be rejected if:

- ❌ The problem it solves can be addressed more simply (e.g., in documentation, examples)
- ❌ It conflicts with an already-approved RFC or core design principle
- ❌ The implementation burden outweighs the benefit
- ❌ Sufficient consensus is not reached during public comment
- ❌ Security or performance concerns cannot be mitigated

In case of rejection, the issue is closed with a summary explaining why and suggestions for follow-up.

## What Requires Governance

### Requires RFC + Council Vote

These decisions go through the full governance process:

1. **New Rule Descriptors**
   - Adding rules (e.g., `rule:liquidity-pool`)
   - Changing rule semantics or parameters
   - Deprecating or removing rules

2. **Hard Limit Changes**
   - Max rules per alert
   - Max page size
   - Max alert owners
   - Per-owner / per-contract / global alert limits
   - Max watchers

3. **Breaking Contract Upgrades**
   - Changes to contract interface (public function signatures)
   - Changes to data structures stored on-chain
   - Changes to error codes (removals or reinterpretations)
   - Changes to event schemas

4. **Deprecation Timelines**
   - When to emit deprecation warnings
   - When to remove deprecated features
   - Migration path for integrators

5. **Major Feature Additions**
   - New alert types (e.g., rule groups, alert templates)
   - New registry features (e.g., alert scheduling, webhooks v2)
   - New security features (e.g., webhook signature schemes)

### Does NOT Require RFC

These decisions are made by maintainers without council vote:

- **Bug fixes**: Addressing security vulnerabilities or correctness issues
- **Documentation updates**: Clarifications, examples, guides (unless they propose policy changes)
- **Non-breaking SDK improvements**: New optional parameters, helper methods, performance optimizations
- **Internal refactoring**: Code reorganization, test improvements (no external impact)
- **Maintenance**: Dependency updates, CI/CD improvements
- **Minor version bumps**: Bugfix releases (v0.3.1 → v0.3.2)

## Decision Timeline

### Standard RFC Timeline: 28 days

```
Day 0    ← Issue created with RFC template
Days 1-7 ← Initial review phase
Day 7    ← Council pre-meeting (informal check)
Days 8-21 ← Public comment period
Days 22-28 ← Council voting
Day 28   ← Final decision posted
```

### Expedited Timeline: 7 days (Security Only)

For critical security patches or vulnerability disclosures:

```
Day 0-1  ← Issue created with RFC template (marked `security-critical`)
Days 1-3 ← Initial review (fast-tracked)
Days 3-5 ← Abbreviated public comment (security practitioners only)
Days 5-6 ← Council vote (accelerated)
Day 7    ← Decision and implementation begins
```

Expedited RFCs require unanimous council approval. If any council member objects, it reverts to the standard 28-day timeline.

### Implementation Timeline

After approval:

1. **Implementation begins** (within 1 week): Core maintainers or assigned community contributor starts work
2. **Testnet deployment** (within 4 weeks): Change is deployed to Stellar testnet and tested
3. **Stabilization period** (2-4 weeks): Community tests the change, feedback is collected
4. **Mainnet deployment** (6-8 weeks from approval): Change is deployed to Stellar mainnet

For breaking changes, the timeline is extended to allow integrators time to migrate:

- **Deprecation announced** at approval time
- **Deprecation warning** emitted in testnet (v0.X.0)
- **Grace period** (minimum 8 weeks): Integrators migrate in this window
- **Breaking change** shipped in next major version (v1.0.0 or v0.Y.0)

## Dispute Resolution

### Disagreement During Public Comment

If significant concerns are raised during the public comment phase:

1. RFC author revises the proposal to address concerns
2. If concerns are not addressed, maintainers may extend the public comment period by 1 week
3. Council members vote with the revised proposal

### Tie or No Consensus

If the council vote is tied or reaches no consensus:

1. The RFC champion (assigned maintainer) facilitates a live discussion
2. Council members explain their reasoning and concerns
3. One more vote is held after discussion
4. If still tied, the RFC is **rejected** (status quo wins)

### Appeal Process

If a community member strongly disagrees with a decision, they can:

1. Request a written explanation from the council (within 7 days)
2. Identify new information or use cases not addressed in the RFC
3. Propose a revised RFC (earliest: 2 months after rejection)

Revised RFCs that introduce new perspectives or data are considered on their merits.

## Community Participation

### How to Get Involved

1. **Watch RFCs**: Star the [OverStand repository](https://github.com/QingQosh/OverStand) and enable notifications for issues labeled `rfc`
2. **Comment on RFCs**: Join discussions and share your use cases, concerns, or ideas
3. **Become a Community Representative**: Demonstrate expertise and engagement; maintainers may nominate you for a council seat
4. **Propose RFCs**: Submit your own proposals following the template and process

### Community Channels

- **GitHub Issues**: [OverStand/issues](https://github.com/QingQosh/OverStand/issues) - Formal proposals and decisions
- **Discord**: [Stellar Community Discord](https://discord.gg/stellar) - Real-time discussion
- **Forums**: [Stellar Developers Forum](https://stellar.org/community) - Long-form discussions
- **Twitter**: [@QingQosh](https://twitter.com/QingQosh) - Announcements

### Council Nominations

Community members interested in representing their ecosystem or use case on the governance council can:

1. Demonstrate deep engagement with OverStand (e.g., published integrations, active issue participation)
2. Express interest in a council seat via email to governance@qingqosh.org
3. Participate in a trial period (2-3 decisions) before formal nomination
4. If accepted, commit to a 6-month term with option to renew

Council seats rotate quarterly to ensure fresh perspectives and prevent seat-warming.

## Examples

### Example 1: New Rule Descriptor RFC

**Title**: `[RFC] Add rule:liquidity-pool for monitoring LP operations`

**What triggers RFC**: New rule descriptor
**Timeline**: Standard (28 days)
**Who proposes**: Community member from a DEX integration
**Expected outcome**: Rule added to VALID_RULE_DESCRIPTORS, deployed in v0.4.0

### Example 2: Hard Limit Change RFC

**Title**: `[RFC] Raise MAX_RULES_PER_ALERT from 10 to 20`

**What triggers RFC**: Hard limit change
**Timeline**: Standard (28 days)
**Who proposes**: Maintainers based on community feedback
**Expected outcome**: Limit changed in v0.4.0, testnet 4 weeks, mainnet 6 weeks

### Example 3: Breaking Change RFC

**Title**: `[RFC] Migrate AlertConfig webhook_hash to cryptographic signature`

**What triggers RFC**: Breaking contract upgrade
**Timeline**: Standard (28 days) + 8-week grace period
**Who proposes**: Core maintainers
**Expected outcome**: Deprecated in v0.3.x, breaking change in v0.4.0

## Governance History

This document was established in v0.3.0 as part of Phase 3: Ecosystem Growth & Governance.

| Date | Decision | RFC | Outcome |
|---|---|---|---|
| TBD | First governance council formed | N/A | Council seated |
| TBD | First RFC accepted | TBD | Awaiting implementation |

## Questions?

For questions about the governance process:

- **GitHub**: Comment on the [governance issue](https://github.com/QingQosh/OverStand/issues/new?template=rfc) or open a new issue
- **Email**: governance@qingqosh.org
- **Discord**: Ask in #overstand channel

---

**Last Updated**: October 24, 2026  
**Version**: 1.0  
**Status**: Active
