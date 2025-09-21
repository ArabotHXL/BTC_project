/**
 * Web3 Dashboard 工具库
 * Web3 Dashboard Utilities
 * 
 * 提供钱包连接、区块链交互和Web3工具功能
 * Provides wallet connection, blockchain interaction and Web3 tools functionality
 */

// 全局变量
let web3Instance = null;
let currentAccount = null;
let networkData = null;

// 支持的网络配置
const SUPPORTED_NETWORKS = {
    // Base Mainnet
    '0x2105': {
        chainId: '0x2105',
        chainName: 'Base Mainnet',
        nativeCurrency: {
            name: 'Ethereum',
            symbol: 'ETH',
            decimals: 18
        },
        rpcUrls: ['https://mainnet.base.org'],
        blockExplorerUrls: ['https://basescan.org']
    },
    // Base Sepolia Testnet
    '0x14a34': {
        chainId: '0x14a34',
        chainName: 'Base Sepolia',
        nativeCurrency: {
            name: 'Ethereum',
            symbol: 'ETH',
            decimals: 18
        },
        rpcUrls: ['https://sepolia.base.org'],
        blockExplorerUrls: ['https://sepolia-explorer.base.org']
    }
};

/**
 * 检查MetaMask是否已安装
 * Check if MetaMask is installed
 */
function isMetaMaskInstalled() {
    return typeof window.ethereum !== 'undefined' && window.ethereum.isMetaMask;
}

/**
 * 获取当前网络信息
 * Get current network information
 */
async function getCurrentNetwork() {
    if (!window.ethereum) return null;
    
    try {
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        return SUPPORTED_NETWORKS[chainId] || {
            chainId: chainId,
            chainName: 'Unknown Network',
            unsupported: true
        };
    } catch (error) {
        console.error('Failed to get current network:', error);
        return null;
    }
}

/**
 * 切换到指定网络
 * Switch to specified network
 */
async function switchToNetwork(chainId) {
    if (!window.ethereum) {
        throw new Error('MetaMask not installed');
    }
    
    try {
        await window.ethereum.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: chainId }],
        });
        return true;
    } catch (switchError) {
        // 如果网络不存在，尝试添加
        if (switchError.code === 4902) {
            try {
                await window.ethereum.request({
                    method: 'wallet_addEthereumChain',
                    params: [SUPPORTED_NETWORKS[chainId]],
                });
                return true;
            } catch (addError) {
                console.error('Failed to add network:', addError);
                throw addError;
            }
        }
        throw switchError;
    }
}

/**
 * 连接MetaMask钱包
 * Connect MetaMask wallet
 */
async function connectMetaMask() {
    if (!isMetaMaskInstalled()) {
        throw new Error('MetaMask is not installed. Please install MetaMask to continue.');
    }
    
    try {
        // 请求账户访问权限
        const accounts = await window.ethereum.request({ 
            method: 'eth_requestAccounts' 
        });
        
        if (accounts.length === 0) {
            throw new Error('No accounts found. Please unlock MetaMask.');
        }
        
        currentAccount = accounts[0];
        
        // 获取网络信息
        networkData = await getCurrentNetwork();
        
        // 初始化Web3实例
        if (typeof Web3 !== 'undefined') {
            web3Instance = new Web3(window.ethereum);
        }
        
        console.log('MetaMask connected:', {
            account: currentAccount,
            network: networkData
        });
        
        return {
            account: currentAccount,
            network: networkData
        };
        
    } catch (error) {
        console.error('MetaMask connection failed:', error);
        throw error;
    }
}

/**
 * 断开钱包连接
 * Disconnect wallet
 */
function disconnectWallet() {
    currentAccount = null;
    networkData = null;
    web3Instance = null;
    
    // 清除相关的UI状态
    updateWalletUI(false);
    
    console.log('Wallet disconnected');
}

/**
 * 获取账户余额
 * Get account balance
 */
async function getAccountBalance(address = null) {
    if (!web3Instance) {
        throw new Error('Web3 not initialized');
    }
    
    const account = address || currentAccount;
    if (!account) {
        throw new Error('No account specified');
    }
    
    try {
        const balance = await web3Instance.eth.getBalance(account);
        return {
            wei: balance,
            eth: web3Instance.utils.fromWei(balance, 'ether'),
            formatted: parseFloat(web3Instance.utils.fromWei(balance, 'ether')).toFixed(4)
        };
    } catch (error) {
        console.error('Failed to get balance:', error);
        throw error;
    }
}

