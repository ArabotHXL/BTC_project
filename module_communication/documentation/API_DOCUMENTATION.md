# HashInsight Module Communication API Documentation

## Overview

HashInsight is a Bitcoin mining analytics platform consisting of three independent modules that can communicate via REST APIs:

1. **Mining Core Module** (Port 5001) - Mining calculations, data analysis, technical indicators
2. **Web3 Integration Module** (Port 5002) - Wallet authentication, blockchain interactions, NFTs, crypto payments
3. **User Management Module** (Port 5003) - User authentication, CRM, subscription management, admin functions

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Mining Core    │    │ Web3 Integration│    │ User Management │
│   Module        │    │    Module       │    │     Module      │
│   Port 5001     │    │   Port 5002     │    │   Port 5003     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   API Gateway   │
                    │   Port 5000     │
                    │ (Optional)      │
                    └─────────────────┘
```

## Authentication

All inter-module communication uses JWT tokens for authentication. API keys are also supported for service-to-service communication.

### Token Types
- **JWT Tokens**: For user-authenticated requests
- **API Keys**: For service-to-service communication
- **Service Tokens**: For internal module communication

## Mining Core Module API

### Base URL: `http://localhost:5001`

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "module": "mining_core",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "features": ["Mining Profitability Calculation", "Technical Analysis", ...]
}
```

#### Calculate Mining Profitability
```http
POST /api/calculate/profitability
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "miner_model": "Antminer S19 Pro",
  "hashrate": 110,
  "power_consumption": 3250,
  "electricity_cost": 0.08,
  "btc_price": 43000,
  "network_difficulty": 83148355189239,
  "miner_price": 2500
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "miner_model": "Antminer S19 Pro",
    "hashrate_ths": 110,
    "power_consumption_w": 3250,
    "electricity_cost_kwh": 0.08,
    "btc_price_usd": 43000,
    "calculations": {
      "daily_revenue_usd": 25.30,
      "daily_electricity_cost_usd": 6.24,
      "daily_profit_usd": 19.06,
      "monthly_profit_usd": 571.8,
      "yearly_profit_usd": 6956.9,
      "roi_days": 131
    },
    "calculated_at": "2024-01-01T00:00:00Z"
  }
}
```

#### Get Market Analytics
```http
GET /api/analytics/market?timeframe=24h&indicators=btc_price,network_metrics
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "timeframe": "24h",
    "btc_price": {
      "current": 43000,
      "change_24h": 2.5,
      "change_7d": -1.2,
      "high_24h": 43500,
      "low_24h": 42200
    },
    "network_metrics": {
      "difficulty": 83148355189239,
      "hashrate_ehs": 650,
      "next_difficulty_adjustment": 1.2,
      "blocks_until_adjustment": 1456
    },
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

#### Generate Mining Report
```http
POST /api/reports/generate
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "report_type": "standard",
  "period": "30d",
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "report_id": "report_1704067200",
    "report_type": "standard",
    "period": "30d",
    "status": "completed",
    "file_url": "/reports/report_1704067200.pdf",
    "summary": {
      "total_calculations": 145,
      "profitable_configs": 89,
      "average_daily_profit": 15.30,
      "best_miner_model": "Antminer S21",
      "recommended_electricity_cost": 0.06
    }
  }
}
```

## Web3 Integration Module API

### Base URL: `http://localhost:5002`

#### Health Check
```http
GET /health
```

#### Wallet Authentication
```http
POST /api/auth/wallet
Content-Type: application/json
```

**Request Body:**
```json
{
  "wallet_address": "0x742d35Cc6635C0532925a3b8D564c502aE684b72",
  "signature": "0x...",
  "message": "Sign this message to authenticate",
  "wallet_type": "metamask"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "wallet_address": "0x742d35Cc6635C0532925a3b8D564c502aE684b72",
    "wallet_type": "metamask",
    "authenticated": true,
    "auth_token": "wallet_auth_1704067200",
    "authenticated_at": "2024-01-01T00:00:00Z",
    "blockchain_network": "ethereum",
    "wallet_balance": {
      "eth": 1.5,
      "usdc": 1000.0
    }
  }
}
```

