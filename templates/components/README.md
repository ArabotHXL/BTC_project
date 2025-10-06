# HashInsight Components Documentation

## Overview

This directory contains reusable UI components for the HashInsight platform. All components support bilingual functionality (Chinese/English) and follow the design system standards.

## Design System

All components use CSS custom properties (design tokens) defined in `static/css/design-tokens.css` and follow BEM naming conventions defined in `static/css/components.css`.

## Available Components

### 1. Card Components

The card component system provides a unified, consistent way to display content cards across the application. All cards use BEM naming conventions for better maintainability and consistency.

#### Basic Card Structure

```html
<!-- Basic Card -->
<div class="card">
    <div class="card__header">
        <h5>Card Title</h5>
    </div>
    <div class="card__body">
        <p>Card content goes here</p>
    </div>
    <div class="card__footer">
        <button>Action</button>
    </div>
</div>
```

#### Card Color Modifiers

```html
<!-- Primary Card (Gold theme) -->
<div class="card card--primary">
    <div class="card__header">Primary Card</div>
    <div class="card__body">Content</div>
</div>

<!-- Success Card (Green theme) -->
<div class="card card--success">
    <div class="card__header">Success Card</div>
    <div class="card__body">Content</div>
</div>

<!-- Info Card (Blue theme) -->
<div class="card card--info">
    <div class="card__header">Info Card</div>
    <div class="card__body">Content</div>
</div>

<!-- Warning Card (Yellow theme) -->
<div class="card card--warning">
    <div class="card__header">Warning Card</div>
    <div class="card__body">Content</div>
</div>

<!-- Danger Card (Red theme) -->
<div class="card card--danger">
    <div class="card__header">Danger Card</div>
    <div class="card__body">Content</div>
</div>

<!-- Secondary Card (Gray theme) -->
<div class="card card--secondary">
    <div class="card__header">Secondary Card</div>
    <div class="card__body">Content</div>
</div>
```

#### Card Shadow Modifiers

```html
<div class="card card--shadow-sm">Small shadow</div>
<div class="card card--shadow-md">Medium shadow</div>
<div class="card card--shadow-lg">Large shadow</div>
<div class="card card--shadow-xl">Extra large shadow</div>
```

#### Card Effect Modifiers

```html
<!-- Glow effect on hover -->
<div class="card card--glow">
    <div class="card__body">Glows on hover</div>
</div>

<!-- Enhanced hover lift -->
<div class="card card--hover">
    <div class="card__body">Lifts on hover</div>
</div>
```

#### Combining Modifiers

```html
<!-- Primary card with glow and shadow -->
<div class="card card--primary card--glow card--shadow-lg">
    <div class="card__header">
        <h5>Featured Card</h5>
    </div>
    <div class="card__body">
        <p>Multiple modifiers for emphasis</p>
    </div>
</div>
```

#### Body Size Modifiers

```html
<!-- Compact padding -->
<div class="card">
    <div class="card__body card__body--compact">
        Reduced padding
    </div>
</div>

<!-- Spacious padding -->
<div class="card">
    <div class="card__body card__body--spacious">
        Extra padding
    </div>
</div>
```

#### Design Specifications

- **Border**: 2px solid with color variant
- **Border Radius**: 16px (var(--radius-lg))
- **Padding**: 24px (var(--spacing-lg))
- **Shadows**: Multiple levels (sm, md, lg, xl)
- **Transitions**: 0.3s ease-in-out
- **Hover Effects**: Automatic lift and enhanced shadow

#### Responsive Behavior

Cards automatically adjust for different screen sizes:
- **Mobile (320px-767px)**: Full width, stacked layout
- **Tablet (768px-1023px)**: Flexible grid
- **Desktop (1024px+)**: Multi-column layouts

### 2. Navbar Component (`navbar.html`)

The `navbar.html` component is a professional, responsive navigation bar for the HashInsight platform. It provides:

- Role-based dynamic menu display
- Multi-language support (Chinese/English)
- Mobile-responsive design
- User authentication status display
- Professional dark theme with gold accents

### 2. Footer Component (`footer.html`)

The `footer.html` component provides a standardized footer with legal links and contact information. It includes:

- Legal terms and privacy policy link
- Contact email link
- Copyright information
- Bilingual support (Chinese/English)
- Consistent styling with dark theme