/**
 * 获取交易历史 - 使用真实API
 * Get transaction history - Using real APIs
 */
async function getTransactionHistory(address = null, limit = 10) {
    const account = address || currentAccount;
    if (!account) {
        throw new Error('No account specified');
    }
    
    try {
        // 使用区块链浏览器API获取真实交易历史
        const network = await getCurrentNetwork();
        let apiUrl = '';
        
        if (network && network.chainId === '0x2105') {
            // Base Mainnet
            apiUrl = 'https://api.basescan.org/api';
        } else if (network && network.chainId === '0x14a34') {
            // Base Sepolia  
            apiUrl = 'https://api-sepolia.basescan.org/api';
        }
        
        if (apiUrl) {
            try {
                const response = await fetch(`${apiUrl}?module=account&action=txlist&address=${account}&startblock=0&endblock=99999999&page=1&offset=${limit}&sort=desc`);
                const data = await response.json();
                
                if (data.status === '1' && data.result) {
                    const transactions = data.result.map(tx => ({
                        hash: tx.hash,
                        from: tx.from,
                        to: tx.to,
                        value: (parseInt(tx.value) / 1e18).toFixed(6),
                        timestamp: parseInt(tx.timeStamp) * 1000,
                        status: tx.txreceipt_status === '1' ? 'success' : 'failed',
                        blockNumber: tx.blockNumber,
                        gasUsed: tx.gasUsed,
                        gasPrice: tx.gasPrice
                    }));
                    
                    return {
                        account: account,
                        transactions: transactions,
                        total: transactions.length
                    };
                }
            } catch (apiError) {
                console.warn('External API failed, falling back to Web3:', apiError);
            }
        }
        
        // 如果外部API不可用，使用Web3获取基本信息
        if (!web3Instance) {
            return {
                account: account,
                transactions: [],
                total: 0,
                error: 'No API available and Web3 not initialized'
            };
        }
        
        console.log('Using Web3 to get transaction history');
        const latestBlock = await web3Instance.eth.getBlockNumber();
        const transactions = [];
        
        // 检查最近的20个区块
        for (let i = 0; i < Math.min(20, latestBlock) && transactions.length < limit; i++) {
            try {
                const block = await web3Instance.eth.getBlock(latestBlock - i, true);
                if (block && block.transactions) {
                    for (const tx of block.transactions) {
                        if ((tx.from && tx.from.toLowerCase() === account.toLowerCase()) ||
                            (tx.to && tx.to.toLowerCase() === account.toLowerCase())) {
                            transactions.push({
                                hash: tx.hash,
                                from: tx.from,
                                to: tx.to,
                                value: web3Instance.utils.fromWei(tx.value || '0', 'ether'),
                                timestamp: Number(block.timestamp) * 1000,
                                status: 'success',
                                blockNumber: block.number,
                                gasUsed: tx.gas,
                                gasPrice: tx.gasPrice
                            });
                            
                            if (transactions.length >= limit) break;
                        }
                    }
                }
            } catch (blockError) {
                console.warn(`Failed to get block ${latestBlock - i}:`, blockError);
                continue;
            }
        }
        
        return {
            account: account,
            transactions: transactions,
            total: transactions.length
        };
        
    } catch (error) {
        console.error('Failed to get transaction history:', error);
        return {
            account: account,
            transactions: [],
            total: 0,
            error: error.message
        };
    }
}

/**
 * 发送交易
 * Send transaction
 */
async function sendTransaction(to, value, data = '0x') {
    if (!web3Instance || !currentAccount) {
        throw new Error('Wallet not connected');
    }
    
    try {
        const valueInWei = web3Instance.utils.toWei(value.toString(), 'ether');
        
        const txParams = {
            from: currentAccount,
            to: to,
            value: valueInWei,
            data: data
        };
        
        // 估算gas费用
        const gasEstimate = await web3Instance.eth.estimateGas(txParams);
        txParams.gas = gasEstimate;
        
        // 发送交易
        const txHash = await window.ethereum.request({
            method: 'eth_sendTransaction',
            params: [txParams],
        });
        
        console.log('Transaction sent:', txHash);
        return txHash;
        
    } catch (error) {
        console.error('Transaction failed:', error);
        throw error;
    }
}

