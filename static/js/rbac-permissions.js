/**
 * RBAC Permission Management - Frontend Integration
 * 
 * This module provides client-side permission checking and UI control
 * based on the user's role and module access levels.
 */

(function(window) {
    'use strict';
    
    // Permission cache
    let userPermissions = null;
    let permissionsLoaded = false;
    let loadingPromise = null;
    
    // Access level constants
    const AccessLevel = {
        FULL: 'full',
        READ: 'read',
        NONE: 'none'
    };
    
    // Module constants (matching backend Module enum)
    const Module = {
        // Basic Functions
        BASIC_CALCULATOR: 'basic:calculator',
        BASIC_SETTINGS: 'basic:settings',
        BASIC_DASHBOARD: 'basic:dashboard',
        
        // Hosting Services
        HOSTING_SITE_MGMT: 'hosting:site_management',
        HOSTING_BATCH_CREATE: 'hosting:batch_create',
        HOSTING_STATUS_MONITOR: 'hosting:status_monitor',
        HOSTING_TICKET: 'hosting:ticket',
        HOSTING_USAGE_TRACKING: 'hosting:usage',
        HOSTING_RECONCILIATION: 'hosting:reconciliation',
        
        // Smart Curtailment
        CURTAILMENT_STRATEGY: 'curtailment:strategy',
        CURTAILMENT_AI_PREDICT: 'curtailment:ai_predict',
        CURTAILMENT_EXECUTE: 'curtailment:execute',
        CURTAILMENT_EMERGENCY: 'curtailment:emergency',
        CURTAILMENT_HISTORY: 'curtailment:history',
        
        // CRM
        CRM_CUSTOMER_MGMT: 'crm:customer_management',
        CRM_CUSTOMER_VIEW: 'crm:customer_view',
        CRM_TRANSACTION: 'crm:transaction',
        CRM_INVOICE: 'crm:invoice',
        CRM_BROKER_COMMISSION: 'crm:broker_commission',
        CRM_ACTIVITY_LOG: 'crm:activity_log',
        
        // Analytics
        ANALYTICS_BATCH_CALC: 'analytics:batch_calculator',
        ANALYTICS_NETWORK: 'analytics:network',
        ANALYTICS_TECHNICAL: 'analytics:technical',
        ANALYTICS_DERIBIT: 'analytics:deribit',
        
        // AI Layer
        AI_BTC_PREDICT: 'ai:btc_predict',
        AI_ROI_EXPLAIN: 'ai:roi_explain',
        AI_ANOMALY_DETECT: 'ai:anomaly_detect',
        AI_POWER_OPTIMIZE: 'ai:power_optimize',
        
        // User Management
        USER_CREATE: 'user:create',
        USER_EDIT: 'user:edit',
        USER_DELETE: 'user:delete',
        USER_ROLE_ASSIGN: 'user:role_assign',
        USER_LIST_VIEW: 'user:list_view',
        
        // System Monitoring
        SYSTEM_HEALTH: 'system:health',
        SYSTEM_PERFORMANCE: 'system:performance',
        SYSTEM_EVENT: 'system:event',
        
        // Web3
        WEB3_BLOCKCHAIN_VERIFY: 'web3:blockchain_verify',
        WEB3_TRANSPARENCY: 'web3:transparency',
        WEB3_SLA_NFT: 'web3:sla_nft',
        
        // Finance
        FINANCE_BILLING: 'finance:billing',
        FINANCE_BTC_SETTLE: 'finance:btc_settlement',
        FINANCE_CRYPTO_PAY: 'finance:crypto_payment',
        
        // Reports
        REPORT_PDF: 'report:pdf',
        REPORT_EXCEL: 'report:excel',
        REPORT_PPT: 'report:ppt'
    };
    
    /**
     * Load user permissions from the server
     * @returns {Promise<Object>} User permissions data
     */
    async function loadPermissions() {
        if (loadingPromise) {
            return loadingPromise;
        }
        
        loadingPromise = fetch('/api/rbac/my-permissions')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load permissions');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    userPermissions = data.data;
                    permissionsLoaded = true;
                    applyPermissions();
                    return userPermissions;
                } else {
                    throw new Error(data.error || 'Failed to load permissions');
                }
            })
            .catch(error => {
                console.error('Permission loading error:', error);
                loadingPromise = null;
                throw error;
            });
        
        return loadingPromise;
    }
    
    /**
     * Get cached permissions or load if not available
     * @returns {Promise<Object>} User permissions
     */
    async function getPermissions() {
        if (permissionsLoaded && userPermissions) {
            return userPermissions;
        }
        return loadPermissions();
    }
    
    /**
     * Check if user has access to a module
     * @param {string} module - Module identifier
     * @param {boolean} requireFull - If true, requires full access (not read-only)
     * @returns {boolean} Whether user has access
     */
    function hasAccess(module, requireFull = false) {
        if (!userPermissions || !userPermissions.permissions) {
            return false;
        }
        
        const modulePermission = userPermissions.permissions[module];
        if (!modulePermission) {
            return false;
        }
        
        if (requireFull) {
            return modulePermission === AccessLevel.FULL;
        }
        
        return modulePermission === AccessLevel.FULL || modulePermission === AccessLevel.READ;
    }
    
    /**
     * Check if user can write (full access) to a module
     * @param {string} module - Module identifier
     * @returns {boolean} Whether user can write
     */
    function canWrite(module) {
        return hasAccess(module, true);
    }
    
    /**
     * Check if user can read a module
     * @param {string} module - Module identifier
     * @returns {boolean} Whether user can read
     */
    function canRead(module) {
        return hasAccess(module, false);
    }
    
    /**
     * Get the user's current role
     * @returns {string|null} User role
     */
    function getRole() {
        return userPermissions ? userPermissions.role : null;
    }
    
    /**
     * Check if user has a specific role
     * @param {string|string[]} roles - Role or array of roles to check
     * @returns {boolean} Whether user has one of the roles
     */
    function hasRole(roles) {
        if (!userPermissions) return false;
        
        const roleList = Array.isArray(roles) ? roles : [roles];
        return roleList.includes(userPermissions.role);
    }
    
    /**
     * Apply permissions to DOM elements with data-permission attributes
     */
    function applyPermissions() {
        if (!permissionsLoaded) return;
        
        // Hide elements based on data-require-module
        document.querySelectorAll('[data-require-module]').forEach(el => {
            const module = el.dataset.requireModule;
            const requireFull = el.dataset.requireFull === 'true';
            
            if (!hasAccess(module, requireFull)) {
                el.style.display = 'none';
                el.classList.add('rbac-hidden');
            } else {
                el.style.display = '';
                el.classList.remove('rbac-hidden');
            }
        });
        
        // Disable buttons/inputs for read-only access
        document.querySelectorAll('[data-require-write]').forEach(el => {
            const module = el.dataset.requireWrite;
            
            if (!canWrite(module)) {
                el.disabled = true;
                el.classList.add('rbac-disabled');
                el.title = el.dataset.readonlyMessage || 'You have read-only access';
            } else {
                el.disabled = false;
                el.classList.remove('rbac-disabled');
            }
        });
        
        // Show/hide based on role
        document.querySelectorAll('[data-require-role]').forEach(el => {
            const requiredRoles = el.dataset.requireRole.split(',').map(r => r.trim());
            
            if (!hasRole(requiredRoles)) {
                el.style.display = 'none';
                el.classList.add('rbac-hidden');
            } else {
                el.style.display = '';
                el.classList.remove('rbac-hidden');
            }
        });
        
        // Update role display elements
        document.querySelectorAll('[data-show-role]').forEach(el => {
            el.textContent = getRole() || 'Guest';
        });
        
        // Dispatch event for custom handlers
        document.dispatchEvent(new CustomEvent('rbac:permissionsApplied', {
            detail: userPermissions
        }));
    }
    
    /**
     * Check a permission via API (for dynamic checks)
     * @param {string} module - Module to check
     * @param {boolean} requireFull - Whether to require full access
     * @returns {Promise<Object>} Permission check result
     */
    async function checkPermission(module, requireFull = false) {
        const response = await fetch('/api/rbac/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                module: module,
                require_full: requireFull
            })
        });
        
        const data = await response.json();
        return data.success ? data.data : null;
    }
    
    /**
     * Create a permission-aware button
     * @param {Object} options - Button configuration
     * @returns {HTMLElement} Configured button element
     */
    function createPermissionButton(options) {
        const {
            text,
            module,
            requireFull = true,
            onClick,
            className = 'btn btn-primary',
            icon = null
        } = options;
        
        const button = document.createElement('button');
        button.className = className;
        button.innerHTML = icon ? `<i class="${icon}"></i> ${text}` : text;
        
        if (!hasAccess(module, requireFull)) {
            button.disabled = true;
            button.className += ' disabled';
            button.title = requireFull ? 'Requires full access' : 'No access to this module';
        } else {
            button.addEventListener('click', onClick);
        }
        
        return button;
    }
    
    /**
     * Show access denied message
     * @param {string} message - Custom message (optional)
     */
    function showAccessDenied(message) {
        const defaultMsg = 'You do not have permission to access this feature.';
        const msg = message || defaultMsg;
        
        // Check if using Bootstrap
        if (window.bootstrap && window.bootstrap.Toast) {
            const toastEl = document.createElement('div');
            toastEl.className = 'toast align-items-center text-white bg-danger border-0';
            toastEl.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi bi-shield-exclamation me-2"></i>${msg}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;
            document.body.appendChild(toastEl);
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
        } else {
            alert(msg);
        }
    }
    
    /**
     * Wrap a function with permission check
     * @param {Function} fn - Function to wrap
     * @param {string} module - Required module
     * @param {boolean} requireFull - Whether to require full access
     * @returns {Function} Wrapped function
     */
    function withPermission(fn, module, requireFull = true) {
        return function(...args) {
            if (!hasAccess(module, requireFull)) {
                showAccessDenied();
                return Promise.reject(new Error('Permission denied'));
            }
            return fn.apply(this, args);
        };
    }
    
    // Initialize on DOM load
    document.addEventListener('DOMContentLoaded', function() {
        // Auto-load permissions if user is logged in
        const isLoggedIn = document.body.dataset.loggedIn === 'true' || 
                          document.querySelector('[data-logged-in="true"]');
        
        if (isLoggedIn) {
            loadPermissions().catch(error => {
                console.warn('Could not load permissions:', error);
            });
        }
    });
    
    // Export to window
    window.RBAC = {
        // Constants
        AccessLevel,
        Module,
        
        // Permission functions
        loadPermissions,
        getPermissions,
        hasAccess,
        canWrite,
        canRead,
        checkPermission,
        
        // Role functions
        getRole,
        hasRole,
        
        // UI helpers
        applyPermissions,
        createPermissionButton,
        showAccessDenied,
        withPermission
    };
    
})(window);