#### Create Payment Order
```http
POST /api/payments/create
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "amount": 100,
  "currency": "USDC",
  "user_id": "user_123",
  "payment_purpose": "subscription",
  "wallet_address": "0x742d35Cc6635C0532925a3b8D564c502aE684b72"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "payment_id": "pay_1704067200",
    "amount": 100,
    "currency": "USDC",
    "status": "pending",
    "to_wallet": "0x742d35Cc6635C0532925a3b8D564c502aE684b72",
    "expires_at": 1704070800,
    "gas_estimate": {
      "gas_limit": 21000,
      "gas_price_gwei": 20,
      "estimated_fee_usd": 2.5
    }
  }
}
```

#### Check Payment Status
```http
GET /api/payments/{payment_id}/status
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "payment_id": "pay_1704067200",
    "status": "completed",
    "transaction_hash": "0xpay_1704067200abcd1234567890",
    "confirmations": 12,
    "required_confirmations": 6,
    "completed_at": "2024-01-01T00:00:00Z"
  }
}
```

#### Mint SLA NFT
```http
POST /api/nft/sla/mint
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "user_id": "user_123",
  "calculation_data": {...},
  "sla_metadata": {
    "verification_level": "premium",
    "calculation_accuracy": "99.9%"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "nft_id": "nft_1704067200",
    "contract_address": "0x1234567890abcdef1234567890abcdef12345678",
    "token_id": 1704067200,
    "transaction_hash": "0xnft_1704067200mint1234567890",
    "ipfs_metadata_url": "ipfs://Qmnft_1704067200metadata",
    "ipfs_image_url": "ipfs://Qmnft_1704067200image",
    "metadata": {
      "name": "Mining SLA Certificate #nft_1704067200",
      "description": "Verified mining calculation and SLA certificate"
    }
  }
}
```

#### Store Data on IPFS
```http
POST /api/storage/ipfs
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "data": {
    "calculation_result": {...},
    "user_id": "user_123"
  },
  "metadata": {
    "content_type": "application/json"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "ipfs_hash": "Qm1704067200DataHash",
    "ipfs_url": "ipfs://Qm1704067200DataHash",
    "gateway_url": "https://gateway.ipfs.io/ipfs/Qm1704067200DataHash",
    "size_bytes": 1024,
    "stored_at": "2024-01-01T00:00:00Z",
    "pin_status": "pinned"
  }
}
```

## User Management Module API

### Base URL: `http://localhost:5003`

#### Health Check
```http
GET /health
```

#### Validate User Token
```http
POST /api/auth/validate
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "jwt_token_here"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "user_id": "user_123",
    "email": "user@example.com",
    "role": "user",
    "subscription_level": "basic"
  }
}
```

#### Check User Subscription
```http
GET /api/users/{user_id}/subscription
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "subscription_level": "basic",
    "status": "active",
    "expires_at": "2024-12-31T23:59:59Z",
    "features": {
      "advanced_analytics": true,
      "api_access": true,
      "export_features": true
    }
  }
}
```

#### Check User Permissions
```http
POST /api/users/{user_id}/permissions
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "required_permissions": ["mining:calculate", "mining:analyze"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "has_permissions": true,
    "user_permissions": ["mining:calculate", "mining:analyze", "web3:authenticate"],
    "required_permissions": ["mining:calculate", "mining:analyze"]
  }
}
```

#### Update KYC Status
```http
PUT /api/users/{user_id}/kyc
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "kyc_status": "approved",
  "kyc_data": {
    "verification_level": "enhanced",
    "verified_fields": ["identity", "address", "phone"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "kyc_status": "approved",
    "updated_at": "2024-01-01T00:00:00Z",
    "message": "KYC status updated successfully"
  }
}
```

#### Process Payment Completion
```http
POST /api/users/{user_id}/payments/complete
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "payment_id": "pay_1704067200",
  "amount": 100,
  "currency": "USDC",
  "subscription_upgrade": "premium"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "payment_id": "pay_1704067200",
    "processed_at": "2024-01-01T00:00:00Z",
    "subscription_updated": true,
    "new_subscription_level": "premium"
  }
}
```

## API Gateway (Optional)

### Base URL: `http://localhost:5000`

The API Gateway provides a unified entry point and routes requests to appropriate modules.

#### Gateway Info
```http
GET /gateway/info
```

#### Route Mappings
- `/api/mining/*` → Mining Core Module
- `/api/web3/*` → Web3 Integration Module
- `/api/users/*` → User Management Module
- `/api/auth/*` → User Management Module