/**
 * 签名消息
 * Sign message
 */
async function signMessage(message) {
    if (!currentAccount) {
        throw new Error('Wallet not connected');
    }
    
    try {
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [message, currentAccount]
        });
        
        console.log('Message signed:', signature);
        return signature;
        
    } catch (error) {
        console.error('Message signing failed:', error);
        throw error;
    }
}

/**
 * 验证签名
 * Verify signature
 */
async function verifySignature(message, signature, address) {
    if (!web3Instance) {
        throw new Error('Web3 not initialized');
    }
    
    try {
        const recoveredAddress = web3Instance.eth.accounts.recover(message, signature);
        return recoveredAddress.toLowerCase() === address.toLowerCase();
    } catch (error) {
        console.error('Signature verification failed:', error);
        return false;
    }
}

/**
 * 格式化地址显示
 * Format address for display
 */
function formatAddress(address, startChars = 6, endChars = 4) {
    if (!address) return '';
    
    if (address.length <= startChars + endChars) {
        return address;
    }
    
    return `${address.slice(0, startChars)}...${address.slice(-endChars)}`;
}

/**
 * 格式化余额显示
 * Format balance for display
 */
function formatBalance(balance, decimals = 4) {
    if (!balance) return '0';
    
    const num = parseFloat(balance);
    if (num === 0) return '0';
    
    if (num < 0.0001) {
        return '< 0.0001';
    }
    
    return num.toFixed(decimals);
}

/**
 * 更新钱包UI状态
 * Update wallet UI state
 */
function updateWalletUI(connected, data = null) {
    // 更新连接状态指示器
    const indicators = document.querySelectorAll('.wallet-indicator');
    indicators.forEach(indicator => {
        indicator.className = `wallet-indicator ${connected ? 'connected' : 'disconnected'}`;
    });
    
    // 更新钱包地址显示
    const addressElements = document.querySelectorAll('.wallet-address');
    addressElements.forEach(element => {
        if (connected && data && data.account) {
            element.textContent = formatAddress(data.account);
            element.style.display = 'block';
        } else {
            element.style.display = 'none';
        }
    });
    
    // 更新连接按钮文本
    const connectButtons = document.querySelectorAll('[onclick*="connectWallet"]');
    connectButtons.forEach(button => {
        if (connected) {
            button.textContent = button.textContent.includes('Connect') ? 'Connected' : '已连接';
            button.disabled = true;
        } else {
            button.textContent = button.textContent.includes('Connected') ? 'Connect Wallet' : '连接钱包';
            button.disabled = false;
        }
    });
    
    // 更新网络信息
    if (connected && data && data.network) {
        const networkElements = document.querySelectorAll('.network-name');
        networkElements.forEach(element => {
            element.textContent = data.network.chainName;
        });
    }
}

/**
 * 监听账户变化
 * Listen for account changes
 */
function setupAccountListener() {
    if (window.ethereum) {
        window.ethereum.on('accountsChanged', (accounts) => {
            if (accounts.length === 0) {
                // 用户断开了连接
                disconnectWallet();
            } else if (accounts[0] !== currentAccount) {
                // 用户切换了账户
                currentAccount = accounts[0];
                updateWalletUI(true, { account: currentAccount, network: networkData });
                console.log('Account changed to:', currentAccount);
            }
        });
        
        window.ethereum.on('chainChanged', (chainId) => {
            // 网络切换，重新加载页面
            console.log('Network changed to:', chainId);
            window.location.reload();
        });
        
        window.ethereum.on('disconnect', () => {
            console.log('MetaMask disconnected');
            disconnectWallet();
        });
    }
}

/**
 * 检查钱包连接状态
 * Check wallet connection status
 */
async function checkWalletConnection() {
    if (!isMetaMaskInstalled()) {
        return { connected: false, reason: 'MetaMask not installed' };
    }
    
    try {
        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
        
        if (accounts.length > 0) {
            currentAccount = accounts[0];
            networkData = await getCurrentNetwork();
            
            if (typeof Web3 !== 'undefined') {
                web3Instance = new Web3(window.ethereum);
            }
            
            return {
                connected: true,
                account: currentAccount,
                network: networkData
            };
        } else {
            return { connected: false, reason: 'No accounts available' };
        }
    } catch (error) {
        console.error('Failed to check wallet connection:', error);
        return { connected: false, reason: error.message };
    }
}

