package overstand

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewRule_Valid(t *testing.T) {
	tests := []string{
		"rule:transfer",
		"rule:mint",
		"rule:burn",
		"rule:approve",
		"rule:clawback",
		"rule:transfer:min=1000000",
		"rule:mint:min=500000",
		"rule:approve:min=100",
	}

	for _, descriptor := range tests {
		t.Run(descriptor, func(t *testing.T) {
			rule, err := NewRule(descriptor)
			require.NoError(t, err)
			assert.Equal(t, descriptor, rule.Descriptor)
		})
	}
}

func TestNewRule_Invalid(t *testing.T) {
	tests := []string{
		"invalid:transfer",
		"transfer",
		"rule:invalid",
		"rule:",
		"",
	}

	for _, descriptor := range tests {
		t.Run(descriptor, func(t *testing.T) {
			rule, err := NewRule(descriptor)
			assert.Error(t, err)
			assert.Nil(t, rule)
		})
	}
}

func TestWebhookHashFromURL(t *testing.T) {
	url := "https://example.com/webhook"
	hash := WebhookHashFromURL(url)

	// Should return a 32-byte array
	assert.Equal(t, 32, len(hash))

	// Same URL should produce same hash
	hash2 := WebhookHashFromURL(url)
	assert.Equal(t, hash, hash2)

	// Different URLs should produce different hashes
	hash3 := WebhookHashFromURL("https://different.com/webhook")
	assert.NotEqual(t, hash, hash3)
}

func TestAlertInputValidation(t *testing.T) {
	// Valid input
	input := AlertInput{
		Label:         "Test Alert",
		WebhookHash:   WebhookHashFromURL("https://example.com/hook"),
		Rules:         []string{"rule:transfer", "rule:mint"},
		TargetContract: "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
	}

	assert.NotEmpty(t, input.Label)
	assert.NotEmpty(t, input.Rules)
	assert.Equal(t, 32, len(input.WebhookHash))
}
