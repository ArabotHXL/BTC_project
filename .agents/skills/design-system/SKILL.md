---
name: design-system
description: HashInsight Enterprise BTC-themed design system with Dark, Light, and System theme support. Use when creating or styling UI components, pages, cards, buttons, forms, or any visual element. Provides color palettes, CSS variables, spacing rules, typography, component patterns, and theme-switching implementation.
---

# HashInsight Enterprise Design System

## Theme Architecture

The app currently uses a **Dark** theme by default. The design system defines tokens for **Dark**, **Light**, and **System** modes. Dark is fully implemented; Light and System are proposed for future adoption via `[data-theme]` attribute toggling.

### Theme Switching (Proposed Implementation)

Add `data-theme` to `<html>` and use this JS to toggle:

```javascript
function setTheme(mode) {
  if (mode === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    localStorage.setItem('theme-preference', 'system');
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
      if (localStorage.getItem('theme-preference') === 'system') {
        document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
      }
    });
  } else {
    document.documentElement.setAttribute('data-theme', mode);
    localStorage.setItem('theme-preference', mode);
  }
}
setTheme(localStorage.getItem('theme-preference') || 'dark');
```

---

## 1. Color Palettes

### Current CSS Variables (`:root` in `static/css/styles.css`)

These tokens are **live in the codebase** today:

```css
:root {
  --primary-gradient: linear-gradient(135deg, #f7931e 0%, #ffc107 100%);
  --secondary-gradient: linear-gradient(135deg, #6c757d 0%, #495057 100%);
  --accent-color: #f7931e;
  --accent-secondary: #ffc107;
  --text-primary: #ffffff;
  --text-secondary: #adb5bd;
  --bg-primary: #212529;
  --bg-secondary: #1a1a1a;
  --bg-card: rgba(255, 255, 255, 0.05);
  --border-color: #333;
  --border-accent: #ffc107;
  --shadow-color: rgba(255, 193, 7, 0.2);
  --transition-default: all 0.3s ease;
  --border-radius-card: 15px;
  --border-radius-button: 8px;
}
```

### Current CSS Variables (`:root` in `analytics_main.html` inline styles)

These are **scoped to the analytics page**:

```css
:root {
  --primary-gold: #f7931a;
  --bg-gradient: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
  --card-bg: rgba(255, 255, 255, 0.05);
  --card-border: rgba(255, 255, 255, 0.1);
  --text-primary: #ffffff;
  --text-secondary: #b8b8b8;
  --shadow-glow: 0 8px 32px rgba(247, 147, 26, 0.15);
}
```

> **Note:** There is a known discrepancy: `styles.css` uses `#f7931e` for accent while `analytics_main.html` uses `#f7931a` (the official BTC orange). Also `--text-secondary` is `#adb5bd` in styles.css vs `#b8b8b8` in analytics. When unifying, prefer `#f7931a` (official BTC brand) and `#b8b8b8`.

### Hardcoded Colors Used Across the Codebase

These colors are used directly in CSS but not yet abstracted into variables:

| Color | Usage |
|---|---|
| `#1a2332` | Navbar background |
| `#2d3748` | Navbar border, tab bottom border |
| `#e2e8f0` | Metric labels, indicator labels |
| `#cbd5e0` | Muted text, sidebar text |
| `#48bb78` | Bullish / success / online / buy signal |
| `#f56565` | Bearish / danger / offline / sell signal |
| `#fbb040` | Neutral / warning / hold signal |
| `#17a2b8` | Info accent, CRM icon color |
| `#ed8936` | Warning status indicator |

### Dark Theme — Proposed Unified Tokens

When migrating to theme-aware variables, use this mapping:

```css
[data-theme="dark"], :root {
  --bg-page: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
  --bg-page-flat: #1a1a1a;
  --bg-card: rgba(255, 255, 255, 0.05);
  --bg-card-header: rgba(255, 255, 255, 0.05);
  --bg-input: rgba(255, 255, 255, 0.1);
  --bg-input-focus: rgba(255, 255, 255, 0.15);
  --bg-navbar: #1a2332;
  --bg-hover: rgba(255, 193, 7, 0.05);

  --text-primary: #ffffff;
  --text-secondary: #b8b8b8;
  --text-muted: #cbd5e0;
  --text-label: #e2e8f0;
  --text-on-brand: #000000;

  --border-default: rgba(255, 255, 255, 0.1);
  --border-medium: #333333;
  --border-strong: #2d3748;
  --border-accent: #f7931a;
  --border-accent-subtle: rgba(247, 147, 26, 0.3);

  --shadow-card: 0 4px 15px rgba(0, 0, 0, 0.2);
  --shadow-glow: 0 8px 32px rgba(247, 147, 26, 0.15);
  --shadow-hover: 0 10px 25px rgba(255, 193, 7, 0.2);

  --color-success: #48bb78;
  --color-danger: #f56565;
  --color-warning: #fbb040;
  --color-info: #17a2b8;
}
```