/**
 * 初始化Web3钱包功能
 * Initialize Web3 wallet functionality
 */
async function initializeWeb3() {
    console.log('Initializing Web3 wallet functionality...');
    
    // 检查现有连接
    const connectionStatus = await checkWalletConnection();
    
    if (connectionStatus.connected) {
        updateWalletUI(true, connectionStatus);
        console.log('Wallet already connected:', connectionStatus);
    }
    
    // 设置事件监听器
    setupAccountListener();
    
    console.log('Web3 initialization complete');
}

// 导出主要函数供全局使用
window.Web3Utils = {
    isMetaMaskInstalled,
    connectMetaMask,
    disconnectWallet,
    getCurrentNetwork,
    switchToNetwork,
    getAccountBalance,
    getTransactionHistory,
    sendTransaction,
    signMessage,
    verifySignature,
    formatAddress,
    formatBalance,
    updateWalletUI,
    checkWalletConnection,
    initializeWeb3,
    
    // 获取当前状态
    getCurrentAccount: () => currentAccount,
    getCurrentNetwork: () => networkData,
    getWeb3Instance: () => web3Instance
};

// ============================================================================
// 增强功能：多链资产管理、ERC-20代币支持、NFT管理
// Enhanced Features: Multi-chain Asset Management, ERC-20 Token Support, NFT Management
// ============================================================================

// 代币合约地址配置
const TOKEN_CONTRACTS = {
    // Base Mainnet
    '0x2105': {
        USDC: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        WETH: '0x4200000000000000000000000000000000000006'
    },
    // Base Sepolia
    '0x14a34': {
        USDC: '0x036CbD53842c5426634e7929541eC2318f3dCF7e',
        WETH: '0x4200000000000000000000000000000000000006'
    }
};

// ERC-20 代币ABI
const ERC20_ABI = [
    {
        "constant": true,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    }
];

// 缓存和状态管理
let priceCache = {};
let balanceCache = {};
let nftCache = {};
let updateInterval = null;

// RPC调用批处理和防抖
let rpcQueue = [];
let rpcBatchTimer = null;
const RPC_BATCH_DELAY = 100; // 100ms 批处理延迟
const RPC_CACHE_TTL = 30000; // 30秒缓存TTL

/**
 * RPC调用防抖和批处理
 * Debounced and batched RPC calls
 */
async function batchedRPCCall(method, params = [], useCache = true) {
    const cacheKey = `${method}_${JSON.stringify(params)}`;
    
    // 检查缓存
    if (useCache && priceCache[cacheKey] && (Date.now() - priceCache[cacheKey].timestamp) < RPC_CACHE_TTL) {
        return priceCache[cacheKey].data;
    }
    
    return new Promise((resolve, reject) => {
        rpcQueue.push({
            method,
            params,
            cacheKey,
            useCache,
            resolve,
            reject
        });
        
        // 防抖处理
        if (rpcBatchTimer) {
            clearTimeout(rpcBatchTimer);
        }
        
        rpcBatchTimer = setTimeout(processBatchedRPCCalls, RPC_BATCH_DELAY);
    });
}

/**
 * 处理批量RPC调用
 * Process batched RPC calls
 */
async function processBatchedRPCCalls() {
    if (rpcQueue.length === 0) return;
    
    const batch = rpcQueue.splice(0); // 取出所有队列中的调用
    
    for (const call of batch) {
        try {
            let result;
            
            // 根据方法类型执行不同的调用
            if (call.method === 'eth_getBalance' && web3Instance) {
                result = await web3Instance.eth.getBalance(call.params[0]);
            } else if (call.method === 'eth_blockNumber' && web3Instance) {
                result = await web3Instance.eth.getBlockNumber();
            } else if (call.method === 'eth_gasPrice' && web3Instance) {
                result = await web3Instance.eth.getGasPrice();
            } else if (call.method === 'eth_getTransactionCount' && web3Instance) {
                result = await web3Instance.eth.getTransactionCount(call.params[0]);
            } else {
                // 通用Web3调用
                if (!web3Instance) {
                    throw new Error('Web3 not initialized');
                }
                result = await web3Instance.eth[call.method](...call.params);
            }
            
            // 缓存结果
            if (call.useCache) {
                priceCache[call.cacheKey] = {
                    data: result,
                    timestamp: Date.now()
                };
            }
            
            call.resolve(result);
            
        } catch (error) {
            console.error(`RPC call ${call.method} failed:`, error);
            call.reject(error);
        }
    }
}

