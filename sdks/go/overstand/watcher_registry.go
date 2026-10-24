package overstand

import (
	"context"
	"fmt"

	"github.com/stellar/go/clients/sorobanrpc"
	"github.com/stellar/go/txnbuild"
)

// WatcherRegistry is a client for interacting with the WatcherRegistry Soroban contract.
type WatcherRegistry struct {
	client     *sorobanrpc.Client
	contractID string
	network    string
}

// NewWatcherRegistry creates a new WatcherRegistry client.
//
// Parameters:
//   - rpcURL: URL of the Soroban RPC server (e.g., "https://soroban-testnet.stellar.org")
//   - contractID: The contract ID of the deployed WatcherRegistry
//   - network: Network passphrase (e.g., "Test SDF Network ; September 2015" for testnet)
func NewWatcherRegistry(rpcURL, contractID, network string) (*WatcherRegistry, error) {
	client, err := sorobanrpc.NewClient(rpcURL)
	if err != nil {
		return nil, fmt.Errorf("failed to create Soroban RPC client: %w", err)
	}

	return &WatcherRegistry{
		client:     client,
		contractID: contractID,
		network:    network,
	}, nil
}

// RegisterWatcher registers a new watcher node in the registry.
//
// Only the contract admin can register watchers.
func (wr *WatcherRegistry) RegisterWatcher(
	ctx context.Context,
	watcherAddress string,
	signingKeypair *txnbuild.Account,
) (string, error) {
	return "", fmt.Errorf("RegisterWatcher: not yet implemented")
}

// RemoveWatcher removes a watcher from the registry.
//
// Only the contract admin can remove watchers.
func (wr *WatcherRegistry) RemoveWatcher(
	ctx context.Context,
	watcherAddress string,
	signingKeypair *txnbuild.Account,
) (string, error) {
	return "", fmt.Errorf("RemoveWatcher: not yet implemented")
}

// IsWatcherAuthorized checks if a watcher is registered and authorized.
func (wr *WatcherRegistry) IsWatcherAuthorized(ctx context.Context, watcherAddress string) (bool, error) {
	return false, fmt.Errorf("IsWatcherAuthorized: not yet implemented")
}

// GetWatchers retrieves all registered watchers.
func (wr *WatcherRegistry) GetWatchers(ctx context.Context) ([]WatcherInfo, error) {
	return nil, fmt.Errorf("GetWatchers: not yet implemented")
}

// GetAdmin retrieves the current admin address.
func (wr *WatcherRegistry) GetAdmin(ctx context.Context) (string, error) {
	return "", fmt.Errorf("GetAdmin: not yet implemented")
}

// GetWatcherCount retrieves the total number of registered watchers.
func (wr *WatcherRegistry) GetWatcherCount(ctx context.Context) (uint32, error) {
	return 0, fmt.Errorf("GetWatcherCount: not yet implemented")
}

// TransferAdmin transfers admin role to a new address.
//
// Only the current admin can transfer their role.
func (wr *WatcherRegistry) TransferAdmin(
	ctx context.Context,
	newAdmin string,
	signingKeypair *txnbuild.Account,
) (string, error) {
	return "", fmt.Errorf("TransferAdmin: not yet implemented")
}
