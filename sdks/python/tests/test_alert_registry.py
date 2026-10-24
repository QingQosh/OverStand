"""
Unit tests for AlertRegistry client.
"""

import pytest
from overstand_py import AlertRegistry
from overstand_py.types import AlertConfig


class TestAlertRegistry:
    """Test suite for AlertRegistry client."""

    def test_init(self) -> None:
        """Test AlertRegistry initialization."""
        registry = AlertRegistry(
            contract_id="CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            server=None,  # type: ignore
            network=None,  # type: ignore
        )
        assert registry.contract_id == "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    def test_alert_config_creation(self) -> None:
        """Test AlertConfig model creation."""
        alert = AlertConfig(
            config_id=1,
            label="Test Alert",
            webhook_hash="abcd1234",
            rules=["rule:transfer", "rule:mint"],
            owner="GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            target_contract="CBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            active=True,
        )
        assert alert.config_id == 1
        assert alert.label == "Test Alert"
        assert len(alert.rules) == 2

    def test_alert_config_serialization(self) -> None:
        """Test AlertConfig JSON serialization."""
        alert = AlertConfig(
            config_id=42,
            label="Serialization Test",
            webhook_hash="deadbeef",
            rules=["rule:transfer:min=1000"],
            owner="GAAAA",
            target_contract="CBBBB",
        )
        data = alert.model_dump()
        assert data["config_id"] == 42
        assert data["label"] == "Serialization Test"

    def test_label_length_validation_sync(self) -> None:
        """Test that label can be created if <= 128 bytes."""
        long_label = "A" * 128
        alert = AlertConfig(
            config_id=1,
            label=long_label,
            webhook_hash="abcd",
            owner="GAAAA",
            target_contract="CBBBB",
        )
        assert len(alert.label.encode('utf-8')) <= 128

    def test_rules_count_validation(self) -> None:
        """Test that rules count is validated."""
        too_many_rules = [f"rule:custom:{i}" for i in range(11)]
        # Pydantic will accept this, but the SDK should reject on register
        alert = AlertConfig(
            config_id=1,
            label="Test",
            webhook_hash="abcd",
            rules=too_many_rules,  # type: ignore
            owner="GAAAA",
            target_contract="CBBBB",
        )
        assert len(alert.rules) == 11


class TestAlertConfigEdgeCases:
    """Test edge cases for AlertConfig."""

    def test_zero_value_rules(self) -> None:
        """Test that zero-value rules are accepted."""
        alert = AlertConfig(
            config_id=1,
            label="Zero Test",
            webhook_hash="abcd",
            rules=["rule:transfer:min=0", "rule:mint:min=0"],
            owner="GAAAA",
            target_contract="CBBBB",
        )
        assert "rule:transfer:min=0" in alert.rules

    def test_large_rule_amount(self) -> None:
        """Test that large rule amounts are accepted."""
        max_i128 = "9223372036854775807"
        alert = AlertConfig(
            config_id=1,
            label="Large Amount",
            webhook_hash="abcd",
            rules=[f"rule:transfer:min={max_i128}"],
            owner="GAAAA",
            target_contract="CBBBB",
        )
        assert alert.rules[0] == f"rule:transfer:min={max_i128}"

    def test_no_expiry(self) -> None:
        """Test alert with no expiry."""
        alert = AlertConfig(
            config_id=1,
            label="No Expiry",
            webhook_hash="abcd",
            owner="GAAAA",
            target_contract="CBBBB",
            active_until_ledger=None,
        )
        assert alert.active_until_ledger is None

    def test_with_expiry(self) -> None:
        """Test alert with expiry."""
        alert = AlertConfig(
            config_id=1,
            label="With Expiry",
            webhook_hash="abcd",
            owner="GAAAA",
            target_contract="CBBBB",
            active_until_ledger=1_000_000,
        )
        assert alert.active_until_ledger == 1_000_000