/**
 * 获取ERC-20代币余额
 * Get ERC-20 token balance
 */
async function getTokenBalance(tokenAddress, accountAddress = null) {
    if (!web3Instance) {
        throw new Error('Web3 not initialized');
    }
    
    const account = accountAddress || currentAccount;
    if (!account) {
        throw new Error('No account specified');
    }
    
    try {
        const contract = new web3Instance.eth.Contract(ERC20_ABI, tokenAddress);
        
        const [balance, decimals, symbol, name] = await Promise.all([
            contract.methods.balanceOf(account).call(),
            contract.methods.decimals().call(),
            contract.methods.symbol().call(),
            contract.methods.name().call()
        ]);
        
        const balanceFormatted = balance / Math.pow(10, decimals);
        
        return {
            balance: balance,
            balanceFormatted: balanceFormatted,
            decimals: decimals,
            symbol: symbol,
            name: name,
            contractAddress: tokenAddress
        };
    } catch (error) {
        console.error('Failed to get token balance:', error);
        throw error;
    }
}

/**
 * 获取多种资产余额
 * Get multiple asset balances
 */
async function getMultiAssetBalances(accountAddress = null) {
    const account = accountAddress || currentAccount;
    if (!account) {
        throw new Error('No account specified');
    }
    
    if (!networkData || !networkData.chainId) {
        throw new Error('Network not detected');
    }
    
    try {
        const balances = {};
        
        // 获取ETH余额
        const ethBalance = await getAccountBalance(account);
        balances.ETH = {
            balance: ethBalance.wei,
            balanceFormatted: parseFloat(ethBalance.eth),
            symbol: 'ETH',
            name: 'Ethereum',
            decimals: 18
        };
        
        // 获取代币余额
        const tokens = TOKEN_CONTRACTS[networkData.chainId];
        if (tokens) {
            for (const [symbol, address] of Object.entries(tokens)) {
                try {
                    const tokenBalance = await getTokenBalance(address, account);
                    balances[symbol] = tokenBalance;
                } catch (error) {
                    console.warn(`Failed to get ${symbol} balance:`, error);
                    balances[symbol] = {
                        balance: '0',
                        balanceFormatted: 0,
                        symbol: symbol,
                        name: symbol,
                        decimals: 18,
                        error: error.message
                    };
                }
            }
        }
        
        // 缓存余额数据
        balanceCache[account] = {
            balances: balances,
            timestamp: Date.now()
        };
        
        return balances;
        
    } catch (error) {
        console.error('Failed to get multi-asset balances:', error);
        throw error;
    }
}

/**
 * 后台刷新策略和健康监控
 * Background refresh strategy and health monitoring
 */
let healthCheckInterval = null;
let backgroundUpdateInterval = null;
let connectionStatus = {
    web3Connected: false,
    walletConnected: false,
    networkSupported: true,
    lastUpdate: null,
    errorCount: 0,
    maxErrors: 5
};

/**
 * 初始化健康监控和后台刷新
 * Initialize health monitoring and background refresh
 */
function initializeHealthMonitoring() {
    // 清理现有的定时器
    if (healthCheckInterval) clearInterval(healthCheckInterval);
    if (backgroundUpdateInterval) clearInterval(backgroundUpdateInterval);
    
    // 健康检查：每30秒检查一次连接状态
    healthCheckInterval = setInterval(performHealthCheck, 30000);
    
    // 后台数据更新：每2分钟更新一次数据
    backgroundUpdateInterval = setInterval(backgroundDataUpdate, 120000);
    
    // 立即执行一次健康检查
    performHealthCheck();
    
    console.log('Health monitoring and background refresh initialized');
}

/**
 * 执行健康检查
 * Perform health check
 */
