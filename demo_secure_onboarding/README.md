# HashInsight Secure Miner Onboarding Demo

Enterprise-grade security demonstration for Bitcoin mining farm miner onboarding with:
- **Three-tier Credential Protection** (Mode 1/2/3)
- **ABAC (Attribute-Based Access Control)**
- **Guarded Approval Workflow** with Four-Eyes principle
- **Immutable Audit Log** with SHA-256 hash chain
- **Anti-rollback Protection** for E2EE credentials

## 🚀 Quick Start

```bash
cd demo_secure_onboarding
pip install -r requirements.txt
python main.py
```

Open browser at `http://localhost:3000`

## 🔐 Security Modes

### Mode 1: UI Masking
- Credentials stored in plaintext
- UI-level masking (IP: `192.168.xxx.xxx`)
- RBAC controls who can reveal
- Full audit trail

### Mode 2: Server Envelope Encryption
- Two-layer key management (MASTER_KEY → Site DEK)
- Credentials encrypted with Fernet (AES-256)
- Server can decrypt with approval
- Stored with `ENC:` prefix

### Mode 3: Device E2EE (End-to-End Encryption)
- Server never sees plaintext
- libsodium X25519 sealed box encryption
- Only authorized Edge devices can decrypt
- Anti-rollback counter protection
- Stored with `E2EE:` prefix

## 🛡️ ABAC Rules

1. **RULE-1**: Tenant isolation - actors can only access their own tenant's resources
2. **RULE-2**: Site isolation - actors can only access sites in their `allowed_site_ids`
3. **RULE-3**: Sensitive actions require `owner` or `admin` role + approval workflow
4. **RULE-4**: Discovery/Onboard allowed for `operator` within allowed sites
5. **RULE-5**: Edge decrypt requires valid device token + ACTIVE status

## 📋 Approval Workflow (Guarded Execution)

High-risk operations require:
1. **Create Change Request** - requester submits with reason
2. **Approve** - different person (Four-Eyes principle)
3. **Execute** - controlled execution with audit

Change Request types:
- `REVEAL_CREDENTIAL`
- `CHANGE_SITE_MODE`
- `BATCH_MIGRATE`
- `DEVICE_REVOKE`
- `UPDATE_CREDENTIAL`

## 📊 Audit Events

All sensitive actions are logged with hash chain integrity:
- `CREATE_SITE`, `CHANGE_MODE_*`, `DISCOVERY_SCAN`
- `CREATE_MINER`, `UPDATE_CREDENTIAL_*`
- `REVEAL_REQUEST/APPROVE/EXECUTE`
- `REGISTER_DEVICE`, `REVOKE_DEVICE`
- `EDGE_DECRYPT`, `ANTI_ROLLBACK_REJECT`
- `POLICY_DENY`

## ⚠️ Production Notes

**DEMO MODE WARNINGS:**

1. Device secret keys are stored for demo purposes (Edge decrypt simulation)
   - Set `DEMO_ALLOW_STORE_DEVICE_SECRET=false` in production
   - Real E2EE: secret key stays on Edge device only

2. MASTER_KEY derived from SESSION_SECRET
   - Use strong, unique SESSION_SECRET in production
   - Consider HSM/KMS for key management

3. SQLite for demo
   - Use PostgreSQL/production database for real deployment

## 🧪 Test Scenarios

1. **ABAC Isolation**: Create actors with different `allowed_site_ids`, verify filtering
2. **Four-Eyes**: Submit CR as operator, approve as admin (different person)
3. **Mode Switching**: Change site mode via CR workflow
4. **Discovery**: Scan CIDR, onboard miners
5. **E2EE Flow**: Register device, onboard in Mode 3, Edge decrypt
6. **Anti-rollback**: Try decrypting with lower counter → should fail
7. **Audit Verify**: Corrupt an event, verify chain → should detect break

## 📁 Project Structure

```
demo_secure_onboarding/
├── main.py                     # FastAPI application
├── db.py                       # SQLAlchemy models (7 tables)
├── services/
│   ├── audit_service.py        # Hash chain audit logging
│   ├── approval_service.py     # Guarded approval workflow
│   ├── credential_service.py   # Mode 1/2/3 credential handling
│   ├── discovery_service.py    # Network scanning simulation
│   ├── envelope_kms_service.py # MASTER_KEY/DEK management
│   └── policy_service.py       # ABAC policy evaluation
├── templates/
│   └── index.html              # Single-page UI
├── static/
│   ├── app.js                  # Frontend JavaScript
│   └── style.css               # Styling
├── requirements.txt
└── README.md
```

## 🔑 Environment Variables

```env
SESSION_SECRET=your-secure-secret    # For MASTER_KEY derivation
MASTER_SALT=your-salt                # PBKDF2 salt
DEMO_DATABASE_URL=sqlite:///./demo.db
DEMO_ALLOW_STORE_DEVICE_SECRET=true  # false in production!
```

## 📄 License

MIT License - For demonstration purposes only.
