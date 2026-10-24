package main

import (
	"context"
	"fmt"
	"log"

	"github.com/QingQosh/OverStand/sdks/go/overstand"
	"github.com/stellar/go/keypair"
	"github.com/stellar/go/network"
)

// This example demonstrates how to register a new alert using the Go SDK.
//
// To run this example:
//   1. Set TESTNET_SECRET_KEY environment variable to a funded testnet keypair
//   2. Set ALERT_CONTRACT_ID to your deployed AlertRegistry contract
//   3. go run examples/register_alert.go
func main() {
	ctx := context.Background()

	// Initialize clients
	rpcURL := "https://soroban-testnet.stellar.org"
	contractID := "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" // Replace with actual contract ID
	networkPassphrase := network.TestNetworkPassphrase

	registry, err := overstand.NewAlertRegistry(rpcURL, contractID, networkPassphrase)
	if err != nil {
		log.Fatalf("Failed to create AlertRegistry client: %v", err)
	}

	// Create keypair from secret key
	// In production, load this securely from environment or vault
	kp, err := keypair.ParseFull("SBBB...") // Replace with actual secret key
	if err != nil {
		log.Fatalf("Failed to parse keypair: %v", err)
	}

	owner := kp.Address()

	// Define alert parameters
	label := "Monitor High-Value Transfers"
	targetContract := "CBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB" // Contract to monitor
	webhookURL := "https://api.example.com/webhook/alert"
	webhookHash := overstand.WebhookHashFromURL(webhookURL)

	// Define rules: monitor transfers >= 1 million units and all mint operations
	rules := []string{
		"rule:transfer:min=1000000",
		"rule:mint",
	}

	// Register the alert
	fmt.Println("Registering alert...")
	txHash, err := registry.RegisterAlert(
		ctx,
		owner,
		label,
		webhookHash,
		rules,
		targetContract,
		nil, // Would pass signing keypair in production
	)
	if err != nil {
		log.Fatalf("Failed to register alert: %v", err)
	}

	fmt.Printf("Alert registered successfully!\n")
	fmt.Printf("Transaction hash: %s\n", txHash)
	fmt.Printf("Owner: %s\n", owner)
	fmt.Printf("Label: %s\n", label)
	fmt.Printf("Target contract: %s\n", targetContract)
	fmt.Printf("Rules: %v\n", rules)
}
