# Rule Descriptors Specification

This document provides an unambiguous specification of all rule descriptors supported by OverStand's AlertRegistry contract. It is intended for:

- **Watcher implementation teams** building off-chain rule evaluation logic
- **Integration developers** understanding what events trigger alerts
- **Future extensibility planning** for new rule types

## Overview

A rule descriptor is a string that tells the watcher which event to monitor. The AlertRegistry stores these descriptors verbatim; the watcher interprets them and matches against Stellar contract events.

All rule descriptors follow the format: `rule:<base>` or `rule:<base>:min=<amount>`, where:
- `<base>` is one of the five recognized rule types (see below)
- `:min=<amount>` is an optional parameter specifying a minimum token amount (for transfer, mint, approve events)

## Rule Descriptors

### 1. Transfer Events

**Descriptor:** `rule:transfer` or `rule:transfer:min=<amount>`

**Stellar SEP-0041 Event Pattern:**

The contract emits a `transfer` topic with `Contract` source, containing:
```
Topic: "transfer"
Topic: from_address (Address)
Topic: to_address (Address)
Data: amount (i128)
```

**Exact Match Condition:**

Trigger when any contract event matches ALL of:
1. Event source is `Contract` (i.e., a smart contract, not Stellar native)
2. Event topic name is exactly `"transfer"` (case-sensitive)
3. Event has exactly 3 topics: `["transfer", <from>, <to>]`
4. Event data is a single i128 value (the amount)
5. If `min` parameter is present: `amount >= min` (numeric comparison as i128)

**Edge Cases:**

- **Zero-value transfers** (`amount == 0`): These are valid and should match `rule:transfer` or `rule:transfer:min=0`. They do NOT match `rule:transfer:min=1`.
- **Negative amounts:** Soroban i128 is signed; negative values are technically valid at the protocol level but semantically nonsensical for transfers. Watchers SHOULD ignore negative amounts or reject them explicitly (implementation choice). The contract does not validate amount sign.
- **Multiple transfer events in one transaction:** Each event is evaluated independently.
- **Transfer to self** (`from == to`): Valid and should trigger the rule.
- **Transfer from/to zero address:** Valid at the protocol level; trigger as normal.

**Example Matches:**

```
// Matches "rule:transfer"
{source: Contract, topics: ["transfer", Alice, Bob], data: i128(1000)}

// Matches "rule:transfer:min=500"
{source: Contract, topics: ["transfer", Alice, Bob], data: i128(1000)}

// Does NOT match "rule:transfer:min=1"
{source: Contract, topics: ["transfer", Alice, Bob], data: i128(0)}

// Matches "rule:transfer" (transfer to self)
{source: Contract, topics: ["transfer", Alice, Alice], data: i128(500)}
```

**Watcher Pseudocode:**

```python
def matches_transfer(event, rule):
    if rule.base != "transfer":
        return False
    if event.source != "Contract":
        return False
    if len(event.topics) != 3 or event.topics[0] != "transfer":
        return False
    if not isinstance(event.data, i128):
        return False
    amount = event.data
    if rule.has_min_param():
        return amount >= rule.min_value
    return True
```

**Test Vectors:**

| Event | Rule | Match? | Rationale |
|---|---|---|---|
| `transfer(Alice→Bob, 1000)` | `rule:transfer` | ✅ Yes | Standard transfer |
| `transfer(Alice→Bob, 1000)` | `rule:transfer:min=500` | ✅ Yes | Amount ≥ min |
| `transfer(Alice→Bob, 100)` | `rule:transfer:min=500` | ❌ No | Amount < min |
| `transfer(Alice→Bob, 0)` | `rule:transfer` | ✅ Yes | Zero-value valid |
| `transfer(Alice→Bob, 0)` | `rule:transfer:min=1` | ❌ No | 0 < 1 |
| `transfer(Alice→Alice, 500)` | `rule:transfer` | ✅ Yes | Self-transfer valid |

