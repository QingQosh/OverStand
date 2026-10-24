# Webhook Security Best Practices

This guide provides best practices for securing webhook endpoints that receive alerts from OverStand. It covers both the contract's role (HMAC signing) and the integrator's role (validation, rate limiting, audit logging).

## Table of Contents

1. [Overview](#overview)
2. [Webhook Sender Security](#webhook-sender-security)
3. [Webhook Receiver Security](#webhook-receiver-security)
4. [Implementation Examples](#implementation-examples)
5. [Security Checklist](#security-checklist)

---

## Overview

A webhook endpoint receives HTTP POST requests from OverStand watcher nodes when alerts fire. This endpoint is part of your integration's security perimeter and must be protected accordingly.

### Attack Vectors

| Vector | Risk | Mitigation |
|---|---|---|
| **Spoofed webhooks** | Attacker sends fake alert from wrong source | HMAC signature validation |
| **Injection attacks** | Attacker crafts payload with malicious data | Input validation |
| **Rate limiting bypass** | Attacker floods endpoint to exhaust resources | Rate limiting |
| **Credential exposure** | Auth tokens leaked in logs or monitoring | Secure storage, secret rotation |
| **Man-in-the-middle** | Attacker intercepts webhook in transit | TLS 1.3+ enforcement |
| **Replay attacks** | Attacker re-sends old webhook to trigger action | Nonce/timestamp validation |

### Security Layers

```
┌─────────────────────────────────────────────┐
│  OverStand AlertRegistry Contract           │
│  (Trusted source of truth)                  │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │ HMAC Signing        │
        │ (v0.4.0 feature)    │
        └──────────┬──────────┘
                   │
                   ▼ HTTP POST
        ┌──────────────────────┐
        │  TLS 1.3+ Encrypted  │
        │  Channel             │
        └──────────┬───────────┘
                   │
                   ▼
        ┌─────────────────────────────────────┐
        │ Your Webhook Receiver               │
        │ ┌───────────────────────────────┐   │
        │ │ 1. Validate HMAC signature    │   │
        │ │ 2. Verify source IP (optional)│   │
        │ │ 3. Rate limiting              │   │
        │ │ 4. Input validation           │   │
        │ │ 5. Audit logging              │   │
        │ │ 6. Action execution           │   │
        │ └───────────────────────────────┘   │
        └─────────────────────────────────────┘
```

---

## Webhook Sender Security

### OverStand Contract (Sender)

The OverStand AlertRegistry contract is responsible for securely sending webhooks:

#### Current (v0.3.0)

Currently, the contract sends unsigned webhooks:

```
POST /webhook-url HTTP/1.1
Host: example.com
Content-Type: application/json

{
  "config_id": 123,
  "label": "My Alert",
  "target_contract": "CAAAA...",
  "triggered_rules": ["rule:transfer:min=1000000"],
  "event": {
    "type": "contract_invoked",
    "contract": "CBBBB...",
    "operation": "transfer",
    "details": {...}
  }
}
```

**Validation responsibility**: 100% on receiver (you).

#### Enhanced (v0.4.0 Planned)

v0.4.0 will add optional HMAC-SHA256 signing:

```
POST /webhook-url HTTP/1.1
Host: example.com
Content-Type: application/json
X-OverStand-Signature: sha256=...
X-OverStand-Timestamp: 1698000000

{
  "config_id": 123,
  "label": "My Alert",
  ...
}
```

**New headers**:
- `X-OverStand-Signature`: HMAC-SHA256 of the payload (format: `sha256=<hex>`)
- `X-OverStand-Timestamp`: Unix timestamp when webhook was sent

**How to enable** (v0.4.0):

```rust
// Contract interface (planned)
pub fn register_alert(
    env: Env,
    owner: Address,
    label: String,
    webhook_hash: BytesN<32>,
    webhook_secret: Option<BytesN<32>>,  // NEW: Optional shared secret
    rules: Vec<String>,
    target_contract: Address,
) -> Result<u64, ContractError>
```

If `webhook_secret` is provided, the contract will:
1. Generate HMAC-SHA256 of the payload using the secret
2. Include signature in `X-OverStand-Signature` header
3. Include timestamp for replay protection

---

## Webhook Receiver Security

### Best Practices for Your Endpoint

Your webhook receiver must implement multiple layers of validation:

#### 1. Validate HMAC Signature (v0.4.0+)

When webhook signing is enabled, validate the signature before processing:

```python
# Python example
import hmac
import hashlib
import json
from flask import request, abort

SECRET = bytes.fromhex(os.environ["OVERSTAND_WEBHOOK_SECRET"])

@app.route("/webhook", methods=["POST"])
def webhook():
    # Extract signature and body
    signature = request.headers.get("X-OverStand-Signature")
    timestamp = request.headers.get("X-OverStand-Timestamp")
    
    if not signature or not timestamp:
        return abort(400, "Missing signature or timestamp")
    
    # Reconstruct HMAC
    body = request.get_data()
    expected_hmac = hmac.new(
        SECRET,
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Compare (using constant-time comparison to prevent timing attacks)
    if not hmac.compare_digest(
        f"sha256={expected_hmac}",
        signature
    ):
        return abort(401, "Invalid signature")
    
    # Validate timestamp (within 5 minutes)
    import time
    current_time = int(time.time())
    if abs(current_time - int(timestamp)) > 300:
        return abort(401, "Timestamp too old (replay attack)")
    
    # Process webhook...
    return {"status": "ok"}, 200
```

#### 2. Validate Source IP (Optional but Recommended)

Whitelist watcher node IP addresses:

```python
@app.route("/webhook", methods=["POST"])
def webhook():
    ALLOWED_IPS = [
        "203.0.113.1",    # Watcher node 1
        "203.0.113.2",    # Watcher node 2
        "203.0.113.3",    # Watcher node 3
    ]
    
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        return abort(403, f"IP {client_ip} not whitelisted")
    
    # Process webhook...
```

**Note**: If behind a proxy/load balancer, extract the real IP from `X-Forwarded-For`:

```python
def get_real_ip(request):
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr
```

#### 3. Implement Rate Limiting

Prevent a single source from overwhelming your endpoint:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/webhook", methods=["POST"])
@limiter.limit("10 per minute")  # Per-source rate limit
def webhook():
    # Process webhook...
```

Or use middleware/reverse proxy (nginx, Cloudflare):

```nginx
# nginx rate limiting
limit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=10r/m;

server {
    location /webhook {
        limit_req zone=webhook_limit burst=5 nodelay;
        proxy_pass http://backend;
    }
}
```

#### 4. Input Validation

Validate all webhook payload fields:

```python
from pydantic import BaseModel, validator

class AlertPayload(BaseModel):
    config_id: int
    label: str
    target_contract: str
    triggered_rules: List[str]
    event: dict

    @validator("config_id")
    def config_id_positive(cls, v):
        if v <= 0:
            raise ValueError("config_id must be positive")
        return v

    @validator("label")
    def label_length(cls, v):
        if len(v) > 128:
            raise ValueError("label too long (max 128 bytes)")
        return v

    @validator("triggered_rules")
    def validate_rules(cls, v):
        if len(v) > 10:
            raise ValueError("too many rules")
        for rule in v:
            if not rule.startswith("rule:"):
                raise ValueError(f"invalid rule: {rule}")
        return v

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        payload = AlertPayload(**request.json)
    except ValidationError as e:
        return {"error": str(e)}, 400
    
    # Process valid payload...
```

#### 5. Audit Logging

Log all webhook events for debugging and security audits:

```python
import logging
from datetime import datetime

logger = logging.getLogger("webhook")

@app.route("/webhook", methods=["POST"])
def webhook():
    # Log received webhook
    logger.info(f"Webhook received",
        extra={
            "source_ip": get_real_ip(request),
            "config_id": payload.config_id,
            "timestamp": datetime.utcnow().isoformat(),
            "signature_valid": signature_valid,
        }
    )
    
    try:
        # Process webhook...
        result = process_alert(payload)
        
        logger.info(f"Webhook processed",
            extra={
                "config_id": payload.config_id,
                "result": result,
            }
        )
        return {"status": "ok"}, 200
    
    except Exception as e:
        logger.error(f"Webhook processing failed",
            extra={
                "config_id": payload.config_id,
                "error": str(e),
            },
            exc_info=True
        )
        return {"error": "processing failed"}, 500
```

Structured logs should include:
- Timestamp (ISO 8601)
- Source IP
- Config ID
- Signature validation result
- Processing status (success/failure)
- Error messages (if failed)
- User/account context

#### 6. Use TLS 1.3+

Always use HTTPS with modern TLS:

```python
# Flask with HTTPS
# Option 1: Production server (gunicorn + SSL)
gunicorn --certfile=/path/to/cert.pem \
         --keyfile=/path/to/key.pem \
         --bind 0.0.0.0:443 \
         app:app

# Option 2: Reverse proxy (nginx)
server {
    listen 443 ssl http2;
    ssl_protocols TLSv1.3;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /webhook {
        proxy_pass http://localhost:5000;
    }
}
```

**Check TLS configuration**:

```bash
# Verify TLS 1.3 is enabled
openssl s_client -connect example.com:443 -tls1_3

# Use Mozilla's SSL configuration generator
# https://ssl-config.mozilla.org/
```

#### 7. Rotate Auth Tokens Regularly

If using authentication tokens (e.g., API keys, OAuth):

```python
@app.route("/webhook", methods=["POST"])
def webhook():
    # Extract and validate auth token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return abort(401, "Missing bearer token")
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Validate token (check expiry, signature, revocation list)
    if not validate_token(token):
        return abort(401, "Invalid or expired token")
    
    # Process webhook...
```

**Token rotation policy**:
- Change webhook secret/token every 90 days
- Rotate immediately if exposed
- Maintain a short grace period (1 week) where both old and new tokens are accepted
- Alert on failed webhook attempts after rotation

---

## Implementation Examples

### Python: Flask + HMAC Validation

```python
# webhook_receiver.py

import os
import hmac
import hashlib
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic import BaseModel, validator

app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address)
logger = logging.getLogger(__name__)

# Configuration
WEBHOOK_SECRET = bytes.fromhex(os.environ["OVERSTAND_WEBHOOK_SECRET"])
ALLOWED_IPS = os.environ.get("ALLOWED_IPS", "").split(",")
REQUEST_TIMEOUT = 300  # 5 minutes

class WebhookPayload(BaseModel):
    config_id: int
    label: str
    target_contract: str
    triggered_rules: list
    event: dict
    
    @validator("config_id")
    def config_id_positive(cls, v):
        if v <= 0:
            raise ValueError("config_id must be positive")
        return v

def get_real_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr

def validate_signature(body, signature, timestamp):
    """Validate HMAC-SHA256 signature and timestamp."""
    # Check timestamp (prevent replay attacks)
    try:
        current_time = int(datetime.utcnow().timestamp())
        webhook_time = int(timestamp)
        if abs(current_time - webhook_time) > REQUEST_TIMEOUT:
            logger.warning(f"Webhook timestamp too old: {webhook_time}")
            return False, "Timestamp expired"
    except ValueError:
        logger.warning(f"Invalid timestamp format: {timestamp}")
        return False, "Invalid timestamp"
    
    # Validate signature
    if not signature or not signature.startswith("sha256="):
        return False, "Missing or invalid signature format"
    
    expected_sig = hmac.new(
        WEBHOOK_SECRET,
        body,
        hashlib.sha256
    ).hexdigest()
    
    provided_sig = signature[7:]  # Remove "sha256=" prefix
    
    if not hmac.compare_digest(expected_sig, provided_sig):
        logger.warning(f"Signature mismatch. Expected: {expected_sig}, Got: {provided_sig}")
        return False, "Invalid signature"
    
    return True, None

@app.route("/webhook", methods=["POST"])
@limiter.limit("10 per minute")
def webhook():
    """Handle incoming OverStand webhook."""
    source_ip = get_real_ip()
    
    # 1. Validate source IP (if configured)
    if ALLOWED_IPS and ALLOWED_IPS[0]:  # Skip if empty list
        if source_ip not in ALLOWED_IPS:
            logger.warning(f"Webhook from unauthorized IP: {source_ip}")
            return jsonify({"error": "Unauthorized IP"}), 403
    
    # 2. Extract and validate signature
    signature = request.headers.get("X-OverStand-Signature")
    timestamp = request.headers.get("X-OverStand-Timestamp")
    body = request.get_data()
    
    if not signature or not timestamp:
        logger.warning("Webhook missing signature or timestamp")
        return jsonify({"error": "Missing signature or timestamp"}), 400
    
    valid, error_msg = validate_signature(body, signature, timestamp)
    if not valid:
        logger.warning(f"Signature validation failed: {error_msg}")
        return jsonify({"error": error_msg}), 401
    
    # 3. Parse and validate payload
    try:
        data = json.loads(body)
        payload = WebhookPayload(**data)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON: {e}")
        return jsonify({"error": "Invalid JSON"}), 400
    except Exception as e:
        logger.warning(f"Payload validation failed: {e}")
        return jsonify({"error": f"Invalid payload: {str(e)}"}), 400
    
    # 4. Log webhook receipt
    logger.info("Webhook validated",
        extra={
            "config_id": payload.config_id,
            "source_ip": source_ip,
            "label": payload.label,
        }
    )
    
    # 5. Process webhook (your business logic)
    try:
        result = process_alert(payload)
        
        logger.info("Webhook processed",
            extra={
                "config_id": payload.config_id,
                "result": result,
            }
        )
        return jsonify({"status": "ok", "result": result}), 200
    
    except Exception as e:
        logger.error(f"Webhook processing failed",
            extra={
                "config_id": payload.config_id,
                "error": str(e),
            },
            exc_info=True
        )
        return jsonify({"error": "Processing failed"}), 500

def process_alert(payload: WebhookPayload):
    """Your custom alert processing logic."""
    # Example: Send Slack notification, update database, trigger action, etc.
    print(f"Processing alert #{payload.config_id}: {payload.label}")
    print(f"Rules triggered: {payload.triggered_rules}")
    print(f"Event: {payload.event}")
    
    # TODO: Implement your business logic
    return {"notified_users": 2}

if __name__ == "__main__":
    # Configuration for development only
    # Use gunicorn + TLS for production
    app.run(host="0.0.0.0", port=5000, debug=False)
```

**Run with:**

```bash
# Development (HTTP only, for testing)
export OVERSTAND_WEBHOOK_SECRET="abc123..."
python webhook_receiver.py

# Production (with gunicorn + HTTPS)
export OVERSTAND_WEBHOOK_SECRET="abc123..."
gunicorn --certfile=/path/to/cert.pem \
         --keyfile=/path/to/key.pem \
         --bind 0.0.0.0:443 \
         --workers 4 \
         webhook_receiver:app
```

### Go: Chi + HMAC Validation

```go
// webhook_receiver.go

package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/middleware"
	"github.com/go-chi/httprate"
)

type AlertPayload struct {
	ConfigID       int      `json:"config_id"`
	Label          string   `json:"label"`
	TargetContract string   `json:"target_contract"`
	TriggeredRules []string `json:"triggered_rules"`
	Event          map[string]interface{} `json:"event"`
}

type WebhookServer struct {
	secret     []byte
	allowedIPs map[string]bool
}

func NewWebhookServer(secretHex string, allowedIPs []string) (*WebhookServer, error) {
	secret, err := hex.DecodeString(secretHex)
	if err != nil {
		return nil, fmt.Errorf("invalid secret hex: %w", err)
	}

	ips := make(map[string]bool)
	for _, ip := range allowedIPs {
		ips[ip] = true
	}

	return &WebhookServer{
		secret:     secret,
		allowedIPs: ips,
	}, nil
}

func (ws *WebhookServer) validateSignature(body []byte, signature, timestamp string) error {
	// Validate timestamp
	if signature == "" || timestamp == "" {
		return fmt.Errorf("missing signature or timestamp")
	}

	webhookTime, err := strconv.ParseInt(timestamp, 10, 64)
	if err != nil {
		return fmt.Errorf("invalid timestamp: %w", err)
	}

	currentTime := time.Now().Unix()
	if abs(currentTime-webhookTime) > 300 { // 5 minutes
		return fmt.Errorf("timestamp expired")
	}

	// Validate HMAC
	if !strings.HasPrefix(signature, "sha256=") {
		return fmt.Errorf("invalid signature format")
	}

	providedSig := signature[7:] // Remove "sha256=" prefix
	expectedSig := hex.EncodeToString(
		hmac.New(sha256.New, ws.secret).Sum(body),
	)

	if !hmac.Equal([]byte(expectedSig), []byte(providedSig)) {
		return fmt.Errorf("signature mismatch")
	}

	return nil
}

func (ws *WebhookServer) handleWebhook(w http.ResponseWriter, r *http.Request) {
	// Get real IP
	clientIP := r.Header.Get("X-Forwarded-For")
	if clientIP == "" {
		clientIP = strings.Split(r.RemoteAddr, ":")[0]
	}

	// Validate source IP
	if len(ws.allowedIPs) > 0 && !ws.allowedIPs[clientIP] {
		log.Printf("Unauthorized IP: %s", clientIP)
		http.Error(w, "Unauthorized", http.StatusForbidden)
		return
	}

	// Read body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read body", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	// Validate signature
	signature := r.Header.Get("X-OverStand-Signature")
	timestamp := r.Header.Get("X-OverStand-Timestamp")

	if err := ws.validateSignature(body, signature, timestamp); err != nil {
		log.Printf("Signature validation failed: %v", err)
		http.Error(w, fmt.Sprintf("Validation failed: %v", err), http.StatusUnauthorized)
		return
	}

	// Parse payload
	var payload AlertPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		log.Printf("Failed to parse payload: %v", err)
		http.Error(w, "Invalid payload", http.StatusBadRequest)
		return
	}

	// Validate payload
	if payload.ConfigID <= 0 {
		http.Error(w, "Invalid config_id", http.StatusBadRequest)
		return
	}

	if len(payload.Label) > 128 {
		http.Error(w, "Label too long", http.StatusBadRequest)
		return
	}

	// Log webhook
	log.Printf("Webhook validated: config_id=%d, label=%s, source=%s",
		payload.ConfigID, payload.Label, clientIP)

	// Process webhook
	if err := processAlert(&payload); err != nil {
		log.Printf("Failed to process alert: %v", err)
		http.Error(w, "Processing failed", http.StatusInternalServerError)
		return
	}

	// Success response
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func processAlert(payload *AlertPayload) error {
	// Your custom business logic
	log.Printf("Processing alert #%d: %s\n", payload.ConfigID, payload.Label)
	log.Printf("Rules triggered: %v\n", payload.TriggeredRules)
	// TODO: Send notifications, update database, etc.
	return nil
}

func abs(x int64) int64 {
	if x < 0 {
		return -x
	}
	return x
}

func main() {
	// Configuration
	secretHex := os.Getenv("OVERSTAND_WEBHOOK_SECRET")
	allowedIPsStr := os.Getenv("ALLOWED_IPS")
	var allowedIPs []string
	if allowedIPsStr != "" {
		allowedIPs = strings.Split(allowedIPsStr, ",")
	}

	// Create server
	ws, err := NewWebhookServer(secretHex, allowedIPs)
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	// Setup router
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(httprate.LimitByIP(10, time.Minute)) // 10 requests per minute per IP

	r.Post("/webhook", ws.handleWebhook)

	// Start server
	log.Println("Starting webhook server on :8080")
	log.Fatal(http.ListenAndServe(":8080", r))
}
```

**Run with:**

```bash
export OVERSTAND_WEBHOOK_SECRET="abc123..."
export ALLOWED_IPS="203.0.113.1,203.0.113.2"
go run webhook_receiver.go
```

### Docker Compose: Local Testing

```yaml
# docker-compose.yml - Test setup

version: '3.8'

services:
  webhook-receiver:
    build: .
    ports:
      - "5000:5000"
    environment:
      OVERSTAND_WEBHOOK_SECRET: "${WEBHOOK_SECRET:-abc123def456}"
      ALLOWED_IPS: "127.0.0.1,172.17.0.1"
    volumes:
      - ./webhook_receiver.py:/app/webhook_receiver.py
    networks:
      - webhook-net

  test-client:
    build:
      context: .
      dockerfile: Dockerfile.test
    depends_on:
      - webhook-receiver
    environment:
      WEBHOOK_URL: "http://webhook-receiver:5000/webhook"
      WEBHOOK_SECRET: "${WEBHOOK_SECRET:-abc123def456}"
    volumes:
      - ./test_webhook.py:/app/test_webhook.py
    networks:
      - webhook-net

networks:
  webhook-net:
    driver: bridge
```

**Test script** (`test_webhook.py`):

```python
#!/usr/bin/env python3

import os
import hmac
import hashlib
import json
import requests
import time

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "http://localhost:5000/webhook")
SECRET = bytes.fromhex(os.environ.get("WEBHOOK_SECRET", "abc123def456"))

def test_valid_webhook():
    """Test a valid webhook with correct signature."""
    payload = {
        "config_id": 1,
        "label": "Test Alert",
        "target_contract": "CAAAA...",
        "triggered_rules": ["rule:transfer"],
        "event": {"type": "test"},
    }
    
    body = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    
    signature = f"sha256={hmac.new(SECRET, body, hashlib.sha256).hexdigest()}"
    
    headers = {
        "X-OverStand-Signature": signature,
        "X-OverStand-Timestamp": timestamp,
    }
    
    resp = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    print(f"✅ Valid webhook: {resp.status_code} {resp.text}")
    assert resp.status_code == 200

def test_invalid_signature():
    """Test a webhook with invalid signature."""
    payload = {"config_id": 1, "label": "Bad"}
    timestamp = str(int(time.time()))
    signature = "sha256=invalidsignature"
    
    headers = {
        "X-OverStand-Signature": signature,
        "X-OverStand-Timestamp": timestamp,
    }
    
    resp = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    print(f"❌ Invalid signature: {resp.status_code} (expected 401)")
    assert resp.status_code == 401

def test_expired_timestamp():
    """Test a webhook with expired timestamp."""
    payload = {"config_id": 1}
    old_timestamp = str(int(time.time()) - 400)  # 6+ minutes old
    
    body = json.dumps(payload).encode()
    signature = f"sha256={hmac.new(SECRET, body, hashlib.sha256).hexdigest()}"
    
    headers = {
        "X-OverStand-Signature": signature,
        "X-OverStand-Timestamp": old_timestamp,
    }
    
    resp = requests.post(WEBHOOK_URL, json=payload, headers=headers)
    print(f"⏰ Expired timestamp: {resp.status_code} (expected 401)")
    assert resp.status_code == 401

if __name__ == "__main__":
    print(f"Testing webhook receiver at {WEBHOOK_URL}")
    print()
    
    test_valid_webhook()
    test_invalid_signature()
    test_expired_timestamp()
    
    print()
    print("✅ All tests passed!")
```

**Run tests**:

```bash
docker-compose up -d
docker-compose exec test-client python test_webhook.py
docker-compose down
```

---

## Security Checklist

Before deploying your webhook receiver to production:

- [ ] **HMAC Validation**: Validate X-OverStand-Signature header with your secret key
- [ ] **Timestamp Validation**: Check X-OverStand-Timestamp is within 5 minutes of current time
- [ ] **Source IP Whitelisting**: Restrict webhooks to known watcher node IPs
- [ ] **Rate Limiting**: Limit requests per source IP (e.g., 10/min)
- [ ] **Input Validation**: Validate config_id, label, rules, and event payload
- [ ] **TLS 1.3+**: Use HTTPS only, no HTTP fallback
- [ ] **Audit Logging**: Log all webhooks (received, validated, processed)
- [ ] **Error Handling**: Gracefully handle malformed payloads, don't leak stack traces
- [ ] **Secrets Management**: Store webhook secret in environment variables or secrets vault
- [ ] **Secret Rotation**: Plan for rotating secrets every 90 days
- [ ] **Monitoring**: Alert on high failure rates, invalid signatures, replay attempts
- [ ] **Testing**: Unit test signature validation, timestamp checks, rate limiting
- [ ] **Documentation**: Document webhook security requirements for integrators
- [ ] **Incident Response**: Have a plan if webhook secret is compromised

---

## Appendix: OpenAPI Specification

```yaml
openapi: 3.0.0
info:
  title: OverStand Webhook Receiver
  version: 1.0.0
  description: Secure webhook endpoint for OverStand alerts

paths:
  /webhook:
    post:
      summary: Receive alert webhook
      operationId: receiveWebhook
      tags:
        - Webhooks
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                config_id:
                  type: integer
                  description: Alert configuration ID
                label:
                  type: string
                  maxLength: 128
                target_contract:
                  type: string
                  description: Contract address being monitored
                triggered_rules:
                  type: array
                  items:
                    type: string
                  description: Rules that triggered this alert
                event:
                  type: object
                  description: Event details
      parameters:
        - name: X-OverStand-Signature
          in: header
          required: true
          schema:
            type: string
            pattern: "^sha256=[a-f0-9]{64}$"
          description: HMAC-SHA256 signature of the request body
        - name: X-OverStand-Timestamp
          in: header
          required: true
          schema:
            type: string
            pattern: "^[0-9]{10}$"
          description: Unix timestamp when the webhook was sent
      responses:
        '200':
          description: Webhook processed successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum: [ok]
        '400':
          description: Invalid request (missing headers, malformed JSON)
        '401':
          description: Unauthorized (invalid signature or timestamp)
        '403':
          description: Forbidden (IP not whitelisted)
        '500':
          description: Server error (processing failed)
```

---

**Last Updated**: October 24, 2026  
**Version**: 1.0  
**Status**: Active
