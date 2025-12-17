/**
 * Frontend i18n Engine - 无刷新语言切换
 * Version 1.0
 */
(function(window) {
    'use strict';

    const I18n = {
        translations: {},
        currentLang: 'zh',
        initialized: false,
        onLanguageChange: [],

        /**
         * 初始化翻译引擎
         */
        async init() {
            if (this.initialized) return;
            
            // 从页面获取当前语言
            this.currentLang = document.documentElement.lang || 
                              document.body.dataset.lang || 
                              'zh';
            
            // 加载翻译数据
            await this.loadTranslations();
            this.initialized = true;
            
            // 立即翻译页面上的所有元素
            this.updatePageTranslations();
            
            console.log('[i18n] Initialized with language:', this.currentLang);
        },

        /**
         * 从服务器加载翻译数据
         */
        async loadTranslations() {
            try {
                const response = await fetch('/api/i18n/translations');
                if (response.ok) {
                    const data = await response.json();
                    // Support both old (both languages) and new (single language) format
                    if (data.translations) {
                        // Merge with existing translations
                        Object.assign(this.translations, data.translations);
                    }
                    // Only set currentLang on initial load, not when switching languages
                    // This prevents race conditions where API returns old language value
                    if (!this.initialized) {
                        this.currentLang = data.current_lang || this.currentLang;
                    }
                    console.log('[i18n] Loaded translations for', this.currentLang);
                }
            } catch (error) {
                console.error('[i18n] Failed to load translations:', error);
            }
        },

        /**
         * 获取翻译文本
         * @param {string} key - 翻译键
         * @param {string} lang - 目标语言 (可选)
         * @returns {string} 翻译后的文本
         */
        t(key, lang = null) {
            const targetLang = lang || this.currentLang;
            
            if (this.translations[targetLang] && this.translations[targetLang][key]) {
                return this.translations[targetLang][key];
            }
            
            // 回退到英文
            if (this.translations['en'] && this.translations['en'][key]) {
                return this.translations['en'][key];
            }
            
            // 最后返回key本身
            return key;
        },

        /**
         * Debug: Check if translations are loaded for a language
         */
        debugTranslations() {
            console.log('[i18n DEBUG] currentLang:', this.currentLang);
            console.log('[i18n DEBUG] translations keys:', Object.keys(this.translations));
            if (this.translations['zh']) {
                console.log('[i18n DEBUG] zh has', Object.keys(this.translations['zh']).length, 'keys');
                console.log('[i18n DEBUG] zh.register_new_miner:', this.translations['zh']['register_new_miner']);
            }
            if (this.translations['en']) {
                console.log('[i18n DEBUG] en has', Object.keys(this.translations['en']).length, 'keys');
            }
        },

        /**
         * 切换语言 (无刷新)
         * @param {string} lang - 目标语言 ('zh' 或 'en')
         */
        async setLanguage(lang) {
            if (lang !== 'zh' && lang !== 'en') {
                console.error('[i18n] Invalid language:', lang);
                return false;
            }

            if (lang === this.currentLang) {
                console.log('[i18n] Language already set to:', lang);
                return true;
            }

            try {
                // 通知服务器更新session
                const response = await fetch('/api/i18n/set-language', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ lang: lang })
                });

                if (response.ok) {
                    const oldLang = this.currentLang;
                    this.currentLang = lang;
                    
                    // Reload translations for new language (since API now returns single language)
                    await this.loadTranslations();
                    
                    // Debug: check if translations are loaded correctly
                    this.debugTranslations();
                    
                    // 更新页面上的所有翻译元素
                    this.updatePageTranslations();
                    
                    // 更新HTML lang属性
                    document.documentElement.lang = lang;
                    document.body.dataset.lang = lang;
                    
                    // 触发语言变化回调
                    this.onLanguageChange.forEach(callback => {
                        try {
                            callback(lang, oldLang);
                        } catch (e) {
                            console.error('[i18n] Callback error:', e);
                        }
                    });
                    
                    // 更新语言切换按钮状态
                    this.updateLanguageButtons(lang);
                    
                    console.log('[i18n] Language switched from', oldLang, 'to', lang);
                    return true;
                }
            } catch (error) {
                console.error('[i18n] Failed to set language:', error);
            }
            
            return false;
        },

        /**
         * 更新页面上所有带 data-i18n 属性的元素
         */
        updatePageTranslations() {
            const elements = document.querySelectorAll('[data-i18n]');
            const elementCount = elements.length;
            let updatedCount = 0;
            let skippedKeys = [];
            
            // 更新文本内容
            elements.forEach(el => {
                const key = el.dataset.i18n;
                const translated = this.t(key);
                if (translated && translated !== key) {
                    el.textContent = translated;
                    updatedCount++;
                } else {
                    // Track keys that were not updated (translation not found)
                    if (!skippedKeys.includes(key)) {
                        skippedKeys.push(key);
                    }
                }
            });
            
            console.log(`[i18n] Updated ${updatedCount}/${elementCount} elements for ${this.currentLang}`);
            if (skippedKeys.length > 0 && skippedKeys.length <= 20) {
                console.log('[i18n] Skipped keys (no translation found):', skippedKeys);
            }

            // 更新placeholder
            document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
                const key = el.dataset.i18nPlaceholder;
                const translated = this.t(key);
                if (translated !== key) {
                    el.placeholder = translated;
                }
            });

            // 更新title属性
            document.querySelectorAll('[data-i18n-title]').forEach(el => {
                const key = el.dataset.i18nTitle;
                const translated = this.t(key);
                if (translated !== key) {
                    el.title = translated;
                }
            });

            // 更新aria-label
            document.querySelectorAll('[data-i18n-aria]').forEach(el => {
                const key = el.dataset.i18nAria;
                const translated = this.t(key);
                if (translated !== key) {
                    el.setAttribute('aria-label', translated);
                }
            });
        },

        /**
         * 更新语言切换按钮的激活状态
         */
        updateLanguageButtons(lang) {
            // 更新所有语言切换按钮
            document.querySelectorAll('.lang-switch-btn, .language-btn').forEach(btn => {
                const btnLang = btn.dataset.lang;
                if (btnLang === lang) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            // 更新下拉菜单中的语言选项
            document.querySelectorAll('.dropdown-item[data-lang]').forEach(item => {
                const itemLang = item.dataset.lang;
                if (itemLang === lang) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
        },

        /**
         * 注册语言变化回调
         * @param {Function} callback - 回调函数 (newLang, oldLang) => void
         */
        onLangChange(callback) {
            if (typeof callback === 'function') {
                this.onLanguageChange.push(callback);
            }
        },

        /**
         * 获取当前语言
         * @returns {string}
         */
        getLang() {
            return this.currentLang;
        },

        /**
         * 检查是否为中文
         * @returns {boolean}
         */
        isZh() {
            return this.currentLang === 'zh';
        },

        /**
         * 检查是否为英文
         * @returns {boolean}
         */
        isEn() {
            return this.currentLang === 'en';
        }
    };

    // 绑定语言切换事件
    document.addEventListener('DOMContentLoaded', () => {
        // 初始化
        I18n.init();

        // 为所有语言切换按钮绑定点击事件
        document.addEventListener('click', async (e) => {
            const btn = e.target.closest('[data-lang-switch]');
            if (btn) {
                e.preventDefault();
                const lang = btn.dataset.lang || btn.dataset.langSwitch;
                if (lang) {
                    await I18n.setLanguage(lang);
                }
            }
        });
    });

    // 暴露到全局
    window.I18n = I18n;
    window.t = (key, lang) => I18n.t(key, lang);

})(window);
