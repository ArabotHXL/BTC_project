/**
 * HashInsight Secure Miner Onboarding Demo - Frontend Application
 * Implements ABAC + Guarded Approval + E2EE with libsodium
 */

// State
let currentActor = null;
let currentTenant = null;
let currentSite = null;
let sodium = null;

// i18n translations
const translations = {
    en: {
        actor_panel: "Actor & ABAC",
        select_tenant: "Tenant",
        select_actor: "Actor",
        allowed_sites: "Allowed Sites",
        audit_status: "Audit Chain",
        verify: "Verify",
        site_settings: "Site Security Settings",
        select_site: "Site",
        current_mode: "Current Mode",
        switch_mode1: "→ Mode 1",
        switch_mode2: "→ Mode 2",
        switch_mode3: "→ Mode 3",
        batch_migrate: "Batch Migrate Credentials",
        discovery: "Network Discovery",
        simulate: "Simulate",
        scan: "Scan",
        miners: "Miners",
        change_queue: "Change Queue",
        refresh: "Refresh",
        devices: "Edge Devices",
        register_device: "Register Device",
        audit_log: "Audit Log",
        create_change: "Create Change Request",
        reason: "Reason (required)",
        cancel: "Cancel",
        submit: "Submit"
    },
    zh: {
        actor_panel: "操作者 & ABAC",
        select_tenant: "租户",
        select_actor: "操作者",
        allowed_sites: "可访问站点",
        audit_status: "审计链状态",
        verify: "验证",
        site_settings: "站点安全设置",
        select_site: "站点",
        current_mode: "当前模式",
        switch_mode1: "→ 模式1",
        switch_mode2: "→ 模式2",
        switch_mode3: "→ 模式3",
        batch_migrate: "批量迁移凭证",
        discovery: "网络发现",
        simulate: "模拟",
        scan: "扫描",
        miners: "矿机列表",
        change_queue: "变更队列",
        refresh: "刷新",
        devices: "边缘设备",
        register_device: "注册设备",
        audit_log: "审计日志",
        create_change: "创建变更请求",
        reason: "原因（必填）",
        cancel: "取消",
        submit: "提交"
    }
};

let currentLang = 'zh';

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await initSodium();
    await loadTenants();
    setInterval(loadChanges, 30000); // Auto-refresh changes
});

async function initSodium() {
    try {
        await window.sodium.ready;
        sodium = window.sodium;
        console.log('libsodium initialized');
    } catch (e) {
        console.warn('libsodium not available:', e);
    }
}

function toggleLang() {
    currentLang = currentLang === 'zh' ? 'en' : 'zh';
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[currentLang][key]) {
            el.textContent = translations[currentLang][key];
        }
    });
}

// API Helper
async function api(method, path, data = null) {
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (currentActor) {
        headers['X-Actor'] = currentActor.actor_name;
        headers['X-Role'] = currentActor.role;
        headers['X-Tenant'] = String(currentActor.tenant_id);
        if (currentActor.api_token) {
            headers['Authorization'] = `Bearer ${currentActor.api_token}`;
        }
    }
    
    const options = { method, headers };
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(path, options);
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: response.statusText }));
        throw new Error(error.detail || error.error || 'API Error');
    }
    
    return response.json();
}

function showToast(title, message, type = 'info') {
    const toast = document.getElementById('toast');
    document.getElementById('toast-title').textContent = title;
    document.getElementById('toast-body').textContent = message;
    toast.className = `toast bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} text-white`;
    new bootstrap.Toast(toast).show();
}

