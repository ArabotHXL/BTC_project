// 优化的页面加载器 - 减少界面加载时间
(function() {
    'use strict';
    
    // 预加载关键数据
    var pageLoadStart = performance.now();
    console.log("页面加载优化器启动");
    
    // 使用Web Worker进行后台数据加载（如果支持的话）
    var useWebWorker = false; // 简化版本，不使用Web Worker
    
    // 优化的DOM元素查找缓存
    var elementCache = {};
    function getCachedElement(id) {
        if (!elementCache[id]) {
            elementCache[id] = document.getElementById(id);
        }
        return elementCache[id];
    }
    
    // 延迟加载非关键功能
    var deferredTasks = [];
    function deferTask(task, delay) {
        deferredTasks.push({ task: task, delay: delay || 100 });
    }
    
    // 批量执行延迟任务
    function executeDeferredTasks() {
        deferredTasks.forEach(function(item, index) {
            setTimeout(item.task, item.delay * (index + 1));
        });
    }
    
    // 预缓存关键网络数据
    var networkDataCache = {
        lastUpdate: 0,
        data: null,
        isLoading: false
    };
    
    function preloadNetworkData() {
        if (networkDataCache.isLoading) return;
        
        networkDataCache.isLoading = true;
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/api/network-stats', true);
        xhr.onload = function() {
            if (xhr.status === 200) {
                try {
                    networkDataCache.data = JSON.parse(xhr.responseText);
                    networkDataCache.lastUpdate = Date.now();
                    networkDataCache.isLoading = false;
                    console.log("网络数据预加载成功");
                } catch (e) {
                    console.log("网络数据解析失败:", e);
                    networkDataCache.isLoading = false;
                }
            } else {
                networkDataCache.isLoading = false;
            }
        };
        xhr.onerror = function() {
            networkDataCache.isLoading = false;
        };
        xhr.send();
    }
    
    // 快速显示基本界面元素
    function showBasicUI() {
        var loadingSpinner = getCachedElement('loading-spinner');
        if (loadingSpinner) {
            loadingSpinner.style.display = 'none';
        }
        
        // 显示主要内容区域
        var mainContent = document.querySelector('.container-fluid');
        if (mainContent) {
            mainContent.style.visibility = 'visible';
            mainContent.style.opacity = '1';
        }
    }
    
    // DOM Ready优化版本
    function onDOMReady(callback) {
        if (document.readyState === 'complete' || 
            document.readyState === 'interactive') {
            setTimeout(callback, 1);
        } else {
            document.addEventListener('DOMContentLoaded', callback);
        }
    }
    
    // 页面加载优化主函数
    function optimizePageLoad() {
        var loadTime = performance.now() - pageLoadStart;
        console.log("DOM加载完成，用时:", loadTime.toFixed(2), "ms");
        
        // 立即显示基本UI
        showBasicUI();
        
        // 延迟加载次要功能
        deferTask(function() {
            console.log("开始加载次要功能");
            if (window.fetchNetworkStats) {
                window.fetchNetworkStats();
            }
        }, 50);
        
        deferTask(function() {
            console.log("开始加载矿机数据");
            if (window.fetchMiners) {
                window.fetchMiners();
            }
        }, 100);
        
        deferTask(function() {
            console.log("开始初始化图表");
            if (window.initializeCharts) {
                window.initializeCharts();
            }
        }, 200);
        
        // 执行所有延迟任务
        executeDeferredTasks();
    }
    
    // 预加载网络数据
    preloadNetworkData();
    
    // 启动页面优化
    onDOMReady(optimizePageLoad);
    
    // 导出缓存访问函数
    window.getNetworkDataCache = function() {
        return networkDataCache;
    };
    
    window.getCachedElement = getCachedElement;
    
})();