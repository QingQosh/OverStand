"""
WatcherRegistry contract client.

The WatcherRegistry contract stores authorized watcher node addresses and
manages their registration/deregistration by admins.
"""

from typing import List, Optional
from stellar_sdk import Address, SorobanServer, Network, Account

from .types import WatcherInfo, RegistryStatus


class WatcherRegistry:
    """Client for interacting with the WatcherRegistry Soroban contract.
    
    Provides methods to register/deregister watchers and query their status.
    
    Example:
        >>> from stellar_sdk import SorobanServer, Network
        >>> from overstand_py import WatcherRegistry
        >>> 
        >>> server = SorobanServer("https://soroban-testnet.stellar.org")
        >>> network = Network.testnet_network()
        >>> 
        >>> registry = WatcherRegistry(
        ...     contract_id="CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
        ...     server=server,
        ...     network=network,
        ... )
        >>> 
        >>> # Register a watcher
        >>> tx = registry.register_watcher(
        ...     admin=admin_account,
        ...     watcher_address="GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        ... )
    """

    def __init__(
        self,
        contract_id: str,
        server: SorobanServer,
        network: Network,
    ) -> None:
        """Initialize the WatcherRegistry client.
        
        Args:
            contract_id: The contract ID (starting with 'C')
            server: Soroban RPC server instance
            network: Stellar network (testnet, mainnet, etc.)
        """
        self.contract_id = contract_id
        self.server = server
        self.network = network

    async def register_watcher(
        self,
        admin: Account,
        watcher_address: str,
    ) -> str:
        """Register a new watcher node.
        
        Args:
            admin: Admin account performing the registration
            watcher_address: Public key of the watcher node to register
        
        Returns:
            Transaction hash
        
        Raises:
            ValueError: If watcher_address is invalid
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        # Validate address format
        try:
            Address(watcher_address)
        except Exception:
            raise ValueError(f"Invalid watcher address: {watcher_address}")
        
        raise NotImplementedError("Requires generated contract bindings")

    async def remove_watcher(
        self,
        admin: Account,
        watcher_address: str,
    ) -> str:
        """Deregister a watcher node (admin only).
        
        Args:
            admin: Admin account performing the removal
            watcher_address: Public key of the watcher node to remove
        
        Returns:
            Transaction hash
        
        Raises:
            ValueError: If watcher_address is invalid
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        # Validate address format
        try:
            Address(watcher_address)
        except Exception:
            raise ValueError(f"Invalid watcher address: {watcher_address}")
        
        raise NotImplementedError("Requires generated contract bindings")

    async def get_watchers(self) -> List[str]:
        """Fetch all registered watcher addresses.
        
        Returns:
            List of watcher addresses
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")

    async def is_watcher_authorized(
        self,
        watcher_address: str,
    ) -> bool:
        """Check if a watcher is currently authorized.
        
        Args:
            watcher_address: Public key to check
        
        Returns:
            True if authorized, False otherwise
        
        Raises:
            ValueError: If watcher_address is invalid
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        # Validate address format
        try:
            Address(watcher_address)
        except Exception:
            raise ValueError(f"Invalid watcher address: {watcher_address}")
        
        raise NotImplementedError("Requires generated contract bindings")

    async def get_watcher_count(self) -> int:
        """Get the number of registered watchers.
        
        Returns:
            Count of authorized watchers
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")

    async def transfer_admin(
        self,
        current_admin: Account,
        new_admin: str,
    ) -> str:
        """Propose a new admin (current admin only).
        
        The new admin must accept the transfer via accept_admin_transfer.
        
        Args:
            current_admin: Current admin account
            new_admin: Address of the proposed new admin
        
        Returns:
            Transaction hash
        
        Raises:
            ValueError: If new_admin is invalid
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        # Validate address format
        try:
            Address(new_admin)
        except Exception:
            raise ValueError(f"Invalid admin address: {new_admin}")
        
        raise NotImplementedError("Requires generated contract bindings")

    async def accept_admin_transfer(
        self,
        proposed_admin: Account,
    ) -> str:
        """Accept a pending admin transfer (proposed admin only).
        
        Args:
            proposed_admin: The proposed admin account accepting the transfer
        
        Returns:
            Transaction hash
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")

    async def get_status(self) -> RegistryStatus:
        """Get the current registry status.
        
        Returns:
            RegistryStatus with admin, pause state, and watcher count
        
        Raises:
            stellar_sdk.exceptions.SorobanRPCErrorResponse: If contract call fails
        """
        raise NotImplementedError("Requires generated contract bindings")
