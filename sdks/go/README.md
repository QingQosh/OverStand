# OverStand Go SDK

[![Go Reference](https://pkg.go.dev/badge/github.com/QingQosh/OverStand/sdks/go.svg)](https://pkg.go.dev/github.com/QingQosh/OverStand/sdks/go)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

A Go SDK for interacting with OverStand Soroban smart contracts on the Stellar network.

**OverStand** provides on-chain alert and watcher registry contracts to help you monitor blockchain events and receive real-time webhooks.

## Features

- **AlertRegistry**: Register alerts on specific contract addresses and receive webhooks when rules match
- **WatcherRegistry**: Manage authorized watcher node addresses
- **Type-safe**: Full type safety with idiomatic Go interfaces
- **CLI Tool**: Built-in command-line tool for common operations
- **Well-documented**: Comprehensive godoc and examples

## Installation

### As a Library

```bash
go get github.com/QingQosh/OverStand/sdks/go
```

### CLI Tool

```bash
go install github.com/QingQosh/OverStand/sdks/go/cmd/overstand-cli@latest
```

Or build from source:

```bash
cd sdks/go
go build -o overstand-cli ./cmd/overstand-cli
```

## Quick Start

### Register an Alert (Go)

```go
package main

import (
	"context"
	"log"

	"github.com/QingQosh/OverStand/sdks/go/overstand"
	"github.com/stellar/go/network"
)

func main() {
	ctx := context.Background()

	// Create registry client
	registry, err := overstand.NewAlertRegistry(
		"https://soroban-testnet.stellar.org",
		"CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
		network.TestNetworkPassphrase,
	)
	if err != nil {
		log.Fatal(err)
	}

	// Register an alert
	webhookHash := overstand.WebhookHashFromURL("https://example.com/hook")
	txHash, err := registry.RegisterAlert(
		ctx,
		"GAAAA...", // owner
		"Monitor transfers",
		webhookHash,
		[]string{"rule:transfer:min=1000000", "rule:mint"},
		"CBBBB...", // target contract
		nil,        // signing keypair (would be used in production)
	)
	if err != nil {
		log.Fatal(err)
	}

	println("Alert registered:", txHash)
}
```

### Query Alerts (Go)

```go
// Get alerts for a specific contract
alerts, err := registry.GetContractAlertsPaginated(
	ctx,
	"GAAAA...", // querier
	"CBBBB...", // target contract
	0,          // offset
	10,         // limit
)
if err != nil {
	log.Fatal(err)
}

for _, alert := range alerts {
	println("Alert:", alert.ConfigID, alert.Label)
}

// Get alerts by owner
ownerAlerts, err := registry.GetAlertsByOwnerPaginated(
	ctx,
	"GAAAA...", // querier
	"GCCCC...", // owner
	0,          // offset
	10,         // limit
)
```

### Register an Alert (CLI)

```bash
overstand-cli register-alert \
  --contract CAAAA... \
  --label "Monitor transfers" \
  --webhook-url https://example.com/hook \
  --target CBBBB... \
  --rules "rule:transfer:min=1000000,rule:mint"
```

### Query Alerts (CLI)

```bash
# Get alerts by owner
overstand-cli query-alerts \
  --contract CAAAA... \
  --owner GAAAA... \
  --limit 20

# Get alerts for a contract
overstand-cli query-contract-alerts \
  --contract CAAAA... \
  --target CBBBB...

# Get a specific alert
overstand-cli get-alert \
  --contract CAAAA... \
  --config-id 1

# Get registry status
overstand-cli registry-status --contract CAAAA...
```

## CLI Help

```bash
overstand-cli help
```

## Rule Descriptors

Rules describe which events to monitor. The OverStand registry supports these rule types:

| Rule | Description | With Min Parameter? |
|---|---|---|
| `rule:transfer` | Monitor token transfers | ✅ Yes |
| `rule:mint` | Monitor token mints | ✅ Yes |
| `rule:burn` | Monitor token burns | ❌ No |
| `rule:approve` | Monitor token approvals | ✅ Yes |
| `rule:clawback` | Monitor token clawbacks | ❌ No |

### Using Min Parameters

Some rules support optional minimum amount thresholds:

```go
rules := []string{
	"rule:transfer",              // Any transfer
	"rule:transfer:min=1000000",  // Only transfers >= 1M units
	"rule:mint:min=500000",       // Only mints >= 500K units
	"rule:approve",               // Any approval
	"rule:burn",                  // Any burn
	"rule:clawback",              // Any clawback
}
```

See [docs/rules-specification.md](../../docs/rules-specification.md) for the complete rule semantics.

## API Reference

### AlertRegistry

#### Read Methods

- `GetAlert(ctx, querier, configID)` - Get a single alert by ID
- `GetContractAlertsPaginated(ctx, querier, targetContract, offset, limit)` - Get paginated alerts for a contract
- `GetAlertsByOwnerPaginated(ctx, querier, owner, offset, limit)` - Get paginated alerts by owner
- `GetAlertCount(ctx)` - Get total number of alerts ever registered
- `GetActiveAlertCount(ctx, owner)` - Get number of active alerts for an owner
- `GetAdmin(ctx)` - Get the current admin address
- `GetPerOwnerAlertLimit(ctx)` - Get the per-owner alert limit
- `GetPerContractAlertLimit(ctx)` - Get the per-contract alert limit
- `GetGlobalAlertLimit(ctx)` - Get the global alert limit
- `GetStatus(ctx)` - Get overall registry status

#### Write Methods

- `RegisterAlert(ctx, owner, label, webhookHash, rules, targetContract, signingKeypair)` - Register a new alert
- `UpdateAlert(ctx, configID, rules, active, signingKeypair)` - Update an alert's rules and status
- `UpdateWebhook(ctx, configID, newWebhookHash, signingKeypair)` - Update an alert's webhook hash
- `RemoveAlert(ctx, configID, signingKeypair)` - Remove an alert

### WatcherRegistry

#### Read Methods

- `IsWatcherAuthorized(ctx, watcherAddress)` - Check if a watcher is authorized
- `GetWatchers(ctx)` - Get all registered watchers
- `GetAdmin(ctx)` - Get the current admin address
- `GetWatcherCount(ctx)` - Get the total number of watchers

#### Write Methods

- `RegisterWatcher(ctx, watcherAddress, signingKeypair)` - Register a new watcher
- `RemoveWatcher(ctx, watcherAddress, signingKeypair)` - Remove a watcher
- `TransferAdmin(ctx, newAdmin, signingKeypair)` - Transfer admin role

## Examples

See the `examples/` directory:

- **[register_alert.go](examples/register_alert.go)** - Register a new alert
- **[query_alerts.go](examples/query_alerts.go)** - Query alerts

Run an example:

```bash
cd examples
go run register_alert.go
```

## Type Definitions

The SDK includes type-safe Go types:

```go
import "github.com/QingQosh/OverStand/sdks/go/overstand"

// AlertConfig
alert := overstand.AlertConfig{
	ConfigID:       1,
	Label:          "My Alert",
	WebhookHash:    [32]byte{},
	Rules:          []string{"rule:transfer"},
	Owner:          "GAAAA...",
	TargetContract: "CBBBB...",
	Active:         true,
}

// WatcherInfo
watcher := overstand.WatcherInfo{
	Address:    "GAAAA...",
	Authorized: true,
}

// RegistryStatus
status := overstand.RegistryStatus{
	Admin:            "GAAAA...",
	Paused:           false,
	ActiveAlertCount: 42,
}
```

## Testing

Run the test suite:

```bash
go test ./...
```

Run with coverage:

```bash
go test -cover ./...
```

## Limits

The OverStand contracts enforce these limits:

| Limit | Value | Notes |
|---|---|---|
| Max rules per alert | 10 | Provides headroom for future rule types |
| Max page size | 100 | For paginated queries |
| Max alert label | 128 bytes | UTF-8 encoded |
| Max watchers | 250 | Registry-wide maximum |
| Max alert owners | 10 | Default max, configurable by admin |

See [README.md](../../README.md#hard-limits) for the complete hard limits table.

## Documentation

- **[OverStand Repository](https://github.com/QingQosh/OverStand)** - Main project
- **[Go API Reference](https://pkg.go.dev/github.com/QingQosh/OverStand/sdks/go)** - Godoc
- **[Rule Descriptors Specification](../../docs/rules-specification.md)** - Unambiguous rule semantics
- **[Alert Registry API](../../docs/alert-registry.md)** - Complete contract reference
- **[Watcher Registry API](../../docs/watcher-registry.md)** - Complete contract reference
- **[Stellar Go SDK Documentation](https://github.com/stellar/go)** - Stellar Go SDK

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

Licensed under the Apache License 2.0. See [LICENSE](../../LICENSE) for details.

## Support

- 📖 [Read the docs](../../README.md)
- 💬 [GitHub Issues](https://github.com/QingQosh/OverStand/issues)
- 🌐 [Stellar Community](https://stellar.org/community)

