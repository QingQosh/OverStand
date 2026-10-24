"""
Example: Query Alerts

This example demonstrates how to query alerts from AlertRegistry.

Prerequisites:
- A funded Stellar account (testnet or mainnet) 
- The AlertRegistry contract ID
"""

import asyncio
from stellar_sdk import Account, Network, Keypair, SorobanServer
from overstand_py import AlertRegistry


async def main() -> None:
    """Query alerts on testnet."""
    
    # Configuration
    NETWORK = Network.testnet_network()
    RPC_SERVER = "https://soroban-testnet.stellar.org"
    ALERT_REGISTRY_ID = "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    
    # Your account (for querier)
    SECRET_KEY = "SBBB..."  # Replace with your secret key
    keypair = Keypair.random()  # Or use Keypair.from_secret(SECRET_KEY)
    
    # Initialize Soroban server
    server = SorobanServer(RPC_SERVER)
    
    # Get account for querier
    querier_account = await server.get_account(keypair.public_key)
    
    # Initialize registry client
    registry = AlertRegistry(
        contract_id=ALERT_REGISTRY_ID,
        server=server,
        network=NETWORK,
    )
    
    try:
        # Example 1: Get alerts for a target contract
        print("📋 Fetching alerts for contract...")
        target_contract = "CBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
        alerts = await registry.get_contract_alerts_paginated(
            querier=querier_account,
            target_contract=target_contract,
            offset=0,
            limit=10,
        )
        print(f"✅ Found {len(alerts)} alerts:")
        for alert in alerts:
            print(f"   - ID {alert.config_id}: {alert.label} ({len(alert.rules)} rules)")
        
        # Example 2: Get alerts owned by a specific address
        print("\n👤 Fetching alerts owned by address...")
        owner_address = "GCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
        owner_alerts = await registry.get_alerts_by_owner_paginated(
            querier=querier_account,
            owner=owner_address,
            offset=0,
            limit=10,
        )
        print(f"✅ Found {len(owner_alerts)} alerts owned by {owner_address[:16]}...")
        for alert in owner_alerts:
            print(f"   - ID {alert.config_id}: {alert.label}")
        
        # Example 3: Get a specific alert
        print("\n🔍 Fetching specific alert...")
        config_id = 1
        alert = await registry.get_alert(
            querier=querier_account,
            config_id=config_id,
        )
        print(f"✅ Alert #{config_id}:")
        print(f"   Label: {alert.label}")
        print(f"   Target: {alert.target_contract[:16]}...")
        print(f"   Rules: {', '.join(alert.rules)}")
        print(f"   Owner: {alert.owner[:16]}...")
        print(f"   Active: {alert.active}")
        
        # Example 4: Get registry status
        print("\n📊 Fetching registry status...")
        status = await registry.get_status()
        print(f"✅ Registry status:")
        print(f"   Admin: {status.admin[:16]}...")
        print(f"   Paused: {status.paused}")
        print(f"   Active alerts: {status.active_alert_count}")
        
    except Exception as e:
        print(f"❌ Error querying alerts: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
