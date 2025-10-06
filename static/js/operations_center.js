/**
 * Operations Center - Unified JavaScript Controller
 * 
 * This script provides shared functionality for all center pages:
 * - Hash navigation (deep linking)
 * - Lazy loading of tabs and accordions
 * - Iframe loading with error handling
 * - Mobile/desktop responsive behavior
 * - Custom content loaders (e.g., miner list)
 * 
 * @version 1.0.0
 * @requires Bootstrap 5.3+
 */

(function() {
    'use strict';
    
    /**
     * Initialize all operations centers on the page
     */
    function initializeOperationsCenters() {
        const configs = window.operationsCenterConfig || {};
        
        Object.keys(configs).forEach(centerId => {
            const config = configs[centerId];
            new OperationsCenter(config);
        });
    }
    
    /**
     * Operations Center Class
     */
    class OperationsCenter {
        constructor(config) {
            this.config = config;
            this.centerId = config.id;
            this.currentLang = config.currentLang;
            this.userRole = config.userRole;
            this.isMobile = window.innerWidth < 992;
            this.loadedTabs = new Set();
            this.loadedAccordions = new Set();
            this.customLoaders = {};
            
            console.log(`Initializing Operations Center: ${this.centerId}`);
            console.log('Mobile mode:', this.isMobile);
            
            this.init();
        }
        
        /**
         * Initialize the operations center
         */
        init() {
            this.registerCustomLoaders();
            this.setupEventListeners();
            this.handleInitialLoad();
            
            console.log(`Operations Center initialized: ${this.centerId}`);
        }
        
        /**
         * Register custom content loaders (e.g., miner list)
         */
        registerCustomLoaders() {
            // Mining Operations: Miner List Loader
            this.customLoaders['loadMiners'] = async (containerId) => {
                console.log('Loading miners list...');
                const container = document.getElementById(containerId);
                if (!container) return;
                
                try {
                    const response = await fetch('/admin/miners/api/list?active_only=true');
                    const data = await response.json();
                    
                    if (data.success) {
                        container.innerHTML = this.renderMinersList(data.miners);
                        this.attachMinerSelectionListeners();
                    } else {
                        throw new Error(data.error || 'Failed to load miners');
                    }
                } catch (error) {
                    console.error('Error loading miners:', error);
                    this.showError(container, error.message);
                }
            };
            
            // Add more custom loaders as needed
        }
        
        /**
         * Setup all event listeners
         */
        setupEventListeners() {
            // Hash navigation
            window.addEventListener('hashchange', () => this.handleHashNavigation());
            
            // Desktop tabs
            const tabTriggers = document.querySelectorAll(`#${this.centerId}-tabs button[data-bs-toggle="tab"]`);
            tabTriggers.forEach(trigger => {
                trigger.addEventListener('show.bs.tab', (event) => {
                    const targetId = event.target.getAttribute('data-bs-target').substring(1);
                    this.loadDesktopTab(targetId, trigger);
                });
                
                trigger.addEventListener('shown.bs.tab', (event) => {
                    const targetId = event.target.getAttribute('data-bs-target').substring(1);
                    this.updateHash(targetId);
                });
            });
            
            // Mobile accordions
            const accordionItems = document.querySelectorAll(`#${this.centerId}-accordion .accordion-collapse`);
            accordionItems.forEach(item => {
                item.addEventListener('show.bs.collapse', (event) => {
                    const targetId = event.target.id.replace('collapse-', '');
                    this.loadMobileAccordion(targetId, event.target);
                });
            });
            
            const accordionButtons = document.querySelectorAll(`#${this.centerId}-accordion .accordion-button`);
            accordionButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    const targetId = btn.getAttribute('data-bs-target').replace('#collapse-', '');
                    this.updateHash(targetId);
                });
            });
            
            // Retry button event delegation
            document.addEventListener('click', (e) => {
                const retryBtn = e.target.closest('.retry-btn');
                if (retryBtn && retryBtn.dataset.centerId === this.centerId) {
                    const tabId = retryBtn.dataset.tabId;
                    this.retryLoad(tabId);
                }
            });
        }
        
        /**
         * Handle initial page load
         */
        handleInitialLoad() {
            if (window.location.hash) {
                this.handleHashNavigation();
            } else {
                // Load first tab explicitly
                setTimeout(() => {
                    const firstTab = this.config.tabs[0];
                    if (firstTab) {
                        if (!this.isMobile) {
                            this.loadDesktopTab(firstTab.id);
                        } else {
                            const firstCollapse = document.getElementById(`collapse-${firstTab.id}`);
                            if (firstCollapse && firstCollapse.classList.contains('show')) {
                                this.loadMobileAccordion(firstTab.id, firstCollapse);
                            }
                        }
                    }
                }, 100);
            }
        }
        
        /**
         * Handle hash navigation
         */
        handleHashNavigation() {
            const hash = window.location.hash.substring(1);
            console.log('Hash navigation:', hash);
            
            if (!hash) return;
            
            if (this.isMobile) {
                const collapseElement = document.getElementById(`collapse-${hash}`);
                if (collapseElement) {
                    new bootstrap.Collapse(collapseElement, { show: true });
                }
            } else {
                const tabButton = document.querySelector(`button[data-bs-target="#${hash}"]`);
                if (tabButton) {
                    new bootstrap.Tab(tabButton).show();
                }
            }
        }
        
        /**
         * Update browser hash
         */
        updateHash(tabId) {
            if (window.location.hash !== '#' + tabId) {
                history.replaceState(null, null, '#' + tabId);
                console.log('Hash updated to:', tabId);
            }
        }
        
        /**
         * Load desktop tab content
         */
        loadDesktopTab(tabId, trigger = null) {
            if (this.loadedTabs.has(tabId)) {
                console.log('Tab already loaded:', tabId);
                return;
            }
            
            console.log('Loading desktop tab:', tabId);
            
            const tabConfig = this.config.tabs.find(t => t.id === tabId);
            if (!tabConfig) {
                console.error('Tab config not found:', tabId);
                return;
            }
            
            const loader = document.getElementById(`${tabId}-loader`);
            
            // Check for custom loader
            if (tabConfig.custom_load) {
                const customLoader = this.customLoaders[tabConfig.custom_load];
                if (customLoader) {
                    loader.style.display = 'none';
                    customLoader(`${tabId}-content`);
                    this.loadedTabs.add(tabId);
                    return;
                }
            }
            
            // Standard iframe loading
            const frame = document.getElementById(`${tabId}-frame`);
            if (!frame) {
                console.error('Frame not found:', tabId);
                return;
            }
            
            const url = frame.dataset.url || tabConfig.url;
            frame.src = url;
            
            frame.onload = () => {
                console.log('Iframe loaded successfully:', tabId);
                loader.style.display = 'none';
                frame.style.display = 'block';
                this.loadedTabs.add(tabId);
            };
            
            frame.onerror = () => {
                console.error('Iframe load error:', tabId);
                this.showIframeError(loader, url, tabId);
            };
            
            // Timeout fallback
            setTimeout(() => {
                if (!this.loadedTabs.has(tabId) && frame.src) {
                    console.warn('Iframe load timeout:', tabId);
                    loader.style.display = 'none';
                    frame.style.display = 'block';
                    this.loadedTabs.add(tabId);
                }
            }, 10000);
        }
        
        /**
         * Load mobile accordion content
         */
        loadMobileAccordion(accordionId, collapseElement) {
            if (this.loadedAccordions.has(accordionId)) {
                console.log('Accordion already loaded:', accordionId);
                return;
            }
            
            console.log('Loading mobile accordion:', accordionId);
            
            const accordionBody = collapseElement.querySelector('.operations-center__accordion-body');
            if (!accordionBody) {
                console.error('Accordion body not found:', accordionId);
                return;
            }
            
            const tabConfig = this.config.tabs.find(t => t.id === accordionId);
            if (!tabConfig) {
                console.error('Tab config not found:', accordionId);
                return;
            }
            
            // Check for custom loader
            if (tabConfig.custom_load) {
                const customLoader = this.customLoaders[tabConfig.custom_load];
                if (customLoader) {
                    const loader = accordionBody.querySelector('.operations-center__loader');
                    if (loader) loader.style.display = 'none';
                    customLoader(accordionBody.id);
                    this.loadedAccordions.add(accordionId);
                    return;
                }
            }
            
            // Standard iframe loading
            const iframeUrl = accordionBody.dataset.iframeUrl || tabConfig.url;
            if (!iframeUrl) {
                console.warn('No iframe URL for accordion:', accordionId);
                return;
            }
            
            const iframe = document.createElement('iframe');
            iframe.className = 'operations-center__iframe';
            iframe.src = iframeUrl;
            iframe.setAttribute('loading', 'lazy');
            
            const loader = accordionBody.querySelector('.operations-center__loader');
            
            iframe.onload = () => {
                console.log('Mobile iframe loaded:', accordionId);
                if (loader) loader.style.display = 'none';
                this.loadedAccordions.add(accordionId);
            };
            
            iframe.onerror = () => {
                console.error('Mobile iframe error:', accordionId);
                this.showIframeError(accordionBody, iframeUrl, accordionId);
            };
            
            accordionBody.appendChild(iframe);
            
            // Timeout fallback
            setTimeout(() => {
                if (!this.loadedAccordions.has(accordionId)) {
                    if (loader) loader.style.display = 'none';
                    this.loadedAccordions.add(accordionId);
                }
            }, 10000);
        }
        
        /**
         * Show iframe error with retry button
         */
        showIframeError(container, url, tabId) {
            const errorMsg = i18n.t('operations.failedToLoad');
            const retryText = i18n.t('operations.retry');
            
            container.innerHTML = `
                <div class="operations-center__error">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem;"></i>
                    <p class="mt-3">${errorMsg}: ${url}</p>
                    <button class="btn btn-warning retry-btn" 
                            data-tab-id="${tabId}" 
                            data-center-id="${this.centerId}">
                        <i class="bi bi-arrow-clockwise"></i> ${retryText}
                    </button>
                </div>
            `;
        }
        
        /**
         * Show general error
         */
        showError(container, message) {
            const errorMsg = i18n.t('operations.error');
            container.innerHTML = `
                <div class="operations-center__error">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem;"></i>
                    <p class="mt-3">${errorMsg}: ${message}</p>
                </div>
            `;
        }
        
        /**
         * Retry loading a tab
         */
        retryLoad(tabId) {
            console.log('Retry button clicked for tab:', tabId);
            
            if (this.isMobile) {
                const collapseElement = document.getElementById(`collapse-${tabId}`);
                if (collapseElement) {
                    this.loadedAccordions.delete(tabId);
                    this.loadMobileAccordion(tabId, collapseElement);
                }
            } else {
                this.loadedTabs.delete(tabId);
                this.loadDesktopTab(tabId);
            }
        }
        
        /**
         * Render miners list (Mining Operations specific)
         */
        renderMinersList(miners) {
            const selectedCount = i18n.t('operations.minerSelected');
            const sendToBatchText = i18n.t('operations.sendToBatch');
            const modelText = i18n.t('operations.model');
            const hashrateText = i18n.t('operations.hashrate');
            const powerText = i18n.t('operations.power');
            const statusText = i18n.t('operations.status');
            const selectText = i18n.t('operations.select');
            
            let html = `
                <div class="miner-selection-toolbar">
                    <div>
                        <span class="text-warning">${selectedCount}: </span>
                        <strong id="selected-count">0</strong>
                    </div>
                    <button class="btn btn-warning" id="send-to-batch" disabled>
                        <i class="bi bi-send"></i> ${sendToBatchText}
                    </button>
                </div>
                <div class="table-responsive">
                    <table class="table table-dark table-hover">
                        <thead>
                            <tr>
                                <th>${selectText}</th>
                                <th>${modelText}</th>
                                <th>${hashrateText}</th>
                                <th>${powerText}</th>
                                <th>${statusText}</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            miners.forEach(miner => {
                html += `
                    <tr class="miner-row" data-miner-id="${miner.id}">
                        <td>
                            <input type="checkbox" class="miner-checkbox" value="${miner.id}">
                        </td>
                        <td>${miner.model}</td>
                        <td>${miner.hashrate} TH/s</td>
                        <td>${miner.power} W</td>
                        <td><span class="badge bg-success">${miner.status}</span></td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
            
            return html;
        }
        
        /**
         * Attach miner selection event listeners
         */
        attachMinerSelectionListeners() {
            const checkboxes = document.querySelectorAll('.miner-checkbox');
            const selectedCountElem = document.getElementById('selected-count');
            const sendBtn = document.getElementById('send-to-batch');
            let selectedMiners = [];
            
            checkboxes.forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const minerId = parseInt(e.target.value);
                    const row = e.target.closest('.miner-row');
                    
                    if (e.target.checked) {
                        selectedMiners.push(minerId);
                        row.classList.add('selected-row');
                    } else {
                        selectedMiners = selectedMiners.filter(id => id !== minerId);
                        row.classList.remove('selected-row');
                    }
                    
                    selectedCountElem.textContent = selectedMiners.length;
                    sendBtn.disabled = selectedMiners.length === 0;
                    
                    // Save to sessionStorage
                    sessionStorage.setItem('selectedMiners', JSON.stringify(selectedMiners));
                });
            });
            
            if (sendBtn) {
                sendBtn.addEventListener('click', () => {
                    // Navigate to batch calculator with selected miners
                    window.location.href = '/batch-calculator#miners=' + selectedMiners.join(',');
                });
            }
            
            // Restore previous selection
            const savedSelection = sessionStorage.getItem('selectedMiners');
            if (savedSelection) {
                selectedMiners = JSON.parse(savedSelection);
                selectedMiners.forEach(minerId => {
                    const checkbox = document.querySelector(`.miner-checkbox[value="${minerId}"]`);
                    if (checkbox) {
                        checkbox.checked = true;
                        checkbox.closest('.miner-row').classList.add('selected-row');
                    }
                });
                selectedCountElem.textContent = selectedMiners.length;
                sendBtn.disabled = selectedMiners.length === 0;
            }
        }
        
        /**
         * Public API for debugging
         */
        reload(tabId) {
            if (this.isMobile) {
                this.loadedAccordions.delete(tabId);
                const collapseElement = document.getElementById(`collapse-${tabId}`);
                if (collapseElement) {
                    this.loadMobileAccordion(tabId, collapseElement);
                }
            } else {
                this.loadedTabs.delete(tabId);
                this.loadDesktopTab(tabId);
            }
        }
    }
    
    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeOperationsCenters);
    } else {
        initializeOperationsCenters();
    }
    
    // Expose for debugging
    window.OperationsCenter = OperationsCenter;
    window.initializeOperationsCenters = initializeOperationsCenters;
    
})();