async function performHealthCheck() {
    try {
        // 检查Web3连接
        if (typeof window.ethereum !== 'undefined' && web3Instance) {
            connectionStatus.web3Connected = await web3Instance.eth.net.isListening();
        } else {
            connectionStatus.web3Connected = false;
        }
        
        // 检查钱包连接
        if (currentAccount && window.ethereum) {
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            connectionStatus.walletConnected = accounts.length > 0 && accounts.includes(currentAccount);
        } else {
            connectionStatus.walletConnected = false;
        }
        
        // 检查网络支持
        if (networkData) {
            connectionStatus.networkSupported = !networkData.unsupported;
        }
        
        connectionStatus.lastUpdate = new Date().toISOString();
        connectionStatus.errorCount = 0;
        
        // 更新健康指示器UI
        updateHealthIndicators();
        
    } catch (error) {
        console.error('Health check failed:', error);
        connectionStatus.errorCount++;
        
        if (connectionStatus.errorCount >= connectionStatus.maxErrors) {
            console.warn('Health check failed multiple times, may need user intervention');
            showHealthWarning();
        }
    }
}

/**
 * 后台数据更新
 * Background data update
 */
async function backgroundDataUpdate() {
    if (!currentAccount || !web3Instance) return;
    
    try {
        // 静默更新余额数据
        if (connectionStatus.web3Connected && connectionStatus.walletConnected) {
            await getMultiAssetBalances(currentAccount);
            
            // 清理过期缓存
            cleanExpiredCache();
        }
    } catch (error) {
        console.warn('Background update failed:', error);
    }
}

/**
 * 更新健康指示器UI
 * Update health indicator UI
 */
function updateHealthIndicators() {
    // 更新连接状态指示器
    const indicators = document.querySelectorAll('.health-indicator');
    indicators.forEach(indicator => {
        const type = indicator.dataset.type;
        let isHealthy = false;
        
        switch (type) {
            case 'web3':
                isHealthy = connectionStatus.web3Connected;
                break;
            case 'wallet':
                isHealthy = connectionStatus.walletConnected;
                break;
            case 'network':
                isHealthy = connectionStatus.networkSupported;
                break;
        }
        
        indicator.className = `health-indicator ${isHealthy ? 'healthy' : 'unhealthy'}`;
        indicator.title = `${type}: ${isHealthy ? 'Connected' : 'Disconnected'}`;
    });
    
    // 更新整体健康状态
    const overallHealth = connectionStatus.web3Connected && 
                         connectionStatus.walletConnected && 
                         connectionStatus.networkSupported;
    
    const healthStatus = document.getElementById('overall-health-status');
    if (healthStatus) {
        healthStatus.className = `health-status ${overallHealth ? 'healthy' : 'warning'}`;
        healthStatus.textContent = overallHealth ? '系统正常' : '连接问题';
    }
}

/**
 * 显示健康警告
 * Show health warning
 */
function showHealthWarning() {
    const warningElement = document.getElementById('health-warning');
    if (warningElement) {
        warningElement.style.display = 'block';
        warningElement.textContent = '检测到连接问题，请检查MetaMask连接和网络设置';
        
        // 5秒后自动隐藏
        setTimeout(() => {
            warningElement.style.display = 'none';
        }, 5000);
    }
}

/**
 * 清理过期缓存
 * Clean expired cache
 */
function cleanExpiredCache() {
    const now = Date.now();
    
    // 清理价格缓存
    Object.keys(priceCache).forEach(key => {
        if (priceCache[key].timestamp && (now - priceCache[key].timestamp) > RPC_CACHE_TTL) {
            delete priceCache[key];
        }
    });
    
    // 清理余额缓存
    Object.keys(balanceCache).forEach(key => {
        if (balanceCache[key].timestamp && (now - balanceCache[key].timestamp) > 300000) { // 5分钟TTL
            delete balanceCache[key];
        }
    });
    
    // 清理NFT缓存
    Object.keys(nftCache).forEach(key => {
        if (nftCache[key].timestamp && (now - nftCache[key].timestamp) > 600000) { // 10分钟TTL
            delete nftCache[key];
        }
    });
}

/**
 * 停止监控
 * Stop monitoring
 */