### 3. Flash Messages Component (`flash_messages.html`)

The `flash_messages.html` component displays user notifications and alerts. It supports:

- Multiple message categories (success, warning, danger, info)
- Dismissible alerts
- Automatic styling based on message type
- Responsive layout

---

## Component Details

## Navbar Component

### Including in Templates

The navbar is automatically included in `base.html`:

```jinja
{% include 'components/navbar.html' %}
```

### Context Requirements

The navbar expects the following context variables (automatically provided by the `inject_navigation()` context processor in `app.py`):

- `navigation_menu` - Filtered navigation menu based on user role and language
- `user_menu` - User dropdown menu items
- `session['role']` - Current user role (owner/admin/mining_site/user/guest)
- `session['language']` - Current language (zh/en)
- `session['user_id']` or `session['email']` - User authentication status
- `session['username']` - User display name

## Features

### 1. Role-Based Navigation

The navbar automatically filters menu items based on the user's role:

- **Owner**: Full access to all features including system management
- **Admin**: Access to CRM, user management, analytics, and Web3 features
- **Mining Site**: Access to batch calculator, network analysis, miner management
- **User**: Access to basic calculator and treasury management
- **Guest**: Public pages only

### 2. Language Switching

Language toggle buttons allow users to switch between Chinese and English:

```html
<div class="language-toggle">
    <a href="/?lang=zh" class="btn">中文</a>
    <a href="/?lang=en" class="btn">EN</a>
</div>
```

### 3. Mobile Responsive

The navbar collapses into a hamburger menu on screens smaller than 992px:

- Collapsible navigation with Bootstrap's collapse component
- Touch-friendly mobile menu
- Optimized spacing for small screens

### 4. User Menu

When authenticated, displays:
- User avatar icon
- Username (from session)
- Role badge with color coding
- Dropdown menu with:
  - My Dashboard
  - Profile
  - Logout

When not authenticated, displays:
- Login button

### 5. Current Page Highlighting

Active navigation items are highlighted with:
- Gold background color
- Bottom border indicator
- Visual feedback for current location

## Styling

### Color Scheme

- **Navbar Background**: `#2c3e50` (RGB 44,62,80)
- **Gold Accent**: `#f39c12` (RGB 243,156,18)
- **Hover Background**: `#34495e`
- **Text Color**: `#ecf0f1`

### Role Badge Colors

- **Owner**: Red `#e74c3c`
- **Admin**: Purple `#9b59b6`
- **Mining Site**: Blue `#3498db`
- **User**: Green `#2ecc71`
- **Guest**: Gray `#95a5a6`

### Responsive Breakpoints

- **Mobile**: < 992px (collapsible menu)
- **Tablet**: 992px - 1199px (compact spacing)
- **Desktop**: ≥ 1200px (full layout, max-width 1400px)

## Customization

### Adding New Menu Items

Menu items are defined in `navigation_config.py`. To add new items:

1. Edit `NAVIGATION_MENU` in `navigation_config.py`
2. Set appropriate `min_role` for access control
3. Add translations for both `zh` and `en`

Example:

```python
{
    'id': 'new_feature',
    'name': {
        'zh': '新功能',
        'en': 'New Feature'
    },
    'url': '/new-feature',
    'icon': 'bi-star',
    'min_role': 'user',
    'order': 10
}
```

### Modifying Styles

Styles are embedded in the navbar component. To customize:

1. Edit CSS variables in `:root` selector
2. Modify component-specific styles
3. Adjust responsive breakpoints in media queries

## JavaScript Functionality

The navbar includes JavaScript for:

1. **Active Link Highlighting**: Automatically highlights the current page
2. **Mobile Menu Auto-Close**: Closes mobile menu when a link is clicked
3. **Dropdown Support**: Bootstrap dropdown functionality

## Integration with Flask

The navbar integrates with Flask through:

1. **Context Processor** (`app.py`):
```python
@app.context_processor
def inject_navigation():
    from navigation_config import get_user_navigation, get_user_menu
    
    current_role = session.get('role', 'guest')
    current_lang = session.get('language', 'zh')
    
    return dict(
        navigation_menu=get_user_navigation(current_role, current_lang),
        user_menu=get_user_menu(current_role, current_lang)
    )
```