### Light Theme — Proposed Unified Tokens

```css
[data-theme="light"] {
  --bg-page: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 50%, #dee2e6 100%);
  --bg-page-flat: #f8f9fa;
  --bg-card: rgba(255, 255, 255, 0.95);
  --bg-card-header: rgba(0, 0, 0, 0.03);
  --bg-input: rgba(0, 0, 0, 0.05);
  --bg-input-focus: rgba(0, 0, 0, 0.08);
  --bg-navbar: #ffffff;
  --bg-hover: rgba(247, 147, 26, 0.08);

  --text-primary: #212529;
  --text-secondary: #6c757d;
  --text-muted: #868e96;
  --text-label: #495057;
  --text-on-brand: #ffffff;

  --border-default: rgba(0, 0, 0, 0.1);
  --border-medium: #dee2e6;
  --border-strong: #ced4da;
  --border-accent: #f7931a;
  --border-accent-subtle: rgba(247, 147, 26, 0.25);

  --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.08);
  --shadow-glow: 0 4px 16px rgba(247, 147, 26, 0.12);
  --shadow-hover: 0 8px 20px rgba(0, 0, 0, 0.12);

  --color-success: #28a745;
  --color-danger: #dc3545;
  --color-warning: #f0ad4e;
  --color-info: #0dcaf0;
}
```

### Brand Color (Constant Across Themes)

| Value | Usage |
|---|---|
| `#f7931a` | Official BTC orange — primary accent, active tabs, borders |
| `#ffc107` | Secondary gold — button gradients, hover highlights |
| Gradient: `linear-gradient(135deg, #f7931a 0%, #ffc107 100%)` | Primary buttons, card headers |

### Feature Icon Colors

| Feature | Color | CSS Class |
|---|---|---|
| Mining Calculator | `#ffc107` | `.calculator-item` |
| Batch Calculator | `#28a745` | `.batch-item` |
| CRM / Customer | `#17a2b8` | `.customer-item` |
| Analytics | `#dc3545` | `.analytics-item` |
| User Management | `#6f42c1` | `.user-item` |
| Performance Monitor | `#fd7e14` | `.performance-item` |

### Status Indicator Colors

| Status | Color | Glow (analytics page) |
|---|---|---|
| Online / Active | `#48bb78` | `0 0 8px rgba(72, 187, 120, 0.6)` |
| Offline / Degraded | `#f56565` | `0 0 8px rgba(245, 101, 101, 0.6)` |
| Warning | `#ed8936` | `0 0 8px rgba(237, 137, 54, 0.6)` |

---

## 2. Typography

| Element | Size | Weight | Color (current) |
|---|---|---|---|
| Page title (h2-h4) | Bootstrap default | 600 | `#ffffff` |
| Metric value | `2rem` | `bold` | `#ffffff` |
| Metric label | `0.9rem` | normal | `#e2e8f0` |
| Metric change | `0.8rem` | normal | `#cbd5e0` |
| Indicator value | `1.5rem` | `bold` | `#ffffff` |
| Profit value | `1.5rem` | `600` | success/danger contextual |
| Signal badge | `0.8rem` | `600` | `#ffffff` on colored bg |
| Stats value | `0.9rem` | `bold` | `#ffffff` |

**Font stacks (varies by page):**
- `styles.css`: `'Inter', -apple-system, BlinkMacSystemFont, sans-serif`
- `analytics_main.html`: `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif`

---

## 3. Spacing & Layout

### Border Radius