function stopHealthMonitoring() {
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
        healthCheckInterval = null;
    }
    
    if (backgroundUpdateInterval) {
        clearInterval(backgroundUpdateInterval);
        backgroundUpdateInterval = null;
    }
    
    console.log('Health monitoring stopped');
}

/**
 * 获取加密货币价格
 * Get cryptocurrency prices
 */
async function getCryptoPrices(symbols = ['ETH', 'BTC', 'USDC']) {
    try {
        // 检查缓存
        const cacheKey = symbols.join(',');
        const cached = priceCache[cacheKey];
        if (cached && Date.now() - cached.timestamp < 60000) { // 1分钟缓存
            return cached.prices;
        }
        
        // 模拟价格数据 (实际应用中应该调用真实API)
        const mockPrices = {
            BTC: { price: 113332, change24h: 2.45 },
            ETH: { price: 3678, change24h: -1.23 },
            USDC: { price: 1.00, change24h: 0.01 }
        };
        
        const prices = {};
        symbols.forEach(symbol => {
            if (mockPrices[symbol]) {
                prices[symbol] = mockPrices[symbol];
            }
        });
        
        // 缓存价格数据
        priceCache[cacheKey] = {
            prices: prices,
            timestamp: Date.now()
        };
        
        return prices;
        
    } catch (error) {
        console.error('Failed to get crypto prices:', error);
        throw error;
    }
}

/**
 * 获取用户NFT收藏
 * Get user NFT collection
 */
async function getUserNFTs(accountAddress = null, limit = 20) {
    const account = accountAddress || currentAccount;
    if (!account) {
        throw new Error('No account specified');
    }
    
    try {
        // 检查缓存
        const cached = nftCache[account];
        if (cached && Date.now() - cached.timestamp < 300000) { // 5分钟缓存
            return cached.nfts;
        }
        
        // 模拟NFT数据 (实际应用中应该调用NFT API)
        const mockNFTs = [
            {
                tokenId: '15',
                name: 'SLA Certificate September 2024',
                description: 'Monthly SLA performance certificate',
                image: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiMwMDczZTYiLz48L3N2Zz4=',
                contractAddress: '0x742d35cc6cf7f9eb6c1f7e4b1a0a4c8e8b3f5d1a',
                tokenStandard: 'ERC-721',
                blockchain: 'Base',
                verified: true,
                rarity: 'rare'
            }
        ];
        
        // 缓存NFT数据
        nftCache[account] = {
            nfts: mockNFTs,
            timestamp: Date.now()
        };
        
        return mockNFTs;
        
    } catch (error) {
        console.error('Failed to get user NFTs:', error);
        throw error;
    }
}

/**
 * 监控交易状态
 * Monitor transaction status
 */
async function monitorTransaction(txHash, callback) {
    if (!web3Instance) {
        throw new Error('Web3 not initialized');
    }
    
    try {
        let attempts = 0;
        const maxAttempts = 60; // 最多监控5分钟
        
        const checkStatus = async () => {
            try {
                const receipt = await web3Instance.eth.getTransactionReceipt(txHash);
                
                if (receipt) {
                    // 交易已确认
                    const transaction = await web3Instance.eth.getTransaction(txHash);
                    const result = {
                        status: receipt.status ? 'success' : 'failed',
                        blockNumber: receipt.blockNumber,
                        gasUsed: receipt.gasUsed,
                        transaction: transaction,
                        receipt: receipt
                    };
                    
                    callback(null, result);
                    return;
                }
                
                attempts++;
                if (attempts >= maxAttempts) {
                    callback(new Error('Transaction monitoring timeout'), null);
                    return;
                }
                
                // 5秒后重试
                setTimeout(checkStatus, 5000);
                
            } catch (error) {
                callback(error, null);
            }
        };
        
        checkStatus();
        
    } catch (error) {
        callback(error, null);
    }
}

/**
 * 获取区块链网络状态
 * Get blockchain network status
 */