---

### 2. Mint Events

**Descriptor:** `rule:mint` or `rule:mint:min=<amount>`

**Stellar SEP-0041 Event Pattern:**

The contract emits a `mint` topic with `Contract` source, containing:
```
Topic: "mint"
Topic: admin_address (Address)
Data: amount (i128)
```

**Exact Match Condition:**

Trigger when any contract event matches ALL of:
1. Event source is `Contract`
2. Event topic name is exactly `"mint"` (case-sensitive)
3. Event has exactly 2 topics: `["mint", <admin>]`
4. Event data is a single i128 value (the amount)
5. If `min` parameter is present: `amount >= min`

**Edge Cases:**

- **Zero-value mints** (`amount == 0`): Valid and should match `rule:mint` or `rule:mint:min=0`. Do NOT match `rule:mint:min=1`.
- **Negative mints:** Technically possible in the event stream but semantically invalid for minting. Watchers SHOULD reject or handle explicitly.
- **Admin field:** The admin address is included as context but does not affect matching (only the amount and min parameter matter).

**Example Matches:**

```
// Matches "rule:mint"
{source: Contract, topics: ["mint", Admin1], data: i128(5000)}

// Matches "rule:mint:min=1000"
{source: Contract, topics: ["mint", Admin1], data: i128(5000)}

// Does NOT match "rule:mint:min=1"
{source: Contract, topics: ["mint", Admin1], data: i128(0)}
```

**Watcher Pseudocode:**

```python
def matches_mint(event, rule):
    if rule.base != "mint":
        return False
    if event.source != "Contract":
        return False
    if len(event.topics) != 2 or event.topics[0] != "mint":
        return False
    if not isinstance(event.data, i128):
        return False
    amount = event.data
    if rule.has_min_param():
        return amount >= rule.min_value
    return True
```

**Test Vectors:**

| Event | Rule | Match? | Rationale |
|---|---|---|---|
| `mint(Admin, 5000)` | `rule:mint` | ✅ Yes | Standard mint |
| `mint(Admin, 5000)` | `rule:mint:min=3000` | ✅ Yes | Amount ≥ min |
| `mint(Admin, 500)` | `rule:mint:min=3000` | ❌ No | Amount < min |
| `mint(Admin, 0)` | `rule:mint` | ✅ Yes | Zero-value valid |
| `mint(Admin, 0)` | `rule:mint:min=1` | ❌ No | 0 < 1 |

---

### 3. Burn Events

**Descriptor:** `rule:burn`

**Stellar SEP-0041 Event Pattern:**

The contract emits a `burn` topic with `Contract` source, containing:
```
Topic: "burn"
Topic: holder_address (Address)
Data: amount (i128)
```

**Exact Match Condition:**

Trigger when any contract event matches ALL of:
1. Event source is `Contract`
2. Event topic name is exactly `"burn"` (case-sensitive)
3. Event has exactly 2 topics: `["burn", <holder>]`
4. Event data is a single i128 value (the amount)

**Note:** Unlike `transfer` and `mint`, `burn` does NOT support the `:min=<amount>` parameter. Any burn event of any positive amount is treated equally.

**Edge Cases:**

- **Zero-value burns** (`amount == 0`): Technically valid at the protocol level but semantically nonsensical. Watchers SHOULD reject or log but the descriptor matches regardless.
- **Negative burns:** Signed i128 allows negative values; treat as invalid (implementation choice).
- **Burning non-existent balance:** Not a validation concern here; the event itself indicates a burn was logged by the contract.

**Example Matches:**

```
// Matches "rule:burn"
{source: Contract, topics: ["burn", Holder1], data: i128(1000)}

// Also matches "rule:burn" (zero-value, though semantically odd)
{source: Contract, topics: ["burn", Holder1], data: i128(0)}
```

**Watcher Pseudocode:**