| Element | Radius | Source |
|---|---|---|
| Cards (styles.css) | `15px` via `--border-radius-card` | `styles.css` |
| Cards (analytics) | `16px` | `analytics_main.html` |
| Card headers | `16px 16px 0 0` (top only) | `analytics_main.html` |
| Buttons | `8px` via `--border-radius-button` | `styles.css` |
| Inputs | `8px` | `styles.css` |
| Signal badges | `4px` | `analytics_main.html` |
| Charts | `8px` | `analytics_main.html` |
| Status dots | `50%` (circle) | `analytics_main.html` |
| Language switcher | `25px` (pill) | `analytics_main.html` |

### Padding

| Element | Padding |
|---|---|
| Unified card body | `2rem` |
| Unified card header | `1rem 1.5rem` |
| Buttons (primary/secondary) | `0.75rem 1.5rem` |
| Signal badge | `4px 8px` |
| Chart container | `15px` |
| Execution panel | `1rem` |
| Execution preview | `0.75rem` |

### Grid & Gap

| Pattern | Value |
|---|---|
| Dashboard grid | `repeat(auto-fit, minmax(280px, 1fr))` |
| Grid gap | `2rem` |
| Grid margin | `2rem 0` |
| Stats gap | `1rem` (desktop), `0.5rem` (mobile) |
| Language switcher gap | `4px` |

### Key Dimensions

| Element | Height |
|---|---|
| Dashboard item | `min-height: 200px` |
| Chart container | `height: 400px` |
| Execution preview | `min-height: 120px` |
| Profit heatmap | `min-height: 300px` |
| Status dot | `12px × 12px` |

---

## 4. Component Patterns

### Card — Glassmorphism (analytics page)

```css
.card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  border-radius: 16px;
}
```

### Card — Unified (styles.css)

```css
.unified-card {
  background: var(--bg-card);
  backdrop-filter: blur(10px);
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius-card);
  padding: 2rem;
  transition: var(--transition-default);
}
.unified-card:hover {
  border-color: var(--border-accent);
  box-shadow: 0 10px 25px var(--shadow-color);
  transform: translateY(-2px);
}
```

### Metric Card (Gold Gradient)

```css
.metric-card {
  background: linear-gradient(135deg, rgba(247, 147, 26, 0.2), rgba(247, 147, 26, 0.05));
  border: 1px solid rgba(247, 147, 26, 0.3);
  transition: transform 0.2s ease-in-out;
}
.metric-card:hover { transform: translateY(-2px); }
```

Light theme adaptation (proposed):
```css
[data-theme="light"] .metric-card {
  background: linear-gradient(135deg, rgba(247, 147, 26, 0.1), rgba(247, 147, 26, 0.02));
}
```

### Buttons

```css
.btn-unified-primary {
  background: var(--primary-gradient);
  border: none;
  color: #000;
  font-weight: 600;
  border-radius: var(--border-radius-button);
  padding: 0.75rem 1.5rem;
  transition: var(--transition-default);
}
.btn-unified-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px var(--shadow-color);
}
.btn-unified-secondary {
  background: transparent;
  border: 2px solid var(--border-accent);
  color: var(--accent-secondary);
  font-weight: 600;
  border-radius: var(--border-radius-button);
  padding: 0.75rem 1.5rem;
}
.btn-unified-secondary:hover {
  background: var(--accent-secondary);
  color: #000;
  transform: translateY(-2px);
}
```

### Form Inputs

```css
.form-control-unified {
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid var(--border-color);
  color: var(--text-primary);
  border-radius: var(--border-radius-button);
  transition: var(--transition-default);
}
.form-control-unified:focus {
  background: rgba(255, 255, 255, 0.15);
  border-color: var(--border-accent);
  box-shadow: 0 0 0 0.25rem var(--shadow-color);
}
```

### Signal Badges

```css
.signal-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.signal-buy  { background-color: #48bb78; color: white; }
.signal-sell { background-color: #f56565; color: white; }
.signal-hold { background-color: #fbb040; color: white; }
```

### Status Indicator Dot

```css
.status-indicator {
  width: 12px; height: 12px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 8px;
}
.status-online  { background-color: #48bb78; box-shadow: 0 0 8px rgba(72, 187, 120, 0.6); }
.status-offline { background-color: #f56565; box-shadow: 0 0 8px rgba(245, 101, 101, 0.6); }
```

### Intelligence Alert Cards

