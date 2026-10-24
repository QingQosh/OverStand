"""
AlertRegistry contract client.

The AlertRegistry contract stores alert configurations on-chain, keyed by
target contract address. Owners register alerts to monitor specific contract
events and receive webhook notifications when rules match.
"""

from typing import List, Optional
from stellar_sdk import Address, SorobanServer, Network, Account
from stellar_sdk.client.soroban_client import SorobanClient

from .types import AlertConfig, RegistryStatus


class AlertRegistry:
    """Client for interacting with the AlertRegistry Soroban contract.
    
    Provides methods to register, update, query, and manage alert configurations.
    
    Example:
        >>> from stellar_sdk import SorobanServer, Network
        >>> from overstand_py import AlertRegistry
        >>> 
        >>> server = SorobanServer("https://soroban-testnet.stellar.org")
        >>> network = Network.testnet_network()
        >>> 
        >>> registry = AlertRegistry(
        ...     contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        ...     server=server,
        ...     network=network,
        ... )
        >>> 
        >>> # Register an alert
        >>> tx = registry.register_alert(
        ...     owner=owner_account,
        ...     label="Transfer Monitor",
        ...     webhook_hash="abcd1234...",
        ...     rules=["rule:transfer:min=1000"],
        ...     target_contract="CBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ... )
    """

    def __init__(
        self,
        contract_id: str,
        server: SorobanServer,
        network: Network,
    ) -> None:
        """Initialize the AlertRegistry client.
        
        Args:
            contract_id: The contract ID (starting with 'C')
            server: Soroban RPC server instance
            network: Stellar network (testnet, mainnet, etc.)
        """
        self.contract_id = contract_id
        self.server = server
        self.network = network

    async def register_alert(
        self,
        owner: Account,
        label: str,
        webhook_hash: str,
        rules: List[str],
        target_contract: str,
        active_until_ledger: Optional[int] = None,
        account_id: Optional[str] = None,
    ) -> str:
        """Register a new alert.
        
        Args:
            owner: Alert owner account
            label: Human-readable label (max 128 bytes)
            webhook_hash: SHA-256 hash of webhook URL (hex string, 64 chars)
            rules: List of rule descriptors (e.g., ["rule:transfer", "rule:mint:min=1000"])
            target_contract: Contract address to monitor
            active_until_ledger: Optional ledger at which alert expires (None = no expiry)
            account_id: Optional custom account ID (defaults to owner public key)
        
        Returns:
            Transaction hash
        
        Raises:
            ValueError: If label exceeds 128 bytes or rules exceed 10 items
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        if len(label.encode('utf-8')) > 128:
            raise ValueError("Label exceeds 128 bytes")
        if len(rules) > 10:
            raise ValueError("Maximum 10 rules per alert")
        
        # Build transaction (stub for demo)
        # In a real implementation, this would build a proper Soroban
        # transaction using the Stellar SDK contract bindings
        raise NotImplementedError("Requires generated contract bindings")

    async def get_alert(
        self,
        querier: Account,
        config_id: int,
    ) -> AlertConfig:
        """Fetch an alert by ID.
        
        Args:
            querier: Address querying the alert (must sign the transaction)
            config_id: Alert ID to fetch
        
        Returns:
            AlertConfig
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")

    async def get_alerts_for_contract(
        self,
        querier: Account,
        target_contract: str,
    ) -> List[AlertConfig]:
        """Fetch all alerts for a target contract.
        
        Args:
            querier: Address querying alerts
            target_contract: Contract to get alerts for
        
        Returns:
            List of AlertConfig
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")

    async def get_alerts_by_owner(
        self,
        querier: Account,
        owner: str,
    ) -> List[AlertConfig]:
        """Fetch all alerts owned by an address.
        
        Args:
            querier: Address querying alerts
            owner: Owner address to fetch alerts for
        
        Returns:
            List of AlertConfig
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")

    async def get_contract_alerts_paginated(
        self,
        querier: Account,
        target_contract: str,
        offset: int = 0,
        limit: int = 50,
    ) -> List[AlertConfig]:
        """Fetch alerts for a contract with pagination.
        
        Args:
            querier: Address querying alerts
            target_contract: Contract to get alerts for
            offset: Page offset (default: 0)
            limit: Page size, max 100 (default: 50)
        
        Returns:
            List of AlertConfig (up to `limit` entries)
        
        Raises:
            ValueError: If limit exceeds 100
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        if limit > 100:
            raise ValueError("Limit cannot exceed 100")
        
        raise NotImplementedError("Requires generated contract bindings")

    async def get_alerts_by_owner_paginated(
        self,
        querier: Account,
        owner: str,
        offset: int = 0,
        limit: int = 50,
    ) -> List[AlertConfig]:
        """Fetch alerts owned by an address with pagination.
        
        Args:
            querier: Address querying alerts
            owner: Owner address
            offset: Page offset (default: 0)
            limit: Page size, max 100 (default: 50)
        
        Returns:
            List of AlertConfig (up to `limit` entries)
        
        Raises:
            ValueError: If limit exceeds 100
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        if limit > 100:
            raise ValueError("Limit cannot exceed 100")
        
        raise NotImplementedError("Requires generated contract bindings")

    async def update_alert(
        self,
        owner: Account,
        config_id: int,
        label: Optional[str] = None,
        webhook_hash: Optional[str] = None,
        rules: Optional[List[str]] = None,
        target_contract: Optional[str] = None,
    ) -> str:
        """Update an existing alert (owner only).
        
        Args:
            owner: Alert owner account
            config_id: Alert ID to update
            label: New label (optional)
            webhook_hash: New webhook hash (optional)
            rules: New rules (optional)
            target_contract: New target contract (optional)
        
        Returns:
            Transaction hash
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")

    async def deactivate_alert(
        self,
        owner: Account,
        config_id: int,
    ) -> str:
        """Deactivate an alert (owner only).
        
        Args:
            owner: Alert owner account
            config_id: Alert ID to deactivate
        
        Returns:
            Transaction hash
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")

    async def remove_alert(
        self,
        owner: Account,
        config_id: int,
    ) -> str:
        """Remove an alert (owner only).
        
        Args:
            owner: Alert owner account
            config_id: Alert ID to remove
        
        Returns:
            Transaction hash
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")

    async def get_status(self) -> RegistryStatus:
        """Get the current registry status.
        
        Returns:
            RegistryStatus with admin, pause state, and alert count
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")
