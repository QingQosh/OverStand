"""
OverStand Python SDK

A Python SDK for interacting with OverStand Soroban smart contracts:
- AlertRegistry: Stores alert configurations on-chain
- WatcherRegistry: Manages authorized watcher node addresses

Example usage:

    from overstand_py import AlertRegistry, WatcherRegistry
    from stellar_sdk import Network, SorobanServer

    # Initialize
    server = SorobanServer("https://soroban-testnet.stellar.org")
    network = Network.testnet_network()

    alert_registry = AlertRegistry(
        contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        server=server,
        network=network,
    )

    # Register an alert
    result = alert_registry.register_alert(
        owner=owner_account,
        label="Transfer Monitor",
        webhook_hash=webhook_hash,
        rules=["rule:transfer", "rule:mint"],
        target_contract="CBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    )

See examples/ for more detailed usage patterns.
"""

from .alert_registry import AlertRegistry
from .watcher_registry import WatcherRegistry
from .types import AlertConfig, Rule

__version__ = "0.3.0"
__author__ = "QingQosh"

__all__ = [
    "AlertRegistry",
    "WatcherRegistry",
    "AlertConfig",
    "Rule",
]
