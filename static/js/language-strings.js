/**
 * Language Strings - Centralized Bilingual Content Management
 * Version: 1.0.0
 * 
 * This module provides centralized management for all bilingual strings used in the frontend.
 * It integrates with the backend language system through session storage and meta tags.
 * 
 * Usage:
 *   i18n.t('common.loading')  // Returns: 'Loading...' or '加载中...'
 *   i18n.t('calculator.title') // Returns: 'Mining Profitability Calculator' or '挖矿盈利能力计算器'
 *   i18n.setLanguage('en')    // Switch to English
 *   i18n.getCurrentLanguage() // Returns: 'en' or 'zh'
 */

const LanguageStrings = {
    en: {
        // Common UI Elements
        common: {
            loading: 'Loading...',
            calculating: 'Calculating...',
            error: 'Error',
            success: 'Success',
            warning: 'Warning',
            info: 'Info',
            confirm: 'Confirm',
            cancel: 'Cancel',
            save: 'Save',
            delete: 'Delete',
            edit: 'Edit',
            close: 'Close',
            submit: 'Submit',
            reset: 'Reset',
            retry: 'Retry',
            back: 'Back',
            next: 'Next',
            previous: 'Previous',
            search: 'Search',
            filter: 'Filter',
            export: 'Export',
            import: 'Import',
            download: 'Download',
            upload: 'Upload',
            select: 'Select',
            selectAll: 'Select All',
            deselectAll: 'Deselect All',
            selected: 'Selected',
            noData: 'No data available',
            failedToLoad: 'Failed to load',
            loadError: 'Load error',
            networkError: 'Network error',
            pleaseWait: 'Please wait...',
            processing: 'Processing...'
        },

        // Calculator Module
        calculator: {
            title: 'Mining Profitability Calculator',
            subtitle: 'Bitcoin Mining ROI Analysis',
            selectMiner: 'Select Miner Model',
            selectMinerPlaceholder: 'Select a miner model',
            minerModel: 'Miner Model',
            hashrate: 'Hashrate',
            powerConsumption: 'Power Consumption',
            minerCount: 'Miner Count',
            sitePowerMW: 'Site Power (MW)',
            totalHashrate: 'Total Hashrate',
            totalPower: 'Total Power',
            electricityCost: 'Electricity Cost',
            hostingFee: 'Hosting Fee',
            maintenanceFee: 'Maintenance Fee',
            btcPrice: 'BTC Price',
            networkDifficulty: 'Network Difficulty',
            networkHashrate: 'Network Hashrate',
            blockReward: 'Block Reward',
            calculate: 'Calculate',
            calculating: 'Calculating...',
            results: 'Calculation Results',
            dailyOutput: 'Daily Output',
            monthlyOutput: 'Monthly Output',
            yearlyOutput: 'Yearly Output',
            dailyRevenue: 'Daily Revenue',
            monthlyRevenue: 'Monthly Revenue',
            yearlyRevenue: 'Yearly Revenue',
            dailyProfit: 'Daily Profit',
            monthlyProfit: 'Monthly Profit',
            yearlyProfit: 'Yearly Profit',
            roiPeriod: 'ROI Period',
            profitMargin: 'Profit Margin',
            breakEvenMonth: 'Break Even Month',
            hostProfit: 'Host Profit',
            clientProfit: 'Client Profit',
            totalIncome: 'Total Income',
            totalCost: 'Total Cost',
            netProfit: 'Net Profit',
            algorithm1: 'Algorithm 1',
            algorithm2: 'Algorithm 2',
            difference: 'Difference',
            method1Daily: 'Method 1 (Daily)',
            method2Daily: 'Method 2 (Daily)',
            calculateSuccess: 'Calculation completed successfully',
            calculateError: 'Calculation error',
            displayError: 'Display error',
            invalidInput: 'Invalid input',
            pleaseSelectMiner: 'Please select a miner model',
            yourProfitInfo: 'Your Profit Information',
            hostProfitInfo: 'Host Profit Information',
            btcMined: 'BTC Mined',
            electricityCostTotal: 'Electricity Cost',
            hostingFeeTotal: 'Hosting Fee',
            maintenanceFeeTotal: 'Maintenance Fee',
            revenueFromMining: 'Revenue from Mining'
        },

        // Operations Center Module
        operations: {
            miningCenter: 'Mining Operations Center',
            analyticsCenter: 'Data Analytics Center',
            adminCenter: 'Admin Center',
            minerManagement: 'Miner Management',
            batchCalculator: 'Batch Calculator',
            importMiners: 'Import Miners',
            minerList: 'Miner List',
            loadingMiners: 'Loading miners...',
            loadingData: 'Loading data...',
            failedToLoad: 'Failed to load',
            retry: 'Retry',
            error: 'Error',
            noMinersFound: 'No miners found',
            minerSelected: 'miner(s) selected',
            sendToBatch: 'Send to Batch Calculator',
            model: 'Model',
            hashrate: 'Hashrate',
            power: 'Power',
            status: 'Status',
            active: 'Active',
            inactive: 'Inactive',
            select: 'Select',
            iframeLoadError: 'Failed to load content',
            tabAlreadyLoaded: 'Tab already loaded',
            accordionAlreadyLoaded: 'Accordion already loaded'
        },

        // Charts and Analytics
        charts: {
            price: 'Price',
            difficulty: 'Difficulty',
            hashrate: 'Hashrate',
            revenue: 'Revenue',
            profit: 'Profit',
            cost: 'Cost',
            roi: 'ROI',
            daily: 'Daily',
            weekly: 'Weekly',
            monthly: 'Monthly',
            yearly: 'Yearly',
            trend: 'Trend',
            projection: 'Projection',
            historical: 'Historical',
            current: 'Current',
            average: 'Average',
            maximum: 'Maximum',
            minimum: 'Minimum',
            total: 'Total',
            breakdown: 'Breakdown',
            comparison: 'Comparison',
            heatmap: 'Heatmap',
            profitabilityHeatmap: 'Customer Profitability Heatmap',
            roiProgression: 'Client ROI Progression: Static vs Dynamic',
            breakEvenAnalysis: 'Break Even Analysis',
            legend: 'Legend',
            xAxis: 'X-Axis',
            yAxis: 'Y-Axis',
            month: 'Month',
            value: 'Value'
        },

        // Forms and Validation
        forms: {
            required: 'This field is required',
            invalidEmail: 'Invalid email address',
            invalidNumber: 'Invalid number',
            invalidDate: 'Invalid date',
            minValue: 'Minimum value is',
            maxValue: 'Maximum value is',
            minLength: 'Minimum length is',
            maxLength: 'Maximum length is',
            passwordMismatch: 'Passwords do not match',
            fileTooBig: 'File is too big',
            invalidFileType: 'Invalid file type',
            uploadSuccess: 'Upload successful',
            uploadFailed: 'Upload failed',
            saveSuccess: 'Saved successfully',
            saveFailed: 'Save failed',
            deleteSuccess: 'Deleted successfully',
            deleteFailed: 'Delete failed'
        },

        // Units and Measurements
        units: {
            thps: 'TH/s',
            ehps: 'EH/s',
            watts: 'W',
            kilowatts: 'kW',
            megawatts: 'MW',
            kwh: 'kWh',
            usd: 'USD',
            btc: 'BTC',
            sats: 'sats',
            percent: '%',
            days: 'days',
            months: 'months',
            years: 'years'
        },

        // Time Periods
        time: {
            second: 'second',
            seconds: 'seconds',
            minute: 'minute',
            minutes: 'minutes',
            hour: 'hour',
            hours: 'hours',
            day: 'day',
            days: 'days',
            week: 'week',
            weeks: 'weeks',
            month: 'month',
            months: 'months',
            year: 'year',
            years: 'years',
            daily: 'Daily',
            weekly: 'Weekly',
            monthly: 'Monthly',
            yearly: 'Yearly',
            today: 'Today',
            yesterday: 'Yesterday',
            thisWeek: 'This Week',
            thisMonth: 'This Month',
            thisYear: 'This Year'
        }
    },

    zh: {
        // 常用UI元素
        common: {
            loading: '加载中...',
            calculating: '计算中...',
            error: '错误',
            success: '成功',
            warning: '警告',
            info: '信息',
            confirm: '确认',
            cancel: '取消',
            save: '保存',
            delete: '删除',
            edit: '编辑',
            close: '关闭',
            submit: '提交',
            reset: '重置',
            retry: '重试',
            back: '返回',
            next: '下一步',
            previous: '上一步',
            search: '搜索',
            filter: '筛选',
            export: '导出',
            import: '导入',
            download: '下载',
            upload: '上传',
            select: '选择',
            selectAll: '全选',
            deselectAll: '取消全选',
            selected: '已选择',
            noData: '暂无数据',
            failedToLoad: '加载失败',
            loadError: '加载错误',
            networkError: '网络错误',
            pleaseWait: '请稍候...',
            processing: '处理中...'
        },

        // 计算器模块
        calculator: {
            title: '挖矿盈利能力计算器',
            subtitle: '比特币挖矿ROI分析',
            selectMiner: '选择矿机型号',
            selectMinerPlaceholder: '选择矿机型号',
            minerModel: '矿机型号',
            hashrate: '算力',
            powerConsumption: '功耗',
            minerCount: '矿机数量',
            sitePowerMW: '矿场功率 (MW)',
            totalHashrate: '总算力',
            totalPower: '总功耗',
            electricityCost: '电费成本',
            hostingFee: '托管费',
            maintenanceFee: '维护费',
            btcPrice: 'BTC价格',
            networkDifficulty: '网络难度',
            networkHashrate: '全网算力',
            blockReward: '区块奖励',
            calculate: '计算',
            calculating: '计算中...',
            results: '计算结果',
            dailyOutput: '日产出',
            monthlyOutput: '月产出',
            yearlyOutput: '年产出',
            dailyRevenue: '日收入',
            monthlyRevenue: '月收入',
            yearlyRevenue: '年收入',
            dailyProfit: '日利润',
            monthlyProfit: '月利润',
            yearlyProfit: '年利润',
            roiPeriod: '回本周期',
            profitMargin: '利润率',
            breakEvenMonth: '回本月份',
            hostProfit: '矿场主收益',
            clientProfit: '客户收益',
            totalIncome: '总收入',
            totalCost: '总成本',
            netProfit: '净利润',
            algorithm1: '算法1',
            algorithm2: '算法2',
            difference: '差异',
            method1Daily: '方法1（每日）',
            method2Daily: '方法2（每日）',
            calculateSuccess: '计算成功',
            calculateError: '计算错误',
            displayError: '显示错误',
            invalidInput: '输入无效',
            pleaseSelectMiner: '请选择矿机型号',
            yourProfitInfo: '客户收益信息',
            hostProfitInfo: '矿场主收益信息',
            btcMined: 'BTC产出',
            electricityCostTotal: '电费成本',
            hostingFeeTotal: '托管费',
            maintenanceFeeTotal: '维护费',
            revenueFromMining: '挖矿收入'
        },

        // 操作中心模块
        operations: {
            miningCenter: '挖矿运营中心',
            analyticsCenter: '数据分析中心',
            adminCenter: '管理中心',
            minerManagement: '矿机管理',
            batchCalculator: '批量计算器',
            importMiners: '导入矿机',
            minerList: '矿机列表',
            loadingMiners: '加载矿机中...',
            loadingData: '加载数据中...',
            failedToLoad: '加载失败',
            retry: '重试',
            error: '错误',
            noMinersFound: '未找到矿机',
            minerSelected: '台矿机已选择',
            sendToBatch: '发送到批量计算器',
            model: '型号',
            hashrate: '算力',
            power: '功耗',
            status: '状态',
            active: '激活',
            inactive: '未激活',
            select: '选择',
            iframeLoadError: '加载内容失败',
            tabAlreadyLoaded: '标签页已加载',
            accordionAlreadyLoaded: '手风琴已加载'
        },

        // 图表和分析
        charts: {
            price: '价格',
            difficulty: '难度',
            hashrate: '算力',
            revenue: '收入',
            profit: '利润',
            cost: '成本',
            roi: 'ROI',
            daily: '每日',
            weekly: '每周',
            monthly: '每月',
            yearly: '每年',
            trend: '趋势',
            projection: '预测',
            historical: '历史',
            current: '当前',
            average: '平均',
            maximum: '最大',
            minimum: '最小',
            total: '总计',
            breakdown: '分解',
            comparison: '对比',
            heatmap: '热力图',
            profitabilityHeatmap: '客户收益热力图',
            roiProgression: '客户ROI进展: Static vs Dynamic',
            breakEvenAnalysis: '回本分析',
            legend: '图例',
            xAxis: 'X轴',
            yAxis: 'Y轴',
            month: '月份',
            value: '数值'
        },

        // 表单和验证
        forms: {
            required: '此字段为必填项',
            invalidEmail: '邮箱地址无效',
            invalidNumber: '数字无效',
            invalidDate: '日期无效',
            minValue: '最小值为',
            maxValue: '最大值为',
            minLength: '最小长度为',
            maxLength: '最大长度为',
            passwordMismatch: '密码不匹配',
            fileTooBig: '文件太大',
            invalidFileType: '文件类型无效',
            uploadSuccess: '上传成功',
            uploadFailed: '上传失败',
            saveSuccess: '保存成功',
            saveFailed: '保存失败',
            deleteSuccess: '删除成功',
            deleteFailed: '删除失败'
        },

        // 单位和度量
        units: {
            thps: 'TH/s',
            ehps: 'EH/s',
            watts: 'W',
            kilowatts: 'kW',
            megawatts: 'MW',
            kwh: 'kWh',
            usd: 'USD',
            btc: 'BTC',
            sats: '聪',
            percent: '%',
            days: '天',
            months: '月',
            years: '年'
        },

        // 时间周期
        time: {
            second: '秒',
            seconds: '秒',
            minute: '分钟',
            minutes: '分钟',
            hour: '小时',
            hours: '小时',
            day: '天',
            days: '天',
            week: '周',
            weeks: '周',
            month: '月',
            months: '月',
            year: '年',
            years: '年',
            daily: '每日',
            weekly: '每周',
            monthly: '每月',
            yearly: '每年',
            today: '今天',
            yesterday: '昨天',
            thisWeek: '本周',
            thisMonth: '本月',
            thisYear: '今年'
        }
    }
};