#### Example Proxied Request
```http
GET /api/mining/analytics/market
Authorization: Bearer <jwt_token>
```

This request is automatically routed to the Mining Core Module.

## Service Discovery

### Service Registry: `http://localhost:5005`

#### List All Services
```http
GET /services
```

#### Discover Service Instances
```http
GET /services/{service_name}?healthy_only=true
```

#### Register Service
```http
POST /services/register
Content-Type: application/json
```

**Request Body:**
```json
{
  "service_name": "mining_core",
  "instance_id": "mining_core_1",
  "host": "localhost",
  "port": 5001,
  "health_endpoint": "/health",
  "metadata": {}
}
```

#### Service Heartbeat
```http
POST /services/{service_name}/{instance_id}/heartbeat
```

## Error Handling

All APIs return consistent error responses:

```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human readable error message",
  "details": {
    "additional": "error context"
  }
}
```

### Common Error Codes
- `INVALID_REQUEST`: Request validation failed
- `AUTHENTICATION_FAILED`: Invalid or expired token
- `AUTHORIZATION_FAILED`: Insufficient permissions
- `SERVICE_UNAVAILABLE`: Target service is not available
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Server error

## Rate Limiting

All endpoints are rate limited:
- **Anonymous requests**: 20 requests/minute
- **Authenticated requests**: 100 requests/minute
- **Premium users**: 500 requests/minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067800
```

## Deployment Modes

### 1. Standalone Mode
Each module runs independently on its own port. Direct communication between modules.

### 2. Combined Mode  
All modules + API Gateway + Service Registry run together. Communication via service discovery.

### 3. Gateway Mode
API Gateway only, modules run elsewhere. Centralized routing and load balancing.

## Security

### HTTPS
Production deployments use HTTPS for all communication.

### API Key Rotation
API keys are automatically rotated every 24 hours.

### Request Signing
Service-to-service requests are signed with HMAC-SHA256.

### Rate Limiting
Protects against abuse and DoS attacks.

## Monitoring and Health Checks

### Health Check Format
```json
{
  "status": "healthy",
  "module": "service_name", 
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0"
}
```

### Metrics Collection
- Request counts and response times
- Error rates by endpoint
- Service availability
- Resource utilization

## Integration Examples

### Complete Mining Analysis Workflow

1. **Authenticate User**
```bash
curl -X POST http://localhost:5003/api/auth/validate \
  -H "Content-Type: application/json" \
  -d '{"token": "user_jwt_token"}'
```

2. **Check Subscription**
```bash
curl -X GET http://localhost:5003/api/users/user_123/subscription \
  -H "Authorization: Bearer user_jwt_token"
```

3. **Calculate Mining Profitability**
```bash
curl -X POST http://localhost:5001/api/calculate/profitability \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user_jwt_token" \
  -d '{
    "miner_model": "Antminer S19 Pro",
    "hashrate": 110,
    "power_consumption": 3250,
    "electricity_cost": 0.08
  }'
```

4. **Store Results on IPFS**
```bash
curl -X POST http://localhost:5002/api/storage/ipfs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user_jwt_token" \
  -d '{
    "data": {"calculation_result": "..."},
    "metadata": {"user_id": "user_123"}
  }'
```

5. **Mint SLA NFT**
```bash
curl -X POST http://localhost:5002/api/nft/sla/mint \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user_jwt_token" \
  -d '{
    "user_id": "user_123",
    "calculation_data": "...",
    "sla_metadata": {"verification_level": "premium"}
  }'
```

### Payment Processing Workflow

1. **Create Payment Order**
```bash
curl -X POST http://localhost:5002/api/payments/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user_jwt_token" \
  -d '{
    "amount": 100,
    "currency": "USDC",
    "user_id": "user_123",
    "wallet_address": "0x..."
  }'
```

2. **Check Payment Status**
```bash
curl -X GET http://localhost:5002/api/payments/pay_123/status \
  -H "Authorization: Bearer user_jwt_token"
```

3. **Process Payment Completion**
```bash
curl -X POST http://localhost:5003/api/users/user_123/payments/complete \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user_jwt_token" \
  -d '{
    "payment_id": "pay_123",
    "amount": 100,
    "subscription_upgrade": "premium"
  }'
```

This completes the comprehensive API documentation for the HashInsight module communication system.