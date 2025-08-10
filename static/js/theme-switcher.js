// 主题切换器 - Theme Switcher
class ThemeSwitcher {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.createToggleButton();
        this.bindEvents();
    }

    applyTheme(theme) {
        const body = document.body;
        const navbar = document.querySelector('.navbar');
        const cards = document.querySelectorAll('.card');
        const metricCards = document.querySelectorAll('.metric-card');
        const formControls = document.querySelectorAll('.form-control');
        const tables = document.querySelectorAll('.table');
        const alerts = document.querySelectorAll('.alert');

        // 移除所有主题类
        body.classList.remove('theme-dark', 'theme-light', 'bg-dark-custom', 'bg-light-custom');
        
        if (navbar) {
            navbar.classList.remove('navbar-dark-custom', 'navbar-light-custom');
        }

        // 应用新主题
        if (theme === 'dark') {
            body.classList.add('theme-dark', 'bg-dark-custom');
            if (navbar) {
                navbar.classList.add('navbar-dark-custom');
            }

            // 更新卡片
            cards.forEach(card => {
                card.classList.remove('card-light');
                card.classList.add('card-dark');
            });

            // 更新指标卡片
            metricCards.forEach(card => {
                card.classList.remove('metric-card-light');
                card.classList.add('metric-card-dark');
            });

            // 更新表单控件
            formControls.forEach(control => {
                control.classList.remove('form-control-light');
                control.classList.add('form-control-dark');
            });

            // 更新表格
            tables.forEach(table => {
                table.classList.remove('table-light-custom');
                table.classList.add('table-dark-custom');
            });

            // 更新警报框
            alerts.forEach(alert => {
                alert.classList.remove('alert-light-custom');
                alert.classList.add('alert-dark-custom');
            });

        } else {
            body.classList.add('theme-light', 'bg-light-custom');
            if (navbar) {
                navbar.classList.add('navbar-light-custom');
            }

            // 更新卡片
            cards.forEach(card => {
                card.classList.remove('card-dark');
                card.classList.add('card-light');
            });

            // 更新指标卡片
            metricCards.forEach(card => {
                card.classList.remove('metric-card-dark');
                card.classList.add('metric-card-light');
            });

            // 更新表单控件
            formControls.forEach(control => {
                control.classList.remove('form-control-dark');
                control.classList.add('form-control-light');
            });

            // 更新表格
            tables.forEach(table => {
                table.classList.remove('table-dark-custom');
                table.classList.add('table-light-custom');
            });

            // 更新警报框
            alerts.forEach(alert => {
                alert.classList.remove('alert-dark-custom');
                alert.classList.add('alert-light-custom');
            });
        }

        // 更新所有文本颜色
        this.updateTextColors(theme);
        
        // 保存主题到本地存储
        localStorage.setItem('theme', theme);
        this.currentTheme = theme;
    }

    updateTextColors(theme) {
        const textElements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, span, div, td, th, .card-header, .card-body, .nav-link, .navbar-brand');
        
        textElements.forEach(element => {
            if (theme === 'dark') {
                element.classList.remove('force-light-text');
                element.classList.add('force-dark-text');
            } else {
                element.classList.remove('force-dark-text');
                element.classList.add('force-light-text');
            }
        });

        // 更新状态颜色
        const successElements = document.querySelectorAll('.text-success');
        const dangerElements = document.querySelectorAll('.text-danger');
        const warningElements = document.querySelectorAll('.text-warning');
        const infoElements = document.querySelectorAll('.text-info');

        successElements.forEach(element => {
            element.classList.toggle('text-success-dark', theme === 'dark');
            element.classList.toggle('text-success-light', theme === 'light');
        });

        dangerElements.forEach(element => {
            element.classList.toggle('text-danger-dark', theme === 'dark');
            element.classList.toggle('text-danger-light', theme === 'light');
        });

        warningElements.forEach(element => {
            element.classList.toggle('text-warning-dark', theme === 'dark');
            element.classList.toggle('text-warning-light', theme === 'light');
        });

        infoElements.forEach(element => {
            element.classList.toggle('text-info-dark', theme === 'dark');
            element.classList.toggle('text-info-light', theme === 'light');
        });
    }

    createToggleButton() {
        const button = document.createElement('button');
        button.id = 'theme-toggle';
        button.className = 'btn btn-outline-secondary position-fixed';
        button.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 1050;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        `;
        
        this.updateButtonIcon(button);
        document.body.appendChild(button);
    }

    updateButtonIcon(button) {
        const icon = this.currentTheme === 'dark' ? '☀️' : '🌙';
        button.innerHTML = icon;
        button.title = this.currentTheme === 'dark' ? '切换到浅色主题' : '切换到深色主题';
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            if (e.target.id === 'theme-toggle') {
                this.toggleTheme();
            }
        });

        // 监听系统主题变化
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem('theme')) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(newTheme);
        
        const button = document.getElementById('theme-toggle');
        if (button) {
            this.updateButtonIcon(button);
        }

        // 通知其他组件主题已更改
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme: newTheme } 
        }));
    }

    getTheme() {
        return this.currentTheme;
    }
}

// 页面加载完成后初始化主题切换器
document.addEventListener('DOMContentLoaded', () => {
    window.themeSwitcher = new ThemeSwitcher();
});

// 导出给其他脚本使用
window.ThemeSwitcher = ThemeSwitcher;