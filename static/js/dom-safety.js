// DOM安全操作工具库
(function(window) {
    'use strict';
    
    // 全局DOM安全工具
    window.DOMSafety = {
        // 安全获取元素
        get: function(id) {
            try {
                return document.getElementById(id);
            } catch (e) {
                console.warn(`无法获取元素 ${id}:`, e);
                return null;
            }
        },
        
        // 安全设置样式
        setStyle: function(id, prop, value) {
            const el = this.get(id);
            if (el && el.style && typeof el.style[prop] !== 'undefined') {
                el.style[prop] = value;
                return true;
            }
            return false;
        },
        
        // 安全设置显示/隐藏
        show: function(id) {
            return this.setStyle(id, 'display', 'block');
        },
        
        hide: function(id) {
            return this.setStyle(id, 'display', 'none');
        },
        
        // 安全设置值
        setValue: function(id, value) {
            const el = this.get(id);
            if (el && 'value' in el) {
                el.value = value;
                return true;
            }
            return false;
        },
        
        // 安全获取值
        getValue: function(id, defaultValue = '') {
            const el = this.get(id);
            return el && 'value' in el ? el.value : defaultValue;
        },
        
        // 安全事件绑定
        on: function(id, event, handler) {
            const el = this.get(id);
            if (el && typeof el.addEventListener === 'function') {
                el.addEventListener(event, handler);
                return true;
            }
            return false;
        },
        
        // 安全检查元素是否存在
        exists: function(id) {
            return this.get(id) !== null;
        },
        
        // 批量安全操作
        batch: function(operations) {
            const results = [];
            operations.forEach(op => {
                try {
                    if (op.type === 'style') {
                        results.push(this.setStyle(op.id, op.prop, op.value));
                    } else if (op.type === 'value') {
                        results.push(this.setValue(op.id, op.value));
                    } else if (op.type === 'event') {
                        results.push(this.on(op.id, op.event, op.handler));
                    }
                } catch (e) {
                    console.warn(`批量操作失败:`, op, e);
                    results.push(false);
                }
            });
            return results;
        }
    };
    
    // 全局错误处理
    window.addEventListener('error', function(e) {
        if (e.message && e.message.includes('Cannot read properties of null')) {
            console.warn('DOM访问错误已捕获:', e.message);
            // 阻止错误冒泡到控制台
            e.preventDefault();
            return false;
        }
    });
    
})(window);