```python
def matches_burn(event, rule):
    if rule.base != "burn":
        return False
    if event.source != "Contract":
        return False
    if len(event.topics) != 2 or event.topics[0] != "burn":
        return False
    if not isinstance(event.data, i128):
        return False
    return True
```

**Test Vectors:**

| Event | Rule | Match? | Rationale |
|---|---|---|---|
| `burn(Holder, 1000)` | `rule:burn` | ✅ Yes | Standard burn |
| `burn(Holder, 1)` | `rule:burn` | ✅ Yes | Any amount matches |
| `burn(Holder, 0)` | `rule:burn` | ✅ Yes | Zero-value matches (semantic oddity) |

---

### 4. Approve Events

**Descriptor:** `rule:approve` or `rule:approve:min=<amount>`

**Stellar SEP-0041 Event Pattern:**

The contract emits an `approve` topic with `Contract` source, containing:
```
Topic: "approve"
Topic: owner_address (Address)
Topic: spender_address (Address)
Data: allowance (i128)
```

**Exact Match Condition:**

Trigger when any contract event matches ALL of:
1. Event source is `Contract`
2. Event topic name is exactly `"approve"` (case-sensitive)
3. Event has exactly 3 topics: `["approve", <owner>, <spender>]`
4. Event data is a single i128 value (the allowance)
5. If `min` parameter is present: `allowance >= min`

**Edge Cases:**

- **Approve to self** (`owner == spender`): Valid and should trigger.
- **Zero allowance** (`allowance == 0`): Valid; matches `rule:approve` or `rule:approve:min=0`. Does NOT match `rule:approve:min=1`.
- **Revocation** (setting allowance to 0): Semantically a revocation, but matches rules normally. Watchers may apply domain logic to distinguish approvals from revocations.
- **Multiple approves for same pair**: Each event is independent; all matching events trigger the rule.

**Example Matches:**

```
// Matches "rule:approve"
{source: Contract, topics: ["approve", Owner1, Spender1], data: i128(5000)}

// Matches "rule:approve:min=1000"
{source: Contract, topics: ["approve", Owner1, Spender1], data: i128(5000)}

// Does NOT match "rule:approve:min=1" (revocation)
{source: Contract, topics: ["approve", Owner1, Spender1], data: i128(0)}

// Matches "rule:approve" (approve to self)
{source: Contract, topics: ["approve", Owner1, Owner1], data: i128(1000)}
```

**Watcher Pseudocode:**

```python
def matches_approve(event, rule):
    if rule.base != "approve":
        return False
    if event.source != "Contract":
        return False
    if len(event.topics) != 3 or event.topics[0] != "approve":
        return False
    if not isinstance(event.data, i128):
        return False
    allowance = event.data
    if rule.has_min_param():
        return allowance >= rule.min_value
    return True
```

**Test Vectors:**

| Event | Rule | Match? | Rationale |
|---|---|---|---|
| `approve(Owner, Spender, 5000)` | `rule:approve` | ✅ Yes | Standard approval |
| `approve(Owner, Spender, 5000)` | `rule:approve:min=2000` | ✅ Yes | Allowance ≥ min |
| `approve(Owner, Spender, 500)` | `rule:approve:min=2000` | ❌ No | Allowance < min |
| `approve(Owner, Spender, 0)` | `rule:approve` | ✅ Yes | Revocation (zero) valid |
| `approve(Owner, Spender, 0)` | `rule:approve:min=1` | ❌ No | 0 < 1 |
| `approve(Owner, Owner, 1000)` | `rule:approve` | ✅ Yes | Self-approval valid |

---

### 5. Clawback Events

**Descriptor:** `rule:clawback`

**Stellar SEP-0041 Event Pattern:**

The contract emits a `clawback` topic with `Contract` source, containing:
```
Topic: "clawback"
Topic: admin_address (Address)
Topic: holder_address (Address)
Data: amount (i128)
```

**Exact Match Condition:**