2. **Session Management**: Uses Flask session for user state
3. **URL Generation**: Uses Flask's `url_for()` for dynamic URLs

## Browser Compatibility

Tested and working on:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Accessibility

- Semantic HTML5 structure
- ARIA labels for navigation
- Keyboard navigation support
- Screen reader friendly

## Troubleshooting

### Menu Not Showing

1. Check session role: `session.get('role', 'guest')`
2. Verify navigation_config.py imports correctly
3. Ensure context processor is registered

### Language Not Switching

1. Verify session['language'] is set
2. Check URL parameters for `lang=zh` or `lang=en`
3. Ensure translations exist in navigation_config.py

### Mobile Menu Not Working

1. Verify Bootstrap JS is loaded
2. Check console for JavaScript errors
3. Ensure data-bs-toggle attributes are correct

## Performance

- CSS is embedded (no additional HTTP requests)
- Minimal JavaScript footprint
- Optimized for fast rendering
- Cached navigation data through context processor

---

## Footer Component

### Including in Templates

The footer is automatically included in `base.html`:

```jinja
{% include 'components/footer.html' %}
```

### Features

1. **Legal Links**: Direct links to Terms of Use and Privacy Policy
2. **Contact Information**: Email link for user inquiries
3. **Copyright Notice**: Displays copyright and last update date
4. **Bilingual Support**: Automatically switches between Chinese and English based on `session['language']`

### Context Requirements

- `session['language']` - Current language (zh/en)
- `url_for('legal_terms')` - URL for legal terms page

### Usage Example

The footer is included automatically in the base template and will appear on all pages that extend `base.html`. No additional configuration needed.

### Customization

To modify the footer content:

1. Edit `templates/components/footer.html`
2. Update the email address or legal links
3. Modify the copyright year or last updated date

### Styling

The footer uses Bootstrap classes:
- `py-4 my-4`: Padding and margin
- `border-top`: Top border separator
- `bg-dark`: Dark background
- `btn-outline-warning`: Warning-colored outline buttons
- `btn-outline-info`: Info-colored outline buttons

---

## Flash Messages Component

### Including in Templates

Flash messages are automatically included in `base.html`:

```jinja
{% include 'components/flash_messages.html' %}
```

### Features

1. **Multiple Categories**: Supports success, warning, danger, info message types
2. **Dismissible**: Users can close messages with the × button
3. **Auto-styled**: Bootstrap alert classes apply automatically based on category
4. **Responsive**: Works on all screen sizes

### Message Categories

The component supports the following Flask flash message categories:

- `success` - Green alerts for successful operations
- `warning` - Yellow alerts for warnings
- `danger` - Red alerts for errors
- `info` - Blue alerts for informational messages

### Usage in Flask Routes

```python
from flask import flash

# Success message
flash('操作成功！', 'success')

# Warning message
flash('请注意：数据即将过期', 'warning')

# Error message
flash('发生错误，请重试', 'danger')

# Info message
flash('新功能已上线', 'info')
```

### Customization

To modify the flash messages display:

1. Edit `templates/components/flash_messages.html`
2. Adjust Bootstrap alert classes
3. Modify the layout structure

### Technical Details

- Uses Flask's `get_flashed_messages(with_categories=true)` function
- Automatically handles message iteration
- Bootstrap 5 alert component with dismiss functionality
- No JavaScript required (uses Bootstrap's built-in dismiss)

---

## General Guidelines

### Component Development

When creating new components:

1. **Bilingual Support**: Always use `session.get('language', 'zh')` for language detection
2. **Independence**: Components should be self-contained and reusable
3. **Consistency**: Follow existing design patterns and naming conventions
4. **Responsive**: Ensure mobile-friendly design
5. **Documentation**: Update this README when adding new components

### Best Practices

- Use `{% include %}` for static components
- Use `{% extends %}` for page templates
- Keep components small and focused on a single purpose
- Use Bootstrap classes for consistent styling
- Test components on multiple screen sizes

### File Naming Convention

- Use lowercase with underscores: `flash_messages.html`
- Name should describe the component's function clearly
- Keep names concise but descriptive

### Adding New Components

To add a new component:

1. Create the component file in `templates/components/`
2. Document it in this README
3. Include it in the appropriate template using `{% include %}`
4. Test across different pages and screen sizes
5. Ensure bilingual support is implemented