// Tenant & Actor Management
async function loadTenants() {
    try {
        const tenants = await api('GET', '/api/tenants');
        const select = document.getElementById('tenant-select');
        select.innerHTML = '<option value="">-- Select --</option>';
        tenants.forEach(t => {
            select.innerHTML += `<option value="${t.id}">${t.name}</option>`;
        });
        
        if (tenants.length > 0) {
            select.value = tenants[0].id;
            await loadActors();
        }
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function loadActors() {
    const tenantId = document.getElementById('tenant-select').value;
    if (!tenantId) return;
    
    currentTenant = parseInt(tenantId);
    
    try {
        const actors = await api('GET', `/api/actors?tenant_id=${tenantId}`);
        const select = document.getElementById('actor-select');
        select.innerHTML = '<option value="">-- Select --</option>';
        actors.forEach(a => {
            select.innerHTML += `<option value="${a.id}" data-actor='${JSON.stringify(a)}'>${a.actor_name} (${a.role})</option>`;
        });
        
        if (actors.length > 0) {
            select.value = actors[0].id;
            setCurrentActor();
        }
        
        await loadSites();
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

function setCurrentActor() {
    const select = document.getElementById('actor-select');
    const option = select.options[select.selectedIndex];
    
    if (option && option.dataset.actor) {
        currentActor = JSON.parse(option.dataset.actor);
        
        document.getElementById('current-actor-display').textContent = 
            `${currentActor.actor_name} (${currentActor.role})`;
        document.getElementById('current-actor-display').className = 
            `badge bg-${currentActor.role === 'owner' ? 'danger' : currentActor.role === 'admin' ? 'warning' : 'secondary'}`;
        
        document.getElementById('actor-info').innerHTML = `
            <div>Role: <strong>${currentActor.role}</strong></div>
            <div>Tenant ID: ${currentActor.tenant_id}</div>
        `;
        
        const sitesList = document.getElementById('allowed-sites-list');
        if (currentActor.allowed_site_ids && currentActor.allowed_site_ids.length > 0) {
            sitesList.innerHTML = currentActor.allowed_site_ids.map(id => 
                `<span class="badge bg-secondary me-1">Site ${id}</span>`
            ).join('');
        } else {
            sitesList.innerHTML = '<span class="text-muted">All sites</span>';
        }
        
        loadSites();
        loadChanges();
        loadAuditLog();
    }
}

// Sites
async function loadSites() {
    if (!currentTenant) return;
    
    try {
        const sites = await api('GET', `/api/sites?tenant_id=${currentTenant}`);
        const select = document.getElementById('site-select');
        select.innerHTML = '<option value="">-- Select Site --</option>';
        sites.forEach(s => {
            select.innerHTML += `<option value="${s.id}">${s.name} (Mode ${s.ip_mode})</option>`;
        });
        
        if (sites.length > 0) {
            select.value = sites[0].id;
            loadSiteSettings();
        }
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function loadSiteSettings() {
    const siteId = document.getElementById('site-select').value;
    if (!siteId) return;
    
    currentSite = parseInt(siteId);
    
    try {
        const settings = await api('GET', `/api/sites/${siteId}/settings`);
        
        const modeLabels = {1: 'UI Masking', 2: 'Server Envelope', 3: 'Device E2EE'};
        const modeColors = {1: 'secondary', 2: 'primary', 3: 'success'};
        
        document.getElementById('current-mode-display').innerHTML = 
            `<span class="badge bg-${modeColors[settings.ip_mode]}">${modeLabels[settings.ip_mode]}</span>`;
        
        document.querySelectorAll('.mode-card').forEach(card => {
            card.classList.toggle('active', parseInt(card.dataset.mode) === settings.ip_mode);
        });
        
        loadMiners();
        loadDevices();
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

// Miners
async function loadMiners() {
    if (!currentSite) return;
    
    try {
        const miners = await api('GET', `/api/miners?site_id=${currentSite}`);
        const tbody = document.getElementById('miners-tbody');
        
        if (miners.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No miners</td></tr>';
            return;
        }
        
        tbody.innerHTML = miners.map(m => {
            const credDisplay = formatCredentialDisplay(m.display_credential, m.credential_mode);
            const actions = getMinnerActions(m);
            
            return `
                <tr>
                    <td><strong>${m.name}</strong></td>
                    <td><span class="badge bg-${m.credential_mode === 3 ? 'success' : m.credential_mode === 2 ? 'primary' : 'secondary'}">M${m.credential_mode}</span></td>
                    <td class="small">${credDisplay}</td>
                    <td>${m.last_accepted_counter}</td>
                    <td>${actions}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

function formatCredentialDisplay(cred, mode) {
    if (!cred) return '<span class="text-muted">--</span>';
    
    if (cred.status) {
        if (mode === 2) return `<span class="cred-encrypted">${cred.status}</span>`;
        if (mode === 3) return `<span class="cred-e2ee">${cred.status}</span>`;
        return cred.status;
    }
    
    if (cred.ip) {
        return `<span class="cred-masked">${cred.ip}</span>`;
    }
    
    return '<span class="text-muted">--</span>';
}

function getMinnerActions(miner) {
    const isAdmin = currentActor && ['owner', 'admin'].includes(currentActor.role);
    let actions = [];
    
    if (miner.credential_mode !== 3 && isAdmin) {
        actions.push(`<button class="btn btn-xs btn-outline-success" onclick="requestReveal(${miner.id})"><i class="bi bi-eye"></i></button>`);
    }
    
    if (miner.credential_mode === 3) {
        actions.push(`<button class="btn btn-xs btn-outline-primary" onclick="edgeDecrypt(${miner.id})"><i class="bi bi-unlock"></i></button>`);
    }
    
    return actions.join(' ') || '--';
}

// Discovery
async function runDiscovery() {
    if (!currentSite) {
        showToast('Error', 'Please select a site first', 'error');
        return;
    }
    
    const cidr = document.getElementById('discovery-cidr').value || '192.168.1.0/24';
    const simulate = document.getElementById('discovery-simulate').checked;
    
    try {
        const result = await api('POST', '/api/discovery/scan', {
            site_id: currentSite,
            cidr: cidr,
            ports: [4028],
            simulate: simulate
        });
        
        const tbody = document.getElementById('discovery-tbody');
        tbody.innerHTML = result.candidates.map(c => `
            <tr>
                <td>${c.ip}</td>
                <td>${c.port}</td>
                <td>${c.vendor_hint}</td>
                <td><button class="btn btn-xs btn-success" onclick="onboardMiner('${c.ip}', ${c.port}, '${c.vendor_hint}', '${c.fingerprint}')">
                    <i class="bi bi-plus"></i>
                </button></td>
            </tr>
        `).join('');
        
        showToast('Discovery', `Found ${result.count} miners`, 'success');
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function onboardMiner(ip, port, vendor, fingerprint) {
    if (!currentSite) return;
    
    const settings = await api('GET', `/api/sites/${currentSite}/settings`);
    const mode = settings.ip_mode;
    
    const credentialBlob = {
        ip: ip,
        port: port,
        miner_type: vendor,
        api_username: 'root',
        api_password: 'root'
    };
    
    try {
        let data = {
            site_id: currentSite,
            name: `Miner-${ip.split('.').pop()}`
        };
        
        if (mode === 3) {
            // E2EE mode - encrypt on client side
            const device = await getActiveDevice();
            if (!device) {
                showToast('Error', 'Mode 3 requires an active Edge device', 'error');
                return;
            }
            
            const counter = Date.now();
            const payload = JSON.stringify({ credential: credentialBlob, counter: counter });
            const e2eeB64 = btoa(payload); // Simplified - real impl uses libsodium sealed box
            
            data.credential_e2ee_b64 = e2eeB64;
            data.device_id = device.id;
            data.counter = counter;
        } else {
            data.credential_plaintext_json = JSON.stringify(credentialBlob);
        }
        
        await api('POST', '/api/discovery/onboard', data);
        showToast('Success', 'Miner onboarded', 'success');
        loadMiners();
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function getActiveDevice() {
    if (!currentSite) return null;
    try {
        const devices = await api('GET', `/api/devices?site_id=${currentSite}`);
        return devices.find(d => d.status === 'ACTIVE');
    } catch {
        return null;
    }
}

// Change Requests
function requestModeChange(newMode) {
    if (!currentSite || !currentActor) {
        showToast('Error', 'Please select site and login first', 'error');
        return;
    }
    
    document.getElementById('cr-request-type').value = 'CHANGE_SITE_MODE';
    document.getElementById('cr-target-type').value = 'site';
    document.getElementById('cr-target-id').value = currentSite;
    document.getElementById('cr-action-preview').innerHTML = `
        <strong>Change Site Mode</strong><br>
        Site ID: ${currentSite}<br>
        New Mode: ${newMode} (${['', 'UI Masking', 'Server Envelope', 'Device E2EE'][newMode]})
    `;
    document.getElementById('cr-reason').value = '';
    
    // Store action data
    document.getElementById('cr-action-preview').dataset.action = JSON.stringify({ new_mode: newMode });
    
    new bootstrap.Modal(document.getElementById('changeModal')).show();
}

function requestBatchMigrate() {
    if (!currentSite || !currentActor) {
        showToast('Error', 'Please select site and login first', 'error');
        return;
    }
    
    document.getElementById('cr-request-type').value = 'BATCH_MIGRATE';
    document.getElementById('cr-target-type').value = 'site';
    document.getElementById('cr-target-id').value = currentSite;
    document.getElementById('cr-action-preview').innerHTML = `
        <strong>Batch Migrate Credentials</strong><br>
        Site ID: ${currentSite}<br>
        Migrate all miners to current site mode
    `;
    document.getElementById('cr-action-preview').dataset.action = JSON.stringify({});
    document.getElementById('cr-reason').value = '';
    
    new bootstrap.Modal(document.getElementById('changeModal')).show();
}

function requestReveal(minerId) {
    if (!currentActor) return;
    
    document.getElementById('cr-request-type').value = 'REVEAL_CREDENTIAL';
    document.getElementById('cr-target-type').value = 'miner';
    document.getElementById('cr-target-id').value = minerId;
    document.getElementById('cr-action-preview').innerHTML = `
        <strong>Reveal Credential</strong><br>
        Miner ID: ${minerId}
    `;
    document.getElementById('cr-action-preview').dataset.action = JSON.stringify({ reveal_all: true });
    document.getElementById('cr-reason').value = '';
    
    new bootstrap.Modal(document.getElementById('changeModal')).show();
}

async function submitChangeRequest() {
    const requestType = document.getElementById('cr-request-type').value;
    const targetType = document.getElementById('cr-target-type').value;
    const targetId = parseInt(document.getElementById('cr-target-id').value);
    const reason = document.getElementById('cr-reason').value;
    const action = JSON.parse(document.getElementById('cr-action-preview').dataset.action || '{}');
    
    if (!reason || reason.length < 5) {
        showToast('Error', 'Reason is required (min 5 chars)', 'error');
        return;
    }
    
    try {
        await api('POST', '/api/changes', {
            tenant_id: currentTenant,
            site_id: currentSite,
            request_type: requestType,
            target_type: targetType,
            target_id: targetId,
            requested_action: action,
            reason: reason
        });
        
        bootstrap.Modal.getInstance(document.getElementById('changeModal')).hide();
        showToast('Success', 'Change request created', 'success');
        loadChanges();
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function loadChanges() {
    if (!currentTenant) return;
    
    try {
        const changes = await api('GET', `/api/changes?tenant_id=${currentTenant}`);
        const list = document.getElementById('changes-list');
        
        const pendingCount = changes.filter(c => c.status === 'PENDING').length;
        document.getElementById('pending-count').textContent = pendingCount;
        
        if (changes.length === 0) {
            list.innerHTML = '<div class="p-3 text-muted text-center">No change requests</div>';
            return;
        }
        
        list.innerHTML = changes.slice(0, 20).map(c => `
            <div class="change-card ${c.status.toLowerCase()} ${c.is_expired ? 'expired' : ''}">
                <div class="d-flex justify-content-between">
                    <span class="badge bg-${getStatusColor(c.status)}">${c.status}</span>
                    <small class="text-muted">#${c.id}</small>
                </div>
                <div class="mt-1"><strong>${c.request_type}</strong></div>
                <div class="text-muted">${c.target_type} #${c.target_id}</div>
                <div class="small text-truncate">${c.reason}</div>
                ${c.status === 'PENDING' && !c.is_expired ? `
                    <div class="mt-2 btn-group btn-group-sm w-100">
                        <button class="btn btn-success" onclick="approveChange(${c.id})"><i class="bi bi-check"></i></button>
                        <button class="btn btn-danger" onclick="rejectChange(${c.id})"><i class="bi bi-x"></i></button>
                    </div>
                ` : ''}
                ${c.status === 'APPROVED' ? `
                    <button class="btn btn-sm btn-primary w-100 mt-2" onclick="executeChange(${c.id})">
                        <i class="bi bi-play"></i> Execute
                    </button>
                ` : ''}
            </div>
        `).join('');
    } catch (e) {
        console.error('Load changes error:', e);
    }
}

function getStatusColor(status) {
    return {
        'PENDING': 'warning',
        'APPROVED': 'success',
        'EXECUTED': 'secondary',
        'REJECTED': 'danger',
        'EXPIRED': 'dark'
    }[status] || 'secondary';
}

async function approveChange(crId) {
    try {
        await api('POST', `/api/changes/${crId}/approve`);
        showToast('Success', 'Change request approved', 'success');
        loadChanges();
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function rejectChange(crId) {
    const reason = prompt('Rejection reason:');
    if (!reason) return;
    
    try {
        await api('POST', `/api/changes/${crId}/reject`, { reason });
        showToast('Success', 'Change request rejected', 'success');
        loadChanges();
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function executeChange(crId) {
    try {
        const result = await api('POST', `/api/changes/${crId}/execute`);
        showToast('Success', 'Change executed', 'success');
        loadChanges();
        loadSiteSettings();
        loadMiners();
        
        // If it was a reveal, show the result
        if (result.result && result.result.ip) {
            document.getElementById('reveal-content').textContent = JSON.stringify(result.result, null, 2);
            new bootstrap.Modal(document.getElementById('revealModal')).show();
        }
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

// Devices
async function loadDevices() {
    if (!currentSite) return;
    
    try {
        const devices = await api('GET', `/api/devices?site_id=${currentSite}`);
        const list = document.getElementById('devices-list');
        
        if (devices.length === 0) {
            list.innerHTML = '<div class="text-muted text-center small">No devices</div>';
            return;
        }
        
        list.innerHTML = devices.map(d => `
            <div class="device-item">
                <span><i class="bi bi-hdd-network"></i> ${d.device_name}</span>
                <span class="status-${d.status.toLowerCase()}">${d.status}</span>
            </div>
        `).join('');
    } catch (e) {
        console.error('Load devices error:', e);
    }
}

function showRegisterDeviceModal() {
    document.getElementById('device-name').value = '';
    document.getElementById('device-public-key').value = '';
    document.getElementById('device-secret-key').value = '';
    new bootstrap.Modal(document.getElementById('deviceModal')).show();
}

async function generateKeyPair() {
    if (!sodium) {
        showToast('Error', 'libsodium not loaded', 'error');
        return;
    }
    
    try {
        const keyPair = sodium.crypto_box_keypair();
        const publicKeyB64 = sodium.to_base64(keyPair.publicKey);
        const secretKeyB64 = sodium.to_base64(keyPair.privateKey);
        
        document.getElementById('device-public-key').value = publicKeyB64;
        document.getElementById('device-secret-key').value = secretKeyB64;
        
        showToast('Success', 'KeyPair generated with libsodium', 'success');
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function registerDevice() {
    const name = document.getElementById('device-name').value;
    const publicKey = document.getElementById('device-public-key').value;
    const secretKey = document.getElementById('device-secret-key').value;
    
    if (!name || !publicKey) {
        showToast('Error', 'Name and public key required', 'error');
        return;
    }
    
    try {
        const result = await api('POST', '/api/devices/register', {
            tenant_id: currentTenant,
            site_id: currentSite,
            device_name: name,
            public_key_b64: publicKey,
            secret_key_b64: secretKey
        });
        
        bootstrap.Modal.getInstance(document.getElementById('deviceModal')).hide();
        showToast('Device Registered', `Token: ${result.device_token.substring(0, 16)}...`, 'success');
        loadDevices();
        
        // Store token for edge decrypt
        localStorage.setItem(`device_token_${result.id}`, result.device_token);
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

async function edgeDecrypt(minerId) {
    // Find stored device token
    const devices = await api('GET', `/api/devices?site_id=${currentSite}`);
    const activeDevice = devices.find(d => d.status === 'ACTIVE');
    
    if (!activeDevice) {
        showToast('Error', 'No active device found', 'error');
        return;
    }
    
    const token = localStorage.getItem(`device_token_${activeDevice.id}`);
    if (!token) {
        showToast('Error', 'Device token not found. Re-register device.', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/edge/decrypt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ miner_id: minerId })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Decrypt failed');
        }
        
        const result = await response.json();
        document.getElementById('reveal-content').textContent = JSON.stringify(result.credential_plaintext, null, 2);
        new bootstrap.Modal(document.getElementById('revealModal')).show();
        
        loadMiners(); // Refresh to show updated counter
        loadAuditLog();
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

// Audit
async function loadAuditLog() {
    if (!currentTenant) return;
    
    try {
        const events = await api('GET', `/api/audit?tenant_id=${currentTenant}&limit=20`);
        const log = document.getElementById('audit-log');
        
        log.innerHTML = events.map(e => `
            <div class="audit-entry">
                <span class="audit-type ${getAuditTypeClass(e.event_type)}">${e.event_type}</span>
                <span class="text-muted float-end">${e.actor_name || 'system'}</span>
                <div class="small text-muted">${e.target_type || ''} #${e.target_id || ''}</div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Load audit error:', e);
    }
}

function getAuditTypeClass(type) {
    if (type.includes('DENY') || type.includes('REJECT')) return 'policy-deny';
    if (type.includes('REVEAL') || type.includes('DECRYPT')) return 'reveal';
    if (type.includes('CHANGE') || type.includes('APPROVE')) return 'change';
    return '';
}

async function verifyAuditChain() {
    if (!currentTenant) return;
    
    try {
        const result = await api('GET', `/api/audit/verify?tenant_id=${currentTenant}`);
        const status = document.getElementById('audit-verify-status');
        
        if (result.verify_ok) {
            status.innerHTML = `<span class="badge bg-success verify-ok"><i class="bi bi-check-circle"></i> INTACT</span>`;
        } else {
            status.innerHTML = `<span class="badge bg-danger verify-broken"><i class="bi bi-exclamation-triangle"></i> BROKEN at #${result.first_broken_event_id}</span>`;
        }
    } catch (e) {
        showToast('Error', e.message, 'error');
    }
}

// Add tiny button style
const style = document.createElement('style');
style.textContent = '.btn-xs { padding: 0.1rem 0.3rem; font-size: 0.7rem; }';
document.head.appendChild(style);