/**
 * Language Manager Class
 * Manages language switching and translation lookups
 */
class LanguageManager {
    constructor() {
        // Read language from meta tag (set by backend)
        const metaLang = document.querySelector('meta[name="language"]')?.content;
        // Read from HTML lang attribute as fallback
        const htmlLang = document.documentElement.lang;
        
        // Determine initial language (priority: meta tag > html lang > default 'zh')
        let initialLang = 'zh';
        if (metaLang && (metaLang === 'en' || metaLang === 'zh')) {
            initialLang = metaLang;
        } else if (htmlLang && htmlLang.startsWith('en')) {
            initialLang = 'en';
        } else if (htmlLang && htmlLang.startsWith('zh')) {
            initialLang = 'zh';
        }
        
        this.currentLang = initialLang;
        
        // Listen for language changes from backend
        this.setupLanguageSync();
        
        console.log('[i18n] Language Manager initialized, current language:', this.currentLang);
    }
    
    /**
     * Setup language synchronization with backend
     * Watches for meta tag changes and dispatches events
     */
    setupLanguageSync() {
        // Watch for meta tag changes (in case backend updates it)
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'content') {
                    const newLang = mutation.target.content;
                    if ((newLang === 'en' || newLang === 'zh') && newLang !== this.currentLang) {
                        console.log('[i18n] Language changed via meta tag:', newLang);
                        this.currentLang = newLang;
                        this.dispatchLanguageChangeEvent();
                    }
                }
            });
        });
        
        const metaTag = document.querySelector('meta[name="language"]');
        if (metaTag) {
            observer.observe(metaTag, { attributes: true });
        }
    }
    
    /**
     * Get translated string by path
     * @param {string} path - Dot-separated path (e.g., 'common.loading', 'calculator.title')
     * @param {object} vars - Optional variables for string interpolation
     * @returns {string} Translated string
     */
    t(path, vars = {}) {
        const keys = path.split('.');
        let value = LanguageStrings[this.currentLang];
        
        // Navigate through nested object
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                console.warn(`[i18n] Translation not found for path: ${path}`);
                return path; // Fallback to path if not found
            }
        }
        
        // Variable interpolation
        if (typeof value === 'string' && Object.keys(vars).length > 0) {
            return this.interpolate(value, vars);
        }
        
        return value;
    }
    
    /**
     * Interpolate variables into string
     * Supports {varName} syntax
     * @param {string} str - Template string
     * @param {object} vars - Variables object
     * @returns {string} Interpolated string
     */
    interpolate(str, vars) {
        return str.replace(/\{(\w+)\}/g, (match, key) => {
            return vars.hasOwnProperty(key) ? vars[key] : match;
        });
    }
    
    /**
     * Set current language
     * Note: This only affects frontend. Backend language is controlled via session.
     * @param {string} lang - Language code ('en' or 'zh')
     */
    setLanguage(lang) {
        if (lang !== 'en' && lang !== 'zh') {
            console.error('[i18n] Invalid language code:', lang);
            return;
        }
        
        if (lang === this.currentLang) {
            return; // No change needed
        }
        
        const oldLang = this.currentLang;
        this.currentLang = lang;
        
        console.log(`[i18n] Language changed from ${oldLang} to ${lang}`);
        
        // Update HTML lang attribute
        document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
        
        // Dispatch event for components to react
        this.dispatchLanguageChangeEvent();
    }
    
    /**
     * Get current language code
     * @returns {string} Current language ('en' or 'zh')
     */
    getCurrentLanguage() {
        return this.currentLang;
    }
    
    /**
     * Check if current language is English
     * @returns {boolean}
     */
    isEnglish() {
        return this.currentLang === 'en';
    }
    
    /**
     * Check if current language is Chinese
     * @returns {boolean}
     */
    isChinese() {
        return this.currentLang === 'zh';
    }
    
    /**
     * Dispatch language change event
     * Other components can listen to this event to update their UI
     */
    dispatchLanguageChangeEvent() {
        const event = new CustomEvent('languageChanged', {
            detail: {
                lang: this.currentLang,
                timestamp: new Date().toISOString()
            }
        });
        window.dispatchEvent(event);
        console.log('[i18n] Language change event dispatched');
    }
    
    /**
     * Get all available translations for a category
     * @param {string} category - Category name (e.g., 'common', 'calculator')
     * @returns {object} Category translations in current language
     */
    getCategory(category) {
        if (LanguageStrings[this.currentLang] && LanguageStrings[this.currentLang][category]) {
            return LanguageStrings[this.currentLang][category];
        }
        console.warn(`[i18n] Category not found: ${category}`);
        return {};
    }
}

// Create and export singleton instance
window.i18n = new LanguageManager();

// Also export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { LanguageManager, LanguageStrings };
}

console.log('[i18n] Language Strings module loaded successfully');