async function getNetworkStatus() {
    if (!web3Instance) {
        throw new Error('Web3 not initialized');
    }
    
    try {
        const [blockNumber, gasPrice, networkId] = await Promise.all([
            web3Instance.eth.getBlockNumber(),
            web3Instance.eth.getGasPrice(),
            web3Instance.eth.net.getId()
        ]);
        
        const block = await web3Instance.eth.getBlock(blockNumber);
        
        return {
            blockNumber: blockNumber,
            gasPrice: gasPrice,
            gasPriceGwei: web3Instance.utils.fromWei(gasPrice, 'gwei'),
            networkId: networkId,
            blockTimestamp: block.timestamp,
            difficulty: block.difficulty,
            isConnected: true
        };
        
    } catch (error) {
        console.error('Failed to get network status:', error);
        throw error;
    }
}

/**
 * 启动实时数据更新
 * Start real-time data updates
 */
function startRealTimeUpdates(intervalMs = 30000) {
    // 清除现有的更新间隔
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    updateInterval = setInterval(async () => {
        if (!currentAccount || !web3Instance) return;
        
        try {
            // 更新余额
            await getMultiAssetBalances();
            
            // 更新价格
            await getCryptoPrices();
            
            // 触发UI更新事件
            if (typeof window.updateWeb3Data === 'function') {
                window.updateWeb3Data();
            }
            
            // 发送自定义事件
            window.dispatchEvent(new CustomEvent('web3DataUpdated', {
                detail: {
                    account: currentAccount,
                    balances: balanceCache[currentAccount]?.balances,
                    prices: priceCache,
                    timestamp: Date.now()
                }
            }));
            
        } catch (error) {
            console.error('Real-time update failed:', error);
        }
    }, intervalMs);
    
    console.log(`Real-time updates started (${intervalMs}ms interval)`);
}

/**
 * 停止实时数据更新
 * Stop real-time data updates
 */
function stopRealTimeUpdates() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
        console.log('Real-time updates stopped');
    }
}

/**
 * 清除所有缓存
 * Clear all caches
 */
function clearAllCaches() {
    priceCache = {};
    balanceCache = {};
    nftCache = {};
    console.log('All caches cleared');
}

/**
 * 获取交易费用估算
 * Get transaction fee estimation
 */
async function estimateTransactionFee(txParams) {
    if (!web3Instance) {
        throw new Error('Web3 not initialized');
    }
    
    try {
        const gasEstimate = await web3Instance.eth.estimateGas(txParams);
        const gasPrice = await web3Instance.eth.getGasPrice();
        
        const feeWei = gasEstimate * gasPrice;
        const feeEth = web3Instance.utils.fromWei(feeWei.toString(), 'ether');
        const feeGwei = web3Instance.utils.fromWei(gasPrice.toString(), 'gwei');
        
        return {
            gasEstimate: gasEstimate,
            gasPrice: gasPrice,
            gasPriceGwei: feeGwei,
            feeWei: feeWei,
            feeEth: feeEth,
            feeFormatted: parseFloat(feeEth).toFixed(6)
        };
        
    } catch (error) {
        console.error('Failed to estimate transaction fee:', error);
        throw error;
    }
}

// 扩展Web3Utils对象
window.Web3Utils = {
    // 原有功能
    isMetaMaskInstalled,
    connectMetaMask,
    disconnectWallet,
    getCurrentNetwork,
    switchToNetwork,
    getAccountBalance,
    getTransactionHistory,
    sendTransaction,
    signMessage,
    verifySignature,
    formatAddress,
    formatBalance,
    updateWalletUI,
    checkWalletConnection,
    initializeWeb3,
    
    // 新增增强功能
    getTokenBalance,
    getMultiAssetBalances,
    getCryptoPrices,
    getUserNFTs,
    monitorTransaction,
    getNetworkStatus,
    startRealTimeUpdates,
    stopRealTimeUpdates,
    clearAllCaches,
    estimateTransactionFee,
    
    // 获取当前状态
    getCurrentAccount: () => currentAccount,
    getCurrentNetwork: () => networkData,
    getWeb3Instance: () => web3Instance,
    getBalanceCache: () => balanceCache,
    getPriceCache: () => priceCache,
    getNFTCache: () => nftCache,
    
    // 配置和常量
    SUPPORTED_NETWORKS,
    TOKEN_CONTRACTS,
    ERC20_ABI
};

// 页面加载完成后自动初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeWeb3();
    
    // 如果已连接钱包，启动实时更新
    setTimeout(async () => {
        const status = await checkWalletConnection();
        if (status.connected) {
            startRealTimeUpdates();
        }
    }, 2000);
});