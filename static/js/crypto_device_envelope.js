/**
 * Device Envelope Encryption Module
 * 设备信封加密 - X25519 Box + AES-256-GCM
 * 
 * Uses TweetNaCl for X25519 operations (browser-compatible)
 * 
 * Architecture:
 *   Browser                              Edge Collector
 *   ┌─────────────────────────┐         ┌─────────────────────────┐
 *   │ 1. Get device pubkey    │ ←──────→│ Has X25519 keypair      │
 *   │ 2. Generate random DEK  │         │                         │
 *   │ 3. Seal DEK with pubkey │ ───────→│ Open DEK with privkey   │
 *   │ 4. Encrypt creds w/DEK  │ ───────→│ Decrypt creds w/DEK     │
 *   │ 5. Upload envelope      │         │                         │
 *   └─────────────────────────┘         └─────────────────────────┘
 * 
 * Requires: TweetNaCl (loaded via /static/js/nacl.min.js)
 */
(function() {
    'use strict';

    const SCHEMA_VERSION = 1;
    const DEK_SIZE = 32;
    const NONCE_SIZE = 12;

    let nacl = null;
    let naclUtil = null;
    let isInitialized = false;

    async function ensureNaClLoaded() {
        if (isInitialized && nacl) {
            console.log('[DeviceEnvelope] Already initialized');
            return;
        }

        console.log('[DeviceEnvelope] Ensuring TweetNaCl loaded...');

        // Check if nacl is already loaded globally
        if (typeof window.nacl !== 'undefined') {
            nacl = window.nacl;
            naclUtil = window.nacl.util || window.naclUtil;
            isInitialized = true;
            console.log('[DeviceEnvelope] TweetNaCl ready from global');
            return;
        }

        // Wait for nacl to be available (it may be loading from template script)
        let retries = 0;
        const maxRetries = 50;
        while (typeof window.nacl === 'undefined' && retries < maxRetries) {
            await new Promise(resolve => setTimeout(resolve, 100));
            retries++;
            if (retries % 10 === 0) {
                console.log('[DeviceEnvelope] Waiting for TweetNaCl...', retries * 100, 'ms');
            }
        }

        if (typeof window.nacl === 'undefined') {
            // Try loading dynamically
            console.log('[DeviceEnvelope] Loading TweetNaCl dynamically...');
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = '/static/js/nacl.min.js';
                script.onload = () => {
                    console.log('[DeviceEnvelope] nacl.min.js loaded');
                    resolve();
                };
                script.onerror = reject;
                document.head.appendChild(script);
            });

            // Wait again
            let waitRetries = 0;
            while (typeof window.nacl === 'undefined' && waitRetries < 30) {
                await new Promise(resolve => setTimeout(resolve, 100));
                waitRetries++;
            }
        }

        if (typeof window.nacl === 'undefined') {
            throw new Error('Failed to load TweetNaCl - window.nacl is undefined');
        }

        nacl = window.nacl;
        
        // Load nacl-util for encoding helpers
        if (typeof window.naclUtil === 'undefined' && typeof nacl.util === 'undefined') {
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = '/static/js/nacl-util.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }
        
        naclUtil = nacl.util || window.naclUtil || {};
        isInitialized = true;
        console.log('[DeviceEnvelope] TweetNaCl ready! box.keyPair available:', typeof nacl.box !== 'undefined');
    }

    function base64ToBytes(base64) {
        if (naclUtil && naclUtil.decodeBase64) {
            return naclUtil.decodeBase64(base64);
        }
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes;
    }

    function bytesToBase64(bytes) {
        if (naclUtil && naclUtil.encodeBase64) {
            return naclUtil.encodeBase64(bytes);
        }
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    function generateDEK() {
        return nacl.randomBytes(DEK_SIZE);
    }

    function generateNonce() {
        return crypto.getRandomValues(new Uint8Array(NONCE_SIZE));
    }

    /**
     * Implement sealed box using TweetNaCl primitives
     * Sealed box = ephemeral keypair + crypto_box
     */
    function sealDEK(dek, recipientPublicKeyBase64) {
        const recipientPubKey = base64ToBytes(recipientPublicKeyBase64);
        
        if (recipientPubKey.length !== 32) {
            throw new Error('Invalid public key length. Expected 32 bytes for X25519.');
        }

        // Generate ephemeral keypair
        const ephemeralKeypair = nacl.box.keyPair();
        
        // Generate nonce from ephemeral public key + recipient public key
        // This is the libsodium sealed box approach
        const nonceData = new Uint8Array(48);
        nonceData.set(ephemeralKeypair.publicKey, 0);
        nonceData.set(recipientPubKey, 32);
        
        // Use first 24 bytes of hash as nonce (NaCl box requires 24-byte nonce)
        // Simple approach: concat and use nacl.hash if available, or use the keys directly
        const nonce = new Uint8Array(24);
        for (let i = 0; i < 24; i++) {
            nonce[i] = nonceData[i] ^ nonceData[i + 24];
        }
        
        // Encrypt DEK using NaCl box
        const encrypted = nacl.box(dek, nonce, recipientPubKey, ephemeralKeypair.secretKey);
        
        // Sealed box format: ephemeral_pubkey (32) + encrypted_message (16 MAC + message length)
        const sealed = new Uint8Array(32 + encrypted.length);
        sealed.set(ephemeralKeypair.publicKey, 0);
        sealed.set(encrypted, 32);
        
        return bytesToBase64(sealed);
    }

    async function encryptPayloadWithDEK(payload, dek, nonce) {
        const payloadBytes = new TextEncoder().encode(JSON.stringify(payload));

        const cryptoKey = await crypto.subtle.importKey(
            'raw',
            dek,
            { name: 'AES-GCM', length: 256 },
            false,
            ['encrypt']
        );

        const cipherBuffer = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: nonce },
            cryptoKey,
            payloadBytes
        );

        return bytesToBase64(new Uint8Array(cipherBuffer));
    }

    async function decryptPayloadWithDEK(encryptedPayloadBase64, dek, nonceBase64) {
        const encryptedBytes = base64ToBytes(encryptedPayloadBase64);
        const nonce = base64ToBytes(nonceBase64);

        const cryptoKey = await crypto.subtle.importKey(
            'raw',
            dek,
            { name: 'AES-GCM', length: 256 },
            false,
            ['decrypt']
        );

        const decryptedBuffer = await crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: nonce },
            cryptoKey,
            encryptedBytes
        );

        return JSON.parse(new TextDecoder().decode(decryptedBuffer));
    }

    const DeviceEnvelope = {
        SCHEMA_VERSION,

        async init() {
            await ensureNaClLoaded();
            console.log('[DeviceEnvelope] Initialized with TweetNaCl');
        },

        isReady() {
            return isInitialized;
        },

        async encrypt(credentials, devicePublicKeyBase64, options = {}) {
            await ensureNaClLoaded();

            const { 
                deviceId = null,
                minerId = null,
                tenantId = null,
            } = options;

            const dek = generateDEK();
            const nonce = generateNonce();

            const wrappedDek = sealDEK(dek, devicePublicKeyBase64);
            const encryptedPayload = await encryptPayloadWithDEK(credentials, dek, nonce);

            const aad = {
                schema_version: SCHEMA_VERSION,
                device_id: deviceId,
                miner_id: minerId,
                tenant_id: tenantId,
                timestamp: Date.now(),
                algorithm: 'X25519-BOX+AES256GCM'
            };

            return {
                wrapped_dek: wrappedDek,
                encrypted_payload: encryptedPayload,
                nonce: bytesToBase64(nonce),
                aad: JSON.stringify(aad)
            };
        },

        async encryptConnection(connectionData, devicePublicKeyBase64, options = {}) {
            const fullConnection = {
                ip_address: connectionData.ip || connectionData.ip_address || '',
                port: connectionData.port || 4028,
                username: connectionData.username || 'root',
                password: connectionData.password || '',
                pool_url: connectionData.pool_url || '',
                pool_user: connectionData.pool_user || '',
                pool_password: connectionData.pool_password || ''
            };

            return this.encrypt(fullConnection, devicePublicKeyBase64, options);
        },

        /**
         * Encrypt IP address using E2EE (Strategy 3)
         * IP is encrypted in browser, server never sees plaintext
         * Only Edge Collector with matching private key can decrypt
         */
        async encryptIP(ipAddress, devicePublicKeyBase64, options = {}) {
            await ensureNaClLoaded();

            const { 
                deviceId = null,
                minerId = null,
                tenantId = null,
                macAddress = null
            } = options;

            if (!ipAddress) {
                throw new Error('IP address is required');
            }

            const dek = generateDEK();
            const nonce = generateNonce();

            const ipData = {
                ip: ipAddress,
                mac: macAddress,
                encrypted_at: Date.now(),
                strategy: 3  // E2EE strategy marker
            };

            const wrappedDek = sealDEK(dek, devicePublicKeyBase64);
            const encryptedPayload = await encryptPayloadWithDEK(ipData, dek, nonce);

            const aad = {
                schema_version: SCHEMA_VERSION,
                device_id: deviceId,
                miner_id: minerId,
                tenant_id: tenantId,
                timestamp: Date.now(),
                algorithm: 'X25519-BOX+AES256GCM',
                data_type: 'ip_address'
            };

            return {
                wrapped_dek: wrappedDek,
                encrypted_payload: encryptedPayload,
                nonce: bytesToBase64(nonce),
                aad: JSON.stringify(aad),
                encrypted_ip_marker: 'E2EE:v1'  // Marker for server-side recognition
            };
        },

        /**
         * Create a complete E2EE encrypted miner data package
         * Includes IP, MAC, and credentials in a single encrypted envelope
         */
        async encryptMinerData(minerData, devicePublicKeyBase64, options = {}) {
            await ensureNaClLoaded();

            const { 
                deviceId = null,
                minerId = null,
                tenantId = null,
            } = options;

            const fullData = {
                ip_address: minerData.ip || minerData.ip_address || '',
                mac_address: minerData.mac || minerData.mac_address || '',
                port: minerData.port || 4028,
                username: minerData.username || 'root',
                password: minerData.password || '',
                pool_url: minerData.pool_url || '',
                pool_user: minerData.pool_user || '',
                pool_password: minerData.pool_password || '',
                encrypted_at: Date.now(),
                ip_strategy: 3  // E2EE IP strategy
            };

            const dek = generateDEK();
            const nonce = generateNonce();

            const wrappedDek = sealDEK(dek, devicePublicKeyBase64);
            const encryptedPayload = await encryptPayloadWithDEK(fullData, dek, nonce);

            const aad = {
                schema_version: SCHEMA_VERSION,
                device_id: deviceId,
                miner_id: minerId,
                tenant_id: tenantId,
                timestamp: Date.now(),
                algorithm: 'X25519-BOX+AES256GCM',
                data_type: 'full_miner_data'
            };

            return {
                wrapped_dek: wrappedDek,
                encrypted_payload: encryptedPayload,
                nonce: bytesToBase64(nonce),
                aad: JSON.stringify(aad),
                includes_ip: true,
                includes_credentials: true
            };
        },

        /**
         * Get masked IP for UI display (Strategy 1)
         * Returns xxx-masked IP like 192.168.1.xxx
         */
        maskIP(ipAddress) {
            if (!ipAddress) return '---';
            const parts = ipAddress.split('.');
            if (parts.length === 4) {
                return `${parts[0]}.${parts[1]}.${parts[2]}.xxx`;
            }
            // IPv6 handling
            const ipv6Parts = ipAddress.split(':');
            if (ipv6Parts.length >= 4) {
                return ipv6Parts.slice(0, 3).join(':') + ':xxxx';
            }
            return 'xxx.xxx.xxx.xxx';
        },

        /**
         * Check if an IP string is E2EE encrypted
         */
        isE2EEEncrypted(ipValue) {
            if (!ipValue) return false;
            return ipValue.startsWith('E2EE:') || 
                   (typeof ipValue === 'object' && ipValue.encrypted_ip_marker);
        },

        validatePublicKey(publicKeyBase64) {
            try {
                const bytes = base64ToBytes(publicKeyBase64);
                return bytes.length === 32;
            } catch (e) {
                return false;
            }
        },

        async generateKeypair() {
            console.log('[DeviceEnvelope] generateKeypair called');
            await ensureNaClLoaded();
            console.log('[DeviceEnvelope] nacl loaded, calling box.keyPair');
            
            const keypair = nacl.box.keyPair();
            console.log('[DeviceEnvelope] Raw keypair generated:', {
                publicKeyLength: keypair?.publicKey?.length,
                secretKeyLength: keypair?.secretKey?.length
            });
            
            const publicKeyBase64 = bytesToBase64(keypair.publicKey);
            const privateKeyBase64 = bytesToBase64(keypair.secretKey);
            
            console.log('[DeviceEnvelope] Generated X25519 keypair:', {
                publicKey: publicKeyBase64,
                privateKey: privateKeyBase64?.substring(0, 10) + '...'
            });
            
            return {
                publicKey: publicKeyBase64,
                privateKey: privateKeyBase64
            };
        },

        async testSelfEncryptDecrypt(testMessage = 'Test message') {
            await ensureNaClLoaded();
            
            const keypair = nacl.box.keyPair();
            const publicKeyBase64 = bytesToBase64(keypair.publicKey);
            
            console.log('[DeviceEnvelope] Test keypair generated');
            
            const envelope = await this.encrypt(
                { message: testMessage },
                publicKeyBase64,
                { deviceId: 1, minerId: 100 }
            );
            
            console.log('[DeviceEnvelope] Envelope created:', {
                wrapped_dek_length: envelope.wrapped_dek.length,
                encrypted_payload_length: envelope.encrypted_payload.length,
                nonce: envelope.nonce
            });
            
            // Unseal the DEK (reverse of seal operation)
            const sealedBytes = base64ToBytes(envelope.wrapped_dek);
            const ephemeralPubKey = sealedBytes.slice(0, 32);
            const encryptedDek = sealedBytes.slice(32);
            
            // Recreate nonce
            const nonceData = new Uint8Array(48);
            nonceData.set(ephemeralPubKey, 0);
            nonceData.set(keypair.publicKey, 32);
            const nonce = new Uint8Array(24);
            for (let i = 0; i < 24; i++) {
                nonce[i] = nonceData[i] ^ nonceData[i + 24];
            }
            
            const dekBytes = nacl.box.open(encryptedDek, nonce, ephemeralPubKey, keypair.secretKey);
            
            if (!dekBytes) {
                throw new Error('Failed to unseal DEK');
            }
            
            const decrypted = await decryptPayloadWithDEK(
                envelope.encrypted_payload,
                dekBytes,
                envelope.nonce
            );
            
            console.log('[DeviceEnvelope] Decrypted:', decrypted);
            
            return {
                success: decrypted.message === testMessage,
                original: testMessage,
                decrypted: decrypted.message
            };
        }
    };

    if (typeof window !== 'undefined') {
        window.DeviceEnvelope = DeviceEnvelope;
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = DeviceEnvelope;
    }

    console.log('[DeviceEnvelope] Module loaded. Call DeviceEnvelope.init() to initialize.');

})();