Trigger when any contract event matches ALL of:
1. Event source is `Contract`
2. Event topic name is exactly `"clawback"` (case-sensitive)
3. Event has exactly 3 topics: `["clawback", <admin>, <holder>]`
4. Event data is a single i128 value (the amount)

**Note:** Like `burn`, `clawback` does NOT support the `:min=<amount>` parameter.

**Edge Cases:**

- **Zero-amount clawback** (`amount == 0`): Valid; matches normally.
- **Clawback from self** (`admin == holder`): Technically valid but semantically odd; triggers as normal.
- **Clawback of non-existent balance:** Not a validation concern; the event indicates the contract logged the action.

**Example Matches:**

```
// Matches "rule:clawback"
{source: Contract, topics: ["clawback", Admin, Holder], data: i128(2000)}

// Also matches (zero-amount, though semantically odd)
{source: Contract, topics: ["clawback", Admin, Holder], data: i128(0)}
```

**Watcher Pseudocode:**

```python
def matches_clawback(event, rule):
    if rule.base != "clawback":
        return False
    if event.source != "Contract":
        return False
    if len(event.topics) != 3 or event.topics[0] != "clawback":
        return False
    if not isinstance(event.data, i128):
        return False
    return True
```

**Test Vectors:**

| Event | Rule | Match? | Rationale |
|---|---|---|---|
| `clawback(Admin, Holder, 2000)` | `rule:clawback` | ✅ Yes | Standard clawback |
| `clawback(Admin, Holder, 1)` | `rule:clawback` | ✅ Yes | Any amount matches |
| `clawback(Admin, Holder, 0)` | `rule:clawback` | ✅ Yes | Zero-value matches |

---

## Rule Composition

Multiple rules may be attached to a single alert. The alert triggers if **any** rule matches (logical OR). Examples:

**Example 1: Transfer OR Mint**
```json
{
  "alert_id": 42,
  "target_contract": "C...",
  "rules": ["rule:transfer", "rule:mint"]
}
```
Fires webhook when either a transfer OR mint event occurs on the target contract.

**Example 2: Large Transfers AND Approvals**
```json
{
  "alert_id": 43,
  "target_contract": "C...",
  "rules": ["rule:transfer:min=100000", "rule:approve:min=50000"]
}
```
Fires webhook when a transfer of ≥100,000 units OR an approval for ≥50,000 units occurs. Individual events are evaluated independently; the alert does not wait for both rules to fire in the same transaction.

**Example 3: All Five Rules (Risk Monitoring)**
```json
{
  "alert_id": 44,
  "target_contract": "C...",
  "rules": ["rule:transfer", "rule:mint", "rule:burn", "rule:approve", "rule:clawback"]
}
```
Fires on any financial event affecting the target contract.

---

## Parameter Format

### `:min=<amount>` Parameter

The optional `:min=<amount>` parameter specifies a minimum token amount threshold. It applies only to descriptors that support it:

- ✅ `rule:transfer:min=<amount>`
- ✅ `rule:mint:min=<amount>`
- ❌ `rule:burn` (not supported; rejected if present)
- ✅ `rule:approve:min=<amount>`
- ❌ `rule:clawback` (not supported; rejected if present)

**Amount Format:**

- **Type:** Canonical non-negative decimal `i128`
- **Syntax:** Digits only; no sign, no leading zeros except `0` itself; must not exceed `i128::MAX` (9,223,372,036,854,775,807)
- **Examples:**
  - ✅ `rule:transfer:min=0`
  - ✅ `rule:transfer:min=1`
  - ✅ `rule:transfer:min=9223372036854775807` (i128::MAX)
  - ❌ `rule:transfer:min=+1` (sign not allowed)
  - ❌ `rule:transfer:min=01` (leading zero not allowed)
  - ❌ `rule:transfer:min=-1` (negative not allowed)
  - ❌ `rule:transfer:min=9223372036854775808` (exceeds i128::MAX)

