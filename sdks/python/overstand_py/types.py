"""
Type definitions for OverStand contracts.
"""

from typing import List, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field


class Rule(BaseModel):
    """A rule descriptor string.
    
    Attributes:
        descriptor: Rule descriptor (e.g., "rule:transfer", "rule:mint:min=1000")
    """
    descriptor: str

    def __str__(self) -> str:
        return self.descriptor


class AlertConfig(BaseModel):
    """Alert configuration stored in AlertRegistry.
    
    Attributes:
        config_id: Unique alert identifier
        label: Human-readable label (max 128 bytes)
        webhook_hash: SHA-256 hash of webhook URL (32 bytes)
        rules: List of rule descriptors
        owner: Address of the alert owner
        target_contract: Contract address being watched
        active: Whether the alert is currently active
        active_until_ledger: Optional expiry ledger (None = no expiry)
    """
    config_id: int = Field(..., description="Unique alert identifier")
    label: str = Field(..., description="Human-readable label (max 128 bytes)")
    webhook_hash: str = Field(..., description="SHA-256 hash of webhook URL (hex string)")
    rules: List[str] = Field(default_factory=list, description="Rule descriptors")
    owner: str = Field(..., description="Address of the alert owner")
    target_contract: str = Field(..., description="Contract address being watched")
    active: bool = Field(default=True, description="Whether the alert is active")
    active_until_ledger: Optional[int] = Field(None, description="Optional expiry ledger")


class WatcherInfo(BaseModel):
    """Information about a registered watcher.
    
    Attributes:
        address: Watcher node address
        authorized: Whether the watcher is currently authorized
    """
    address: str = Field(..., description="Watcher node address")
    authorized: bool = Field(default=True, description="Authorization status")


class RegistryStatus(BaseModel):
    """Status and limits of a registry.
    
    Attributes:
        admin: Current admin address
        paused: Whether the registry is paused
        active_alert_count: Current number of active alerts (AlertRegistry only)
        watcher_count: Current number of registered watchers (WatcherRegistry only)
    """
    admin: str = Field(..., description="Current admin address")
    paused: bool = Field(default=False, description="Pause status")
    active_alert_count: Optional[int] = Field(None, description="Active alert count")
    watcher_count: Optional[int] = Field(None, description="Registered watcher count")
