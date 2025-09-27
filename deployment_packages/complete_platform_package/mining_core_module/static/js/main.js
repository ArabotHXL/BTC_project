// Mining Core Module - Main JavaScript

// Global utility functions
function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined || isNaN(value)) {
        return '0.00';
    }
    
    const formatter = new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
    
    return formatter.format(value);
}

function formatCurrency(value, decimals = 2) {
    return '$' + formatNumber(value, decimals);
}

function formatHashrate(value, unit = 'TH/s') {
    return formatNumber(value, 1) + ' ' + unit;
}

function formatPercentage(value, decimals = 1) {
    return formatNumber(value, decimals) + '%';
}

// API utility functions
function makeRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    return fetch(url, finalOptions)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        });
}

// Network data management
class NetworkDataManager {
    constructor() {
        this.data = null;
        this.lastUpdated = null;
        this.updateInterval = 5 * 60 * 1000; // 5 minutes
    }
    
    async loadData() {
        try {
            const response = await makeRequest('/calculator/api/network-data');
            if (response.success && response.data) {
                this.data = response.data;
                this.lastUpdated = new Date();
                this.updateUI();
                return this.data;
            }
        } catch (error) {
            console.error('Failed to load network data:', error);
            this.setDefaultData();
        }
        return this.data;
    }
    
    setDefaultData() {
        this.data = {
            btc_price: 43000,
            network_difficulty: 83148355189239,
            network_hashrate: 650,
            block_reward: 3.125
        };
        this.updateUI();
    }
    
    updateUI() {
        if (!this.data) return;
        
        // Update BTC price
        const btcPriceElements = document.querySelectorAll('#btc-price, #current-btc-price, .btc-price');
        btcPriceElements.forEach(el => {
            if (el) el.textContent = formatCurrency(this.data.btc_price, 0);
        });
        
        // Update network hashrate
        const hashrateElements = document.querySelectorAll('#network-hashrate, #current-hashrate, .network-hashrate');
        hashrateElements.forEach(el => {
            if (el) el.textContent = formatHashrate(this.data.network_hashrate, 'EH/s');
        });
        
        // Update difficulty
        const difficultyElements = document.querySelectorAll('#network-difficulty, #current-difficulty, .network-difficulty');
        difficultyElements.forEach(el => {
            if (el) {
                const difficultyT = this.data.network_difficulty / 1e12;
                el.textContent = formatNumber(difficultyT, 1) + 'T';
            }
        });
        
        // Update block reward
        const blockRewardElements = document.querySelectorAll('#block-reward, #current-block-reward, .block-reward');
        blockRewardElements.forEach(el => {
            if (el) el.textContent = this.data.block_reward + ' BTC';
        });
    }
    
    async refreshData() {
        try {
            const response = await makeRequest('/calculator/api/refresh-data', {
                method: 'POST'
            });
            if (response.success) {
                await this.loadData();
                return true;
            }
        } catch (error) {
            console.error('Failed to refresh network data:', error);
        }
        return false;
    }
    
    shouldUpdate() {
        if (!this.lastUpdated) return true;
        const now = new Date();
        return (now - this.lastUpdated) > this.updateInterval;
    }
}

// Form validation utilities
function validateForm(formElement) {
    const errors = [];
    
    // Check required fields
    const requiredFields = formElement.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            errors.push(`${field.labels[0]?.textContent || field.name} is required`);
        }
    });
    
    // Check numeric fields
    const numericFields = formElement.querySelectorAll('input[type="number"]');
    numericFields.forEach(field => {
        if (field.value && isNaN(parseFloat(field.value))) {
            errors.push(`${field.labels[0]?.textContent || field.name} must be a valid number`);
        }
    });
    
    return errors;
}

function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.querySelector('.container') || document.body;
    const alertId = 'alert-' + Date.now();
    
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert" id="${alertId}">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('afterbegin', alertHTML);
    
    // Auto dismiss
    if (duration > 0) {
        setTimeout(() => {
            const alertElement = document.getElementById(alertId);
            if (alertElement) {
                const bsAlert = new bootstrap.Alert(alertElement);
                bsAlert.close();
            }
        }, duration);
    }
}

// Loading state management
function showLoading(element, text = 'Loading...') {
    if (!element) return;
    
    element.innerHTML = `
        <div class="d-flex justify-content-center align-items-center">
            <div class="spinner-border spinner-border-sm me-2" role="status"></div>
            <span>${text}</span>
        </div>
    `;
}

function hideLoading(element, originalContent = '') {
    if (!element) return;
    element.innerHTML = originalContent;
}

// Table utilities
function createTable(data, columns, tableId = '') {
    if (!data || data.length === 0) {
        return '<div class="text-center text-muted">No data available</div>';
    }
    
    let html = `<div class="table-responsive">
        <table class="table table-dark table-striped ${tableId ? 'id="' + tableId + '"' : ''}">
            <thead>
                <tr>`;
    
    columns.forEach(col => {
        html += `<th>${col.title}</th>`;
    });
    
    html += '</tr></thead><tbody>';
    
    data.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            let value = row[col.key];
            if (col.formatter) {
                value = col.formatter(value, row);
            }
            html += `<td>${value}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    return html;
}

// Chart utilities (if Chart.js is available)
function createChart(canvasId, type, data, options = {}) {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded');
        return null;
    }
    
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error('Canvas element not found:', canvasId);
        return null;
    }
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: '#ffffff'
                }
            }
        },
        scales: {
            x: {
                ticks: {
                    color: '#ffffff'
                },
                grid: {
                    color: '#333333'
                }
            },
            y: {
                ticks: {
                    color: '#ffffff'
                },
                grid: {
                    color: '#333333'
                }
            }
        }
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    return new Chart(ctx, {
        type: type,
        data: data,
        options: finalOptions
    });
}

// Local storage utilities
function saveToStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
        return false;
    }
}

function loadFromStorage(key, defaultValue = null) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : defaultValue;
    } catch (error) {
        console.error('Failed to load from localStorage:', error);
        return defaultValue;
    }
}

// Global application initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('Mining Core Module - Main JavaScript loaded');
    
    // Initialize network data manager
    window.networkDataManager = new NetworkDataManager();
    
    // Load initial network data
    window.networkDataManager.loadData();
    
    // Set up periodic data refresh
    setInterval(() => {
        if (window.networkDataManager.shouldUpdate()) {
            window.networkDataManager.loadData();
        }
    }, 60000); // Check every minute
    
    // Set up global refresh button handlers
    document.addEventListener('click', function(e) {
        if (e.target.matches('.refresh-data-btn, [data-action="refresh"]')) {
            e.preventDefault();
            
            const button = e.target;
            const icon = button.querySelector('i');
            
            if (icon) icon.classList.add('fa-spin');
            
            window.networkDataManager.refreshData()
                .then(success => {
                    if (success) {
                        showAlert('Data refreshed successfully', 'success', 3000);
                    } else {
                        showAlert('Failed to refresh data', 'warning', 3000);
                    }
                })
                .finally(() => {
                    if (icon) icon.classList.remove('fa-spin');
                });
        }
    });
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Initialize popovers if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
});

// Export global utilities for other scripts
window.MiningCoreUtils = {
    formatNumber,
    formatCurrency,
    formatHashrate,
    formatPercentage,
    makeRequest,
    validateForm,
    showAlert,
    showLoading,
    hideLoading,
    createTable,
    createChart,
    saveToStorage,
    loadFromStorage
};