**Validation:** AlertRegistry's `validate_rule` rejects any malformed parameter and returns `ContractError::InvalidRuleDescriptor`.

---

## Future Extensions (v0.3.0+)

This section documents planned extensibility for future rule types.

### Proposed Rules (Not Yet Implemented)

**1. Payment-Stream Rules** (`rule:payment_in`, `rule:payment_out`)
- Monitor continuous payment channels or streaming transactions
- Status: Under discussion; requires SEP-0041 extension or custom event schema

**2. Access Control Rules** (`rule:grant`, `rule:revoke`)
- Monitor permission changes (e.g., role grants/revocations in DAOs or multi-sig contracts)
- Status: Depends on SEP-0041 standardization

**3. Custom User-Defined Rules** (`rule:custom:schema_id`)
- Allow contract owners to register custom event patterns
- Status: Requires versioned rule schema registry; planned for v1.0.0

### Extensibility Guarantee

The AlertRegistry enforces a maximum of 10 rules per alert to provide headroom for these future types. Current validator logic ensures:

1. **Only 5 recognized descriptors are accepted** (transfer, mint, burn, approve, clawback)
2. **No duplicate descriptors** are allowed in a single alert
3. **Unrecognized descriptors are rejected** with `ContractError::InvalidRuleDescriptor`

When new rule types are added in a future release:

1. A new contract version will be published with updated `VALID_RULE_DESCRIPTORS`
2. Existing alerts continue to function unchanged (backward compatible)
3. New alerts may use new rule types immediately upon contract upgrade
4. The on-chain version field (`contractmeta!`) identifies which rule types are supported

---

## Validation Rules

The AlertRegistry enforces the following validation on all rule lists:

| Check | Behavior |
|---|---|
| **Descriptor Count** | Max 10 per alert (from `MAX_RULES_PER_ALERT`); exceeding this returns `ContractError::TooManyRules` |
| **Descriptor Format** | Must match `rule:<base>` or `rule:<base>:min=<amount>` exactly; anything else returns `ContractError::InvalidRuleDescriptor` |
| **Base Recognition** | Base must be one of the 5 recognized types; unrecognized bases return `ContractError::InvalidRuleDescriptor` |
| **Parameter Validation** | If `:min=<amount>` present, `<amount>` must be a canonical non-negative i128; invalid format returns `ContractError::InvalidRuleDescriptor` |
| **Duplicate Detection** | The same descriptor (including parameters) cannot appear twice; duplicates return `ContractError::DuplicateRule` |
| **Base-Level Duplication** | Two descriptors with the same base but different `:min` parameters are allowed (e.g., `rule:transfer:min=100` and `rule:transfer:min=1000` may coexist in one alert) |

---

## Watcher Implementation Checklist

To ensure correct off-chain rule evaluation:

- [ ] Exact string matching for event topic names (`"transfer"`, `"mint"`, etc.) — no case folding
- [ ] Validate event source is `Contract` (not Stellar native operations)
- [ ] Validate topic count matches the rule type (e.g., transfer has 3 topics)
- [ ] Validate data field is a single i128 value
- [ ] Support optional `:min` parameter for transfer, mint, approve only
- [ ] Parse `:min` value as non-negative i128; reject malformed amounts
- [ ] Apply numeric comparison (`>=`) for min thresholds
- [ ] Treat zero-value transfers/mints/approves/burns/clawbacks as valid
- [ ] Handle edge cases (self-transfers, self-approvals, negative amounts) explicitly
- [ ] Log or reject unexpected event structures (malformed topics, missing data, etc.)
- [ ] Test against the provided test vectors for each rule type

---

## References

- [Stellar SEP-0041: Event Emissions](https://stellar.org/protocol/sep-0041)
- [Soroban SDK Event Documentation](https://developers.stellar.org/docs/learn/soroban/events)
- [OverStand AlertRegistry API Reference](alert-registry.md)
- [OverStand Rule Parameters](alert-registry.md#parameterized-rules)
