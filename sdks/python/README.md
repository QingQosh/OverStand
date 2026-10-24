# OverStand Python SDK

[![PyPI](https://img.shields.io/pypi/v/overstand)](https://pypi.org/project/overstand/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

A Python SDK for interacting with OverStand Soroban smart contracts on the Stellar network.

**OverStand** provides on-chain alert and watcher registry contracts to help you monitor blockchain events and receive real-time webhooks.

## Features

- **AlertRegistry**: Register alerts on specific contract addresses and receive webhooks when rules match
- **WatcherRegistry**: Manage authorized watcher node addresses
- **Type-safe**: Full type hints and Pydantic models
- **Async**: Built for modern Python async/await
- **Well-documented**: Comprehensive docstrings and examples

## Installation

Install from PyPI:

```bash
pip install overstand
```

Or install locally for development:

```bash
git clone https://github.com/QingQosh/OverStand.git
cd OverStand/sdks/python
pip install -e ".[dev]"
```

## Quick Start

### Register an Alert

```python
import asyncio
from stellar_sdk import Network, SorobanServer, Keypair
from overstand_py import AlertRegistry

async def main():
    # Initialize
    server = SorobanServer("https://soroban-testnet.stellar.org")
    network = Network.testnet_network()
    keypair = Keypair.from_secret("SBBB...")
    
    # Get account
    account = await server.get_account(keypair.public_key)
    
    # Create registry client
    registry = AlertRegistry(
        contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        server=server,
        network=network,
    )
    
    # Register an alert
    tx = await registry.register_alert(
        owner=account,
        label="Transfer Monitor",
        webhook_hash="abcd1234...",  # SHA-256 of webhook URL
        rules=["rule:transfer:min=1000000"],
        target_contract="CBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    )
    print(f"Alert registered: {tx}")

asyncio.run(main())
```

### Query Alerts

```python
# Get all alerts for a contract
alerts = await registry.get_contract_alerts_paginated(
    querier=account,
    target_contract="CBBBB...",
    offset=0,
    limit=10,
)

for alert in alerts:
    print(f"Alert {alert.config_id}: {alert.label}")
    print(f"  Rules: {', '.join(alert.rules)}")
    print(f"  Active: {alert.active}")
```

### Manage Watchers

```python
from overstand_py import WatcherRegistry

# Create watcher registry client
watcher_registry = WatcherRegistry(
    contract_id="CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
    server=server,
    network=network,
)

# Register a watcher
tx = await watcher_registry.register_watcher(
    admin=admin_account,
    watcher_address="GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
)

# Get all watchers
watchers = await watcher_registry.get_watchers()
print(f"Registered watchers: {len(watchers)}")

# Check if a watcher is authorized
authorized = await watcher_registry.is_watcher_authorized("GAAAA...")
print(f"Authorized: {authorized}")
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

```python
rules = [
    "rule:transfer",              # Any transfer
    "rule:transfer:min=1000000",  # Only transfers >= 1M units
    "rule:mint:min=500000",       # Only mints >= 500K units
    "rule:approve",               # Any approval
    "rule:burn",                  # Any burn
    "rule:clawback",              # Any clawback
]
```

See [docs/rules-specification.md](../../docs/rules-specification.md) for the complete rule semantics.

## Type Definitions

The SDK includes Pydantic models for type safety:

```python
from overstand_py import AlertConfig, WatcherInfo, RegistryStatus

# AlertConfig
alert = AlertConfig(
    config_id=1,
    label="My Alert",
    webhook_hash="abcd1234...",
    rules=["rule:transfer"],
    owner="GAAAA...",
    target_contract="CBBBB...",
    active=True,
)

# WatcherInfo
watcher = WatcherInfo(
    address="GAAAA...",
    authorized=True,
)

# RegistryStatus
status = RegistryStatus(
    admin="GAAAA...",
    paused=False,
    active_alert_count=42,
)
```

## Examples

See the `examples/` directory:

- **[register_alert.py](examples/register_alert.py)** - Register a new alert
- **[query_alerts.py](examples/query_alerts.py)** - Query alerts from the registry

Run an example:

```bash
python examples/register_alert.py
```

## Testing

Run the test suite:

```bash
pytest tests/
pytest tests/ --cov=overstand_py  # With coverage
```

Type checking:

```bash
mypy overstand_py/
```

Code formatting:

```bash
black overstand_py/
isort overstand_py/
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
- **[Rule Descriptors Specification](../../docs/rules-specification.md)** - Unambiguous rule semantics
- **[Alert Registry API](../../docs/alert-registry.md)** - Complete contract reference
- **[Watcher Registry API](../../docs/watcher-registry.md)** - Complete contract reference
- **[Stellar SDK Documentation](https://developers.stellar.org/docs/build/apps/sdks/python)** - Stellar Python SDK

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

Licensed under the Apache License 2.0. See [LICENSE](../../LICENSE) for details.

## Support

- 📖 [Read the docs](../../README.md)
- 💬 [GitHub Issues](https://github.com/QingQosh/OverStand/issues)
- 🌐 [Stellar Community](https://stellar.org/community)
