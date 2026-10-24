"""
Example: Register an Alert

This example demonstrates how to register a new alert in AlertRegistry.

Prerequisites:
- A funded Stellar account (testnet or mainnet)
- The AlertRegistry contract ID
- A target contract to monitor
- A webhook hash (SHA-256 of your webhook URL)
"""

import asyncio
from stellar_sdk import Account, Network, Keypair, SorobanServer, TransactionBuilder
from overstand_py import AlertRegistry


async def main() -> None:
    """Register an alert on testnet."""
    
    # Configuration
    NETWORK = Network.testnet_network()
    RPC_SERVER = "https://soroban-testnet.stellar.org"
    ALERT_REGISTRY_ID = "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    
    # Your account
    SECRET_KEY = "SBBB..."  # Replace with your secret key
    keypair = Keypair.random()  # Or use Keypair.from_secret(SECRET_KEY)
    
    # Initialize Soroban server
    server = SorobanServer(RPC_SERVER)
    
    # Get account sequence
    source_account = await server.get_account(keypair.public_key)
    
    # Initialize registry client
    registry = AlertRegistry(
        contract_id=ALERT_REGISTRY_ID,
        server=server,
        network=NETWORK,
    )
    
    # Alert parameters
    label = "ETH Transfer Monitor"
    webhook_hash = "abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234"
    rules = ["rule:transfer:min=1000000000"]  # Transfers >= 1 billion units
    target_contract = "CBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    
    try:
        # Register the alert
        tx_hash = await registry.register_alert(
            owner=source_account,
            label=label,
            webhook_hash=webhook_hash,
            rules=rules,
            target_contract=target_contract,
        )
        print(f"✅ Alert registered successfully!")
        print(f"   Transaction: {tx_hash}")
        
    except Exception as e:
        print(f"❌ Error registering alert: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
