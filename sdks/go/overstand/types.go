package overstand

import (
	"crypto/sha256"
	"fmt"
)

// AlertConfig represents the configuration of an alert stored on-chain.
type AlertConfig struct {
	ConfigID      uint64
	Label         string
	WebhookHash   [32]byte
	Rules         []string
	Owner         string
	TargetContract string
	Active        bool
}

// AlertInput is used to register a new alert.
type AlertInput struct {
	Label         string
	WebhookHash   [32]byte
	Rules         []string
	TargetContract string
}

// Rule validates and represents a rule descriptor.
type Rule struct {
	Descriptor string
}

// NewRule creates a validated rule descriptor.
func NewRule(descriptor string) (*Rule, error) {
	validDescriptors := map[string]bool{
		"rule:transfer": true,
		"rule:mint":     true,
		"rule:burn":     true,
		"rule:approve":  true,
		"rule:clawback": true,
	}

	// Check if descriptor matches a known pattern (including parameterized rules)
	if len(descriptor) < 5 || descriptor[:5] != "rule:" {
		return nil, fmt.Errorf("invalid rule format: %s", descriptor)
	}

	// Extract base descriptor (before any colon parameters)
	baseDescriptor := descriptor
	for i := 5; i < len(descriptor); i++ {
		if descriptor[i] == ':' {
			baseDescriptor = descriptor[:i]
			break
		}
	}

	if !validDescriptors[baseDescriptor] {
		return nil, fmt.Errorf("unrecognized rule descriptor: %s", baseDescriptor)
	}

	return &Rule{Descriptor: descriptor}, nil
}

// WebhookHashFromURL computes the SHA-256 hash of a webhook URL.
func WebhookHashFromURL(url string) [32]byte {
	return sha256.Sum256([]byte(url))
}

// WatcherInfo represents a registered watcher in the registry.
type WatcherInfo struct {
	Address    string
	Authorized bool
}

// RegistryStatus represents the current state of the registry.
type RegistryStatus struct {
	Admin              string
	Paused             bool
	ActiveAlertCount   uint32
	PerOwnerLimit      uint32
	PerContractLimit   uint32
	GlobalLimit        uint64
	AlertCount         uint64
}

// Constants for registry limits.
const (
	MaxRulesPerAlert = 10
	MaxPageSize      = 100
	MaxLabelLength   = 128
	DefaultMaxOwnerAlerts = 10
	DefaultMaxContractAlerts = 10
)