```css
.intel-alert {
  border-radius: 8px; padding: 1rem;
  margin-bottom: 0.75rem; border-left: 4px solid;
}
.intel-alert-info    { background: rgba(23, 162, 184, 0.1);  border-color: #17a2b8; }
.intel-alert-success { background: rgba(72, 187, 120, 0.1);  border-color: #48bb78; }
.intel-alert-warning { background: rgba(251, 176, 64, 0.1);  border-color: #fbb040; }
.intel-alert-danger  { background: rgba(245, 101, 101, 0.1); border-color: #f56565; }
```

### Tabs (Analytics Inner Navigation)

```css
.nav-tabs { border-bottom: 2px solid #2d3748; }
.nav-tabs .nav-link {
  color: #cbd5e0;
  background-color: transparent;
  border: 1px solid transparent;
  border-radius: 8px 8px 0 0;
  margin-right: 4px;
}
.nav-tabs .nav-link:hover {
  color: #ffffff;
  background-color: rgba(255, 193, 7, 0.1);
  border-color: rgba(255, 193, 7, 0.3);
}
.nav-tabs .nav-link.active {
  color: #f7931a;
  background: rgba(247, 147, 26, 0.1);
  border-color: #f7931a #f7931a transparent;
}
```

### Loading Spinner

```css
.loading-spinner {
  display: inline-block;
  width: 1rem; height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 1s ease-in-out infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

Light theme override (proposed):
```css
[data-theme="light"] .loading-spinner {
  border-color: rgba(0, 0, 0, 0.15);
  border-top-color: #f7931a;
}
```

### Language Switcher (Pill)

```css
.global-lang-switcher {
  position: fixed; top: 15px; right: 15px; z-index: 9999;
  display: flex; gap: 4px;
  background: rgba(26, 29, 46, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid #f7931a;
  border-radius: 25px;
  padding: 4px;
  box-shadow: 0 4px 15px rgba(247, 147, 26, 0.2);
}
```

### Dashboard Item (Sweep Animation)

```css
.dashboard-item {
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius-card);
  padding: 2rem; min-height: 200px;
  display: flex; align-items: center; justify-content: center;
  transition: var(--transition-default);
  position: relative; overflow: hidden;
}
.dashboard-item:hover {
  border-color: var(--border-accent);
  transform: translateY(-5px);
  box-shadow: 0 10px 25px var(--shadow-color);
  background: rgba(255, 193, 7, 0.05);
}
.dashboard-item::before {
  content: '';
  position: absolute; top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 193, 7, 0.1), transparent);
  transition: left 0.5s ease;
}
.dashboard-item:hover::before { left: 100%; }
```

---

## 5. Animation & Transitions

| Effect | Value |
|---|---|
| Default transition | `all 0.3s ease` via `--transition-default` |
| Card hover lift | `transform: translateY(-2px)` |
| Dashboard item lift | `transform: translateY(-5px)` |
| Card hover border | Changes to `--border-accent` |
| Dashboard sweep | `::before` pseudo-element slides left→right with gold gradient |
| Spin animation | `rotate(360deg)` over `1s ease-in-out infinite` |

---

## 6. Responsive Breakpoints

| Breakpoint | Behavior |
|---|---|
| `≤ 768px` | Stats layout switches from row to column; gaps reduce |
| Dashboard grid | Auto-adjusts via `auto-fit, minmax(280px, 1fr)` |
| Metric cards | Use `col-xl-3 col-lg-6 mb-3` Bootstrap grid |

---

## 7. Quick Reference

### Theme-Aware Component Pattern

When adding new components, use CSS variables so they adapt to future theme switching:

```css
.my-component {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}
```

### Chart.js Colors

```javascript
const chartColors = {
  gridColor: 'rgba(255, 255, 255, 0.1)',
  textColor: '#b8b8b8',
  accentColor: '#f7931a',
  successColor: '#48bb78',
  dangerColor: '#f56565',
};
```

For light theme (proposed):
```javascript
const chartColors = {
  gridColor: 'rgba(0, 0, 0, 0.1)',
  textColor: '#6c757d',
  accentColor: '#f7931a',
  successColor: '#28a745',
  dangerColor: '#dc3545',
};
```

### Bilingual Patterns

Server-side (Jinja2):
```html
{% if current_lang == 'en' %}English Text{% else %}中文文本{% endif %}
```

Client-side (JavaScript):
```javascript
getText('中文文本', 'English Text')
currentLanguage === 'en' ? 'English' : '中文'
```
