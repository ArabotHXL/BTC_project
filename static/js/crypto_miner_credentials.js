/**
 * HashInsight Enterprise - Miner Credentials E2E Encryption
 * 矿机凭证端到端加密模块
 * 
 * 使用 WebCrypto API 实现 PBKDF2-SHA256 + AES-GCM-256 加密
 * 后端仅存储密文，本地 Agent 使用相同主密码解密
 * 
 * 安全特性:
 * - 密钥永不离开客户端
 * - 使用 100,000 次 PBKDF2 迭代
 * - 每次加密使用随机 IV
 * - 密文包含版本和算法信息便于未来升级
 */

const MinerCredentialsCrypto = (function() {
    'use strict';
    
    const CRYPTO_VERSION = 1;
    const KDF_ALGORITHM = 'PBKDF2-SHA256';
    const ENCRYPTION_ALGORITHM = 'AES-GCM';
    const KEY_LENGTH = 256;
    const IV_LENGTH = 12;
    const SALT_LENGTH = 16;
    const ITERATIONS = 100000;
    
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();
    
    function arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
    
    function base64ToArrayBuffer(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
    }
    
    function generateRandomBytes(length) {
        const bytes = new Uint8Array(length);
        crypto.getRandomValues(bytes);
        return bytes;
    }
    
    async function deriveKeyFromPassphrase(passphrase, salt, iterations = ITERATIONS) {
        const keyMaterial = await crypto.subtle.importKey(
            'raw',
            encoder.encode(passphrase),
            { name: 'PBKDF2' },
            false,
            ['deriveBits', 'deriveKey']
        );
        
        const key = await crypto.subtle.deriveKey(
            {
                name: 'PBKDF2',
                salt: salt,
                iterations: iterations,
                hash: 'SHA-256'
            },
            keyMaterial,
            { name: 'AES-GCM', length: KEY_LENGTH },
            false,
            ['encrypt', 'decrypt']
        );
        
        return key;
    }
    
    async function encryptMinerCredentials(passphrase, credentialsObj) {
        if (!passphrase || passphrase.length < 8) {
            throw new Error('主密码必须至少8个字符 / Master passphrase must be at least 8 characters');
        }
        
        const validatedCredentials = validateCredentialsObject(credentialsObj);
        
        const salt = generateRandomBytes(SALT_LENGTH);
        const iv = generateRandomBytes(IV_LENGTH);
        
        const key = await deriveKeyFromPassphrase(passphrase, salt, ITERATIONS);
        
        const plaintext = encoder.encode(JSON.stringify(validatedCredentials));
        
        const ciphertext = await crypto.subtle.encrypt(
            {
                name: 'AES-GCM',
                iv: iv
            },
            key,
            plaintext
        );
        
        const encryptedBlock = {
            v: CRYPTO_VERSION,
            algo: ENCRYPTION_ALGORITHM,
            kdf: KDF_ALGORITHM,
            iterations: ITERATIONS,
            salt: arrayBufferToBase64(salt),
            iv: arrayBufferToBase64(iv),
            ciphertext: arrayBufferToBase64(ciphertext)
        };
        
        return JSON.stringify(encryptedBlock);
    }
    
    async function decryptMinerCredentials(passphrase, encryptedJson) {
        const encryptedBlock = typeof encryptedJson === 'string' 
            ? JSON.parse(encryptedJson) 
            : encryptedJson;
        
        if (encryptedBlock.v !== CRYPTO_VERSION) {
            throw new Error(`不支持的加密版本: ${encryptedBlock.v} / Unsupported encryption version`);
        }
        
        if (encryptedBlock.algo !== ENCRYPTION_ALGORITHM || encryptedBlock.kdf !== KDF_ALGORITHM) {
            throw new Error('不支持的加密算法 / Unsupported encryption algorithm');
        }
        
        const salt = new Uint8Array(base64ToArrayBuffer(encryptedBlock.salt));
        const iv = new Uint8Array(base64ToArrayBuffer(encryptedBlock.iv));
        const ciphertext = base64ToArrayBuffer(encryptedBlock.ciphertext);
        
        const key = await deriveKeyFromPassphrase(passphrase, salt, encryptedBlock.iterations);
        
        try {
            const plaintext = await crypto.subtle.decrypt(
                {
                    name: 'AES-GCM',
                    iv: iv
                },
                key,
                ciphertext
            );
            
            const decryptedJson = decoder.decode(plaintext);
            return JSON.parse(decryptedJson);
        } catch (error) {
            throw new Error('解密失败：密码错误或数据损坏 / Decryption failed: incorrect passphrase or corrupted data');
        }
    }
    
    function validateCredentialsObject(credentials) {
        const validated = {};
        
        if (credentials.ip) {
            const ipPattern = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?:[a-fA-F0-9]{1,4}:){7}[a-fA-F0-9]{1,4}$|^[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)*$/;
            if (!ipPattern.test(credentials.ip)) {
                throw new Error('无效的IP地址或主机名 / Invalid IP address or hostname');
            }
            validated.ip = credentials.ip;
        }
        
        if (credentials.api_port !== undefined) {
            const port = parseInt(credentials.api_port, 10);
            if (isNaN(port) || port < 1 || port > 65535) {
                throw new Error('无效的API端口 / Invalid API port');
            }
            validated.api_port = port;
        } else {
            validated.api_port = 4028;
        }
        
        if (credentials.ssh_port !== undefined) {
            const port = parseInt(credentials.ssh_port, 10);
            if (isNaN(port) || port < 1 || port > 65535) {
                throw new Error('无效的SSH端口 / Invalid SSH port');
            }
            validated.ssh_port = port;
        } else {
            validated.ssh_port = 22;
        }
        
        if (credentials.ssh_user) {
            validated.ssh_user = String(credentials.ssh_user).substring(0, 64);
        }
        
        if (credentials.ssh_password) {
            validated.ssh_password = String(credentials.ssh_password);
        }
        
        if (credentials.api_key) {
            validated.api_key = String(credentials.api_key);
        }
        
        if (credentials.pool_password) {
            validated.pool_password = String(credentials.pool_password);
        }
        
        validated.encrypted_at = new Date().toISOString();
        
        return validated;
    }
    
    function getEncryptedBlockHash(encryptedJson) {
        const encryptedBlock = typeof encryptedJson === 'string' 
            ? JSON.parse(encryptedJson) 
            : encryptedJson;
        
        const hashInput = `${encryptedBlock.salt}:${encryptedBlock.iv}:${encryptedBlock.ciphertext.substring(0, 32)}`;
        
        let hash = 0;
        for (let i = 0; i < hashInput.length; i++) {
            const char = hashInput.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        
        return Math.abs(hash).toString(16).padStart(8, '0');
    }
    
    function getEncryptedBlockSize(encryptedJson) {
        return typeof encryptedJson === 'string' ? encryptedJson.length : JSON.stringify(encryptedJson).length;
    }
    
    function isEncryptedCredentials(data) {
        try {
            const obj = typeof data === 'string' ? JSON.parse(data) : data;
            return obj && 
                   typeof obj.v === 'number' &&
                   obj.algo === ENCRYPTION_ALGORITHM &&
                   obj.kdf === KDF_ALGORITHM &&
                   typeof obj.salt === 'string' &&
                   typeof obj.iv === 'string' &&
                   typeof obj.ciphertext === 'string';
        } catch {
            return false;
        }
    }
    
    async function verifyPassphrase(passphrase, encryptedJson) {
        try {
            await decryptMinerCredentials(passphrase, encryptedJson);
            return true;
        } catch {
            return false;
        }
    }
    
    async function reEncryptCredentials(oldPassphrase, newPassphrase, encryptedJson) {
        const credentials = await decryptMinerCredentials(oldPassphrase, encryptedJson);
        
        const newEncrypted = await encryptMinerCredentials(newPassphrase, credentials);
        
        return newEncrypted;
    }
    
    function createSecureConnectionForm(containerId, options = {}) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container element not found: ${containerId}`);
            return null;
        }
        
        const defaultOptions = {
            showSSH: true,
            showAPIKey: true,
            showPoolPassword: false,
            defaultPort: 4028,
            labels: {
                ip: 'IP地址 / IP Address',
                api_port: 'API端口 / API Port',
                ssh_user: 'SSH用户名 / SSH Username',
                ssh_password: 'SSH密码 / SSH Password',
                api_key: 'API密钥 / API Key',
                pool_password: '矿池密码 / Pool Password',
                master_passphrase: '主密码 / Master Passphrase',
                confirm_passphrase: '确认主密码 / Confirm Passphrase'
            }
        };
        
        const opts = { ...defaultOptions, ...options };
        
        const formHtml = `
            <div class="secure-connection-section">
                <h5 class="section-title">
                    <i class="bi bi-shield-lock-fill text-warning me-2"></i>
                    安全连接设置 / Secure Connection Settings
                </h5>
                <div class="alert alert-info small mb-3">
                    <i class="bi bi-info-circle me-1"></i>
                    所有敏感信息在浏览器中加密，服务器仅存储密文。
                    <br>All sensitive data is encrypted in browser, server only stores ciphertext.
                </div>
                
                <div class="row g-3">
                    <div class="col-md-8">
                        <label class="form-label">${opts.labels.ip} <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="secure_miner_ip" 
                               placeholder="192.168.1.100" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">${opts.labels.api_port}</label>
                        <input type="number" class="form-control" id="secure_api_port" 
                               value="${opts.defaultPort}" min="1" max="65535">
                    </div>
                    
                    ${opts.showSSH ? `
                    <div class="col-md-6">
                        <label class="form-label">${opts.labels.ssh_user}</label>
                        <input type="text" class="form-control" id="secure_ssh_user" 
                               placeholder="root">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">${opts.labels.ssh_password}</label>
                        <input type="password" class="form-control" id="secure_ssh_password" 
                               placeholder="••••••••" autocomplete="new-password">
                    </div>
                    ` : ''}
                    
                    ${opts.showAPIKey ? `
                    <div class="col-12">
                        <label class="form-label">${opts.labels.api_key}</label>
                        <input type="password" class="form-control" id="secure_api_key" 
                               placeholder="矿机API密钥（如有）" autocomplete="new-password">
                    </div>
                    ` : ''}
                    
                    ${opts.showPoolPassword ? `
                    <div class="col-12">
                        <label class="form-label">${opts.labels.pool_password}</label>
                        <input type="password" class="form-control" id="secure_pool_password" 
                               placeholder="矿池密码" autocomplete="new-password">
                    </div>
                    ` : ''}
                    
                    <div class="col-md-6">
                        <label class="form-label">${opts.labels.master_passphrase} <span class="text-danger">*</span></label>
                        <input type="password" class="form-control" id="secure_master_passphrase" 
                               placeholder="至少8个字符" minlength="8" required autocomplete="new-password">
                        <div class="form-text text-muted small">
                            此密码不会上传到服务器，请牢记！
                        </div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">${opts.labels.confirm_passphrase} <span class="text-danger">*</span></label>
                        <input type="password" class="form-control" id="secure_confirm_passphrase" 
                               placeholder="再次输入主密码" minlength="8" required autocomplete="new-password">
                    </div>
                </div>
                
                <div id="secure_connection_status" class="mt-3" style="display: none;">
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle-fill me-1"></i>
                        凭证已加密 / Credentials encrypted
                        <span id="encrypted_hash_display" class="ms-2 badge bg-secondary"></span>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = formHtml;
        
        return {
            getCredentials: function() {
                return {
                    ip: document.getElementById('secure_miner_ip')?.value?.trim(),
                    api_port: document.getElementById('secure_api_port')?.value,
                    ssh_user: document.getElementById('secure_ssh_user')?.value?.trim(),
                    ssh_password: document.getElementById('secure_ssh_password')?.value,
                    api_key: document.getElementById('secure_api_key')?.value,
                    pool_password: document.getElementById('secure_pool_password')?.value
                };
            },
            getPassphrase: function() {
                return document.getElementById('secure_master_passphrase')?.value;
            },
            validate: function() {
                const ip = document.getElementById('secure_miner_ip')?.value?.trim();
                const passphrase = document.getElementById('secure_master_passphrase')?.value;
                const confirm = document.getElementById('secure_confirm_passphrase')?.value;
                
                if (!ip) {
                    throw new Error('请输入IP地址 / Please enter IP address');
                }
                if (!passphrase || passphrase.length < 8) {
                    throw new Error('主密码必须至少8个字符 / Master passphrase must be at least 8 characters');
                }
                if (passphrase !== confirm) {
                    throw new Error('两次输入的主密码不一致 / Passphrases do not match');
                }
                return true;
            },
            encrypt: async function() {
                this.validate();
                const credentials = this.getCredentials();
                const passphrase = this.getPassphrase();
                const encrypted = await encryptMinerCredentials(passphrase, credentials);
                
                const statusEl = document.getElementById('secure_connection_status');
                const hashEl = document.getElementById('encrypted_hash_display');
                if (statusEl) statusEl.style.display = 'block';
                if (hashEl) hashEl.textContent = `Hash: ${getEncryptedBlockHash(encrypted)}`;
                
                return encrypted;
            },
            clear: function() {
                ['secure_miner_ip', 'secure_api_port', 'secure_ssh_user', 
                 'secure_ssh_password', 'secure_api_key', 'secure_pool_password',
                 'secure_master_passphrase', 'secure_confirm_passphrase'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        if (id === 'secure_api_port') {
                            el.value = opts.defaultPort;
                        } else {
                            el.value = '';
                        }
                    }
                });
                const statusEl = document.getElementById('secure_connection_status');
                if (statusEl) statusEl.style.display = 'none';
            }
        };
    }
    
    return {
        VERSION: '1.0.0',
        CRYPTO_VERSION: CRYPTO_VERSION,
        
        deriveKeyFromPassphrase: deriveKeyFromPassphrase,
        encryptMinerCredentials: encryptMinerCredentials,
        decryptMinerCredentials: decryptMinerCredentials,
        
        isEncryptedCredentials: isEncryptedCredentials,
        verifyPassphrase: verifyPassphrase,
        reEncryptCredentials: reEncryptCredentials,
        
        getEncryptedBlockHash: getEncryptedBlockHash,
        getEncryptedBlockSize: getEncryptedBlockSize,
        
        createSecureConnectionForm: createSecureConnectionForm
    };
})();

if (typeof window !== 'undefined') {
    window.MinerCredentialsCrypto = MinerCredentialsCrypto;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = MinerCredentialsCrypto;
}
