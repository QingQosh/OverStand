package main

import (
	"context"
	"fmt"
	"log"

	"github.com/QingQosh/OverStand/sdks/go/overstand"
	"github.com/stellar/go/keypair"
	"github.com/stellar/go/network"
)

// This example demonstrates how to query alerts using the Go SDK.
//
// To run this example:
//   1. Set ALERT_CONTRACT_ID to your deployed AlertRegistry contract
//   2. go run examples/query_alerts.go
func main() {
	ctx := context.Background()

	// Initialize client
	rpcURL := "https://soroban-testnet.stellar.org"
	contractID := "CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" // Replace with actual contract ID
	networkPassphrase := network.TestNetworkPassphrase

	registry, err := overstand.NewAlertRegistry(rpcURL, contractID, networkPassphrase)
	if err != nil {
		log.Fatalf("Failed to create AlertRegistry client: %v", err)
	}

	// Example 1: Get alerts for a specific contract
	fmt.Println("=== Querying alerts for a contract ===")
	targetContract := "CBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
	querier := "GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

	alerts, err := registry.GetContractAlertsPaginated(ctx, querier, targetContract, 0, 10)
	if err != nil {
		log.Printf("Error querying alerts: %v\n", err)
	} else {
		fmt.Printf("Found %d alerts for contract %s\n", len(alerts), targetContract)
		for _, alert := range alerts {
			fmt.Printf("  - Alert ID %d: %s (Active: %v, Rules: %v)\n",
				alert.ConfigID, alert.Label, alert.Active, alert.Rules)
		}
	}

	// Example 2: Get alerts by owner
	fmt.Println("\n=== Querying alerts by owner ===")
	owner := "GCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"

	ownerAlerts, err := registry.GetAlertsByOwnerPaginated(ctx, querier, owner, 0, 10)
	if err != nil {
		log.Printf("Error querying owner alerts: %v\n", err)
	} else {
		fmt.Printf("Found %d alerts owned by %s\n", len(ownerAlerts), owner)
		for _, alert := range ownerAlerts {
			fmt.Printf("  - Alert ID %d: %s on %s (Rules: %v)\n",
				alert.ConfigID, alert.Label, alert.TargetContract, alert.Rules)
		}
	}

	// Example 3: Get a single alert
	fmt.Println("\n=== Getting a specific alert ===")
	configID := uint64(1)

	alert, err := registry.GetAlert(ctx, querier, configID)
	if err != nil {
		log.Printf("Error retrieving alert: %v\n", err)
	} else if alert != nil {
		fmt.Printf("Alert %d: %s\n", alert.ConfigID, alert.Label)
		fmt.Printf("  Owner: %s\n", alert.Owner)
		fmt.Printf("  Target: %s\n", alert.TargetContract)
		fmt.Printf("  Active: %v\n", alert.Active)
		fmt.Printf("  Rules: %v\n", alert.Rules)
	}

	// Example 4: Get registry statistics
	fmt.Println("\n=== Registry Statistics ===")
	totalAlerts, err := registry.GetAlertCount(ctx)
	if err != nil {
		log.Printf("Error getting alert count: %v\n", err)
	} else {
		fmt.Printf("Total alerts registered: %d\n", totalAlerts)
	}

	status, err := registry.GetStatus(ctx)
	if err != nil {
		log.Printf("Error getting registry status: %v\n", err)
	} else {
		fmt.Printf("Registry admin: %s\n", status.Admin)
		fmt.Printf("Paused: %v\n", status.Paused)
		fmt.Printf("Per-owner limit: %d\n", status.PerOwnerLimit)
		fmt.Printf("Per-contract limit: %d\n", status.PerContractLimit)
		fmt.Printf("Global limit: %d\n", status.GlobalLimit)
	}
}
