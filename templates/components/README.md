# Navbar Component Documentation

## Overview

The `navbar.html` component is a professional, responsive navigation bar for the HashInsight platform. It provides:

- Role-based dynamic menu display
- Multi-language support (Chinese/English)
- Mobile-responsive design
- User authentication status display
- Professional dark theme with gold accents

## Usage

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
