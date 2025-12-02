/**
 * Miner E2EE (End-to-End Encryption) Module
 * 
 * Provides client-side encryption/decryption for miner connection credentials
 * using Web Crypto API with AES-256-GCM and PBKDF2 key derivation.
 * 
 * Plan A: Encrypt credentials only (username/password/pool_password)
 * Plan B: Encrypt full connection (IP/Port + credentials)
 * 
 * Security: All encryption/decryption happens in the browser.
 * The server only stores ciphertext and cannot decrypt.
 */
(function () {
    'use strict';

    const ALGO = 'AES-256-GCM';
    const VERSION = 1;
    const PBKDF2_ITERATIONS = 100000;
    const SALT_LENGTH = 16;
    const IV_LENGTH = 12;

    /**
     * Generate random bytes and encode as base64
     * @param {number} len - Number of random bytes
     * @returns {string} Base64 encoded random bytes
     */
    function randomBytesBase64(len) {
        const buf = crypto.getRandomValues(new Uint8Array(len));
        return btoa(String.fromCharCode.apply(null, buf));
    }

    /**
     * Convert base64 string to Uint8Array
     * @param {string} base64 - Base64 encoded string
     * @returns {Uint8Array}
     */
    function base64ToBytes(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes;
    }

    /**
     * Convert Uint8Array to base64 string
     * @param {Uint8Array} bytes
     * @returns {string}
     */
    function bytesToBase64(bytes) {
        return btoa(String.fromCharCode.apply(null, bytes));
    }

    /**
     * Derive AES-256 key from passphrase using PBKDF2
     * @param {string} passphrase - User's encryption passphrase
     * @param {string} saltBase64 - Base64 encoded salt
     * @returns {Promise<CryptoKey>}
     */
    async function deriveKeyFromPassphrase(passphrase, saltBase64) {
        const enc = new TextEncoder();
        const salt = base64ToBytes(saltBase64);

        const baseKey = await crypto.subtle.importKey(
            'raw',
            enc.encode(passphrase),
            { name: 'PBKDF2' },
            false,
            ['deriveKey']
        );

        const key = await crypto.subtle.deriveKey(
            {
                name: 'PBKDF2',
                salt: salt,
                iterations: PBKDF2_ITERATIONS,
                hash: 'SHA-256'
            },
            baseKey,
            { name: 'AES-GCM', length: 256 },
            false,
            ['encrypt', 'decrypt']
        );

        return key;
    }

    /**
     * Encrypt an object using AES-256-GCM
     * @param {Object} obj - Plain object to encrypt
     * @param {string} passphrase - Encryption passphrase
     * @returns {Promise<Object>} Encrypted block {ciphertext, iv, salt, algo, version}
     */
    async function encryptObject(obj, passphrase) {
        const enc = new TextEncoder();
        const plainText = JSON.stringify(obj);

        const saltBase64 = randomBytesBase64(SALT_LENGTH);
        const ivBytes = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
        const ivBase64 = bytesToBase64(ivBytes);

        const key = await deriveKeyFromPassphrase(passphrase, saltBase64);

        const cipherBuffer = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: ivBytes },
            key,
            enc.encode(plainText)
        );

        const cipherArray = new Uint8Array(cipherBuffer);
        const ciphertextBase64 = bytesToBase64(cipherArray);

        return {
            ciphertext: ciphertextBase64,
            iv: ivBase64,
            salt: saltBase64,
            algo: ALGO,
            version: VERSION
        };
    }

    /**
     * Decrypt an encrypted block back to object
     * @param {Object} block - Encrypted block {ciphertext, iv, salt, algo, version}
     * @param {string} passphrase - Decryption passphrase
     * @returns {Promise<Object>} Decrypted object
     * @throws {Error} If decryption fails (wrong passphrase or corrupted data)
     */
    async function decryptObject(block, passphrase) {
        if (!block || !block.ciphertext || !block.iv || !block.salt) {
            throw new Error('Invalid encrypted block: missing required fields');
        }

        if (block.algo !== ALGO) {
            throw new Error('Unsupported encryption algorithm: ' + block.algo);
        }

        const dec = new TextDecoder();

        const ivBytes = base64ToBytes(block.iv);
        const cipherBytes = base64ToBytes(block.ciphertext);

        const key = await deriveKeyFromPassphrase(passphrase, block.salt);

        try {
            const plainBuffer = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv: ivBytes },
                key,
                cipherBytes
            );

            const plainText = dec.decode(plainBuffer);
            return JSON.parse(plainText);
        } catch (e) {
            throw new Error('Decryption failed. Please check your passphrase.');
        }
    }

    /**
     * Encrypt miner credentials (Plan A)
     * @param {Object} credentials - {username, password, pool_password}
     * @param {string} passphrase - Encryption passphrase
     * @returns {Promise<Object>} Encrypted block
     */
    async function encryptCredentials(credentials, passphrase) {
        const cleanCreds = {
            username: credentials.username || '',
            password: credentials.password || '',
            pool_password: credentials.pool_password || ''
        };
        return encryptObject(cleanCreds, passphrase);
    }

    /**
     * Decrypt miner credentials (Plan A)
     * @param {Object} block - Encrypted credentials block
     * @param {string} passphrase - Decryption passphrase
     * @returns {Promise<Object>} {username, password, pool_password}
     */
    async function decryptCredentials(block, passphrase) {
        return decryptObject(block, passphrase);
    }

    /**
     * Encrypt full miner connection (Plan B)
     * @param {Object} connection - Full connection object
     * @param {string} passphrase - Encryption passphrase
     * @returns {Promise<Object>} Encrypted block
     */
    async function encryptConnectionFull(connection, passphrase) {
        const cleanConn = {
            ip_address: connection.ip_address || '',
            port: connection.port || 4028,
            username: connection.username || '',
            password: connection.password || '',
            pool_url: connection.pool_url || '',
            pool_user: connection.pool_user || '',
            pool_password: connection.pool_password || ''
        };
        return encryptObject(cleanConn, passphrase);
    }

    /**
     * Decrypt full miner connection (Plan B)
     * @param {Object} block - Encrypted connection block
     * @param {string} passphrase - Decryption passphrase
     * @returns {Promise<Object>} Full connection object
     */
    async function decryptConnectionFull(block, passphrase) {
        return decryptObject(block, passphrase);
    }

    /**
     * Validate passphrase strength
     * @param {string} passphrase
     * @returns {Object} {valid: boolean, message: string}
     */
    function validatePassphrase(passphrase) {
        if (!passphrase || passphrase.length < 8) {
            return {
                valid: false,
                message: 'Passphrase must be at least 8 characters / 密码短语至少需要8个字符'
            };
        }
        if (passphrase.length > 128) {
            return {
                valid: false,
                message: 'Passphrase must be less than 128 characters / 密码短语不能超过128个字符'
            };
        }
        return { valid: true, message: '' };
    }

    /**
     * Check if Web Crypto API is available
     * @returns {boolean}
     */
    function isSupported() {
        return !!(window.crypto && window.crypto.subtle);
    }

    window.MinerE2EE = {
        encryptObject: encryptObject,
        decryptObject: decryptObject,
        encryptCredentials: encryptCredentials,
        decryptCredentials: decryptCredentials,
        encryptConnectionFull: encryptConnectionFull,
        decryptConnectionFull: decryptConnectionFull,
        validatePassphrase: validatePassphrase,
        isSupported: isSupported,
        ALGO: ALGO,
        VERSION: VERSION
    };

    if (!isSupported()) {
        console.warn('MinerE2EE: Web Crypto API not supported in this browser');
    }
})();
