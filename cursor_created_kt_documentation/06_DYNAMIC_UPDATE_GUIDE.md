# Dynamic Documentation Update Guide

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Purpose:** Guide for keeping documentation synchronized with code changes

---

## Overview

This guide explains how to keep the documentation in `cursor_created_kt_documentation/` folder synchronized with actual code changes. The documentation should be updated whenever:

1. New routes are added
2. New blueprints are registered
3. Database models change
4. New modules are added
5. API endpoints change
6. Business logic changes

---

## Documentation Structure

```
cursor_created_kt_documentation/
├── 00_EXECUTIVE_SUMMARY.md          # Non-technical overview
├── 01_HIGH_LEVEL_ARCHITECTURE.md    # Business-focused architecture
├── 03_TECHNICAL_ARCHITECTURE.md     # Developer-focused architecture
├── 04_LOW_LEVEL_IMPLEMENTATION.md   # Architect-level details
├── 05_ROUTE_TO_PAGE_MAPPING.md     # Complete route mapping
└── 06_DYNAMIC_UPDATE_GUIDE.md        # This file
```

---

## Update Checklist

### When Adding a New Route

- [ ] Update `05_ROUTE_TO_PAGE_MAPPING.md`
  - Add route to appropriate section
  - Document template file
  - Document access level
  - Document HTTP method (for APIs)

- [ ] Update `03_TECHNICAL_ARCHITECTURE.md`
  - Add to "Route Organization" section
  - Add to "Key API Endpoints" if it's an API
  - Update blueprint documentation if new blueprint

- [ ] Update `01_HIGH_LEVEL_ARCHITECTURE.md`
  - Add to module's "Key Routes" section
  - Update module description if needed

### When Adding a New Blueprint

- [ ] Update `03_TECHNICAL_ARCHITECTURE.md`
  - Add to "Flask Blueprint Architecture" section
  - Document URL prefix
  - Document registration location in app.py
  - Update blueprint count

- [ ] Update `01_HIGH_LEVEL_ARCHITECTURE.md`
  - Add new module section if it's a new module
  - Update module list

- [ ] Update `05_ROUTE_TO_PAGE_MAPPING.md`
  - Add all routes from new blueprint
  - Document blueprint name

### When Adding a New Database Model

- [ ] Update `03_TECHNICAL_ARCHITECTURE.md`
  - Add to "Database Models" section
  - Document key fields
  - Document relationships

- [ ] Update `01_HIGH_LEVEL_ARCHITECTURE.md`
  - Add to "Data Architecture" section
  - Update table count

### When Adding a New Module

- [ ] Update `01_HIGH_LEVEL_ARCHITECTURE.md`
  - Add new "Core Business Modules" section
  - Document purpose, features, data models, routes
  - Add to module list

- [ ] Update `03_TECHNICAL_ARCHITECTURE.md`
  - Add to "Application Structure"
  - Document module location
  - Add service layer documentation

- [ ] Update `00_EXECUTIVE_SUMMARY.md`
  - Add to "Platform Capabilities" if user-facing
  - Add use case if applicable

### When Changing API Endpoints

- [ ] Update `05_ROUTE_TO_PAGE_MAPPING.md`
  - Update route documentation
  - Update request/response examples if changed

- [ ] Update `03_TECHNICAL_ARCHITECTURE.md`
  - Update "Key API Endpoints" section
  - Update API design examples

### When Adding External Integrations

- [ ] Update `01_HIGH_LEVEL_ARCHITECTURE.md`
  - Add to "External Integrations" section
  - Document purpose and configuration

- [ ] Update `03_TECHNICAL_ARCHITECTURE.md`
  - Add to "External Integrations" section
  - Document API usage examples

---

## Automated Update Scripts

### Script 1: Extract Routes from app.py

```python
#!/usr/bin/env python3
"""
Extract all routes from app.py and generate route documentation
"""
import re
import sys

def extract_routes(app_file):
    routes = []
    with open(app_file, 'r') as f:
        content = f.read()
        
    # Find all @app.route and @blueprint.route decorators
    pattern = r'@(?:app|.*_bp)\.route\([\'"]([^\'"]+)[\'"]'
    matches = re.findall(pattern, content)
    
    for route in matches:
        routes.append(route)
    
    return sorted(set(routes))

if __name__ == '__main__':
    routes = extract_routes('app.py')
    print("Found routes:")
    for route in routes:
        print(f"  - {route}")
```

### Script 2: Extract Blueprints

```python
#!/usr/bin/env python3
"""
Extract all blueprint registrations from app.py
"""
import re

def extract_blueprints(app_file):
    blueprints = []
    with open(app_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if 'register_blueprint' in line:
                # Extract blueprint name and URL prefix
                match = re.search(r'register_blueprint\((\w+)(?:,\s*url_prefix=[\'"]([^\'"]+)[\'"])?\)', line)
                if match:
                    bp_name = match.group(1)
                    url_prefix = match.group(2) if match.group(2) else 'None'
                    blueprints.append({
                        'name': bp_name,
                        'prefix': url_prefix,
                        'line': line_num
                    })
    return blueprints

if __name__ == '__main__':
    blueprints = extract_blueprints('app.py')
    print("Found blueprints:")
    for bp in blueprints:
        print(f"  - {bp['name']} (prefix: {bp['prefix']}, line: {bp['line']})")
```

### Script 3: Extract Database Models

```python
#!/usr/bin/env python3
"""
Extract all database models from models.py
"""
import ast
import sys

def extract_models(models_file):
    models = []
    with open(models_file, 'r') as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it inherits from db.Model
            for base in node.bases:
                if isinstance(base, ast.Attribute):
                    if base.attr == 'Model':
                        models.append(node.name)
    
    return models

if __name__ == '__main__':
    models = extract_models('models.py')
    print("Found models:")
    for model in models:
        print(f"  - {model}")
```

---

## Manual Update Process

### Step 1: Identify Changes

1. Review git diff or recent commits
2. Identify what changed:
   - New files added?
   - Routes modified?
   - Models added?
   - Blueprints registered?

### Step 2: Update Relevant Documentation

1. Start with most specific document (route mapping)
2. Work up to more general documents (architecture)
3. Update executive summary last (if user-facing)

### Step 3: Verify Accuracy

1. Check that all new routes are documented
2. Verify template names match actual files
3. Confirm access levels are correct
4. Test that examples work

### Step 4: Update Version and Date

1. Update "Last Updated" date in document header
2. Increment version if major changes
3. Add changelog entry if significant

---

## Documentation Standards

### Route Documentation Format

```markdown
| Route | Template | Description | Access Level |
|-------|----------|-------------|--------------|
| `/route/path` | `template.html` | Description | Role required |
```

### API Documentation Format

```markdown
| Route | Method | Description | Auth Required |
|-------|--------|-------------|---------------|
| `/api/endpoint` | POST | Description | Yes/No |
```

### Blueprint Documentation Format

```markdown
| Blueprint | URL Prefix | File | Purpose |
|-----------|------------|------|---------|
| `blueprint_name` | `/prefix` | `file.py` | Purpose |
```

---

## Version Control

### Git Workflow

1. **Make code changes** in feature branch
2. **Update documentation** in same commit or follow-up commit
3. **Commit message format:**
   ```
   feat: Add new calculator route
   
   - Add /api/calculate-v2 endpoint
   - Update route mapping documentation
   - Update technical architecture docs
   ```

### Documentation-Only Commits

If updating documentation separately:

```
docs: Update route mapping for new CRM features

- Add /crm/reports route
- Update CRM module documentation
- Fix outdated blueprint references
```

---

## Regular Maintenance

### Monthly Review

1. Review all routes in app.py
2. Verify all are documented
3. Check for deprecated routes
4. Update access levels if changed

### Quarterly Review

1. Review architecture documents
2. Update technology stack versions
3. Review external integrations
4. Update performance metrics

### After Major Releases

1. Full documentation audit
2. Update all version numbers
3. Review and update all examples
4. Verify all links work

---

## Tools and Resources

### Useful Commands

```bash
# Find all routes
grep -r "@.*\.route" app.py routes/ modules/

# Find all blueprints
grep -r "register_blueprint" app.py

# Find all templates
find templates/ -name "*.html"

# Count routes
grep -c "@.*\.route" app.py
```

### Documentation Tools

- **Markdown Linter:** Check markdown syntax
- **Link Checker:** Verify internal links
- **Spell Checker:** Check spelling
- **Table Formatter:** Format tables consistently

---

## Common Issues and Solutions

### Issue: Route not documented

**Solution:** Add to `05_ROUTE_TO_PAGE_MAPPING.md` immediately

### Issue: Blueprint count mismatch

**Solution:** Run blueprint extraction script and update count

### Issue: Outdated examples

**Solution:** Test examples and update with actual API responses

### Issue: Broken internal links

**Solution:** Use link checker tool and fix all broken links

---

## Best Practices

1. **Update as you code** - Don't wait until the end
2. **Test examples** - Ensure all code examples work
3. **Keep it simple** - Clear, concise documentation
4. **Version control** - Commit documentation with code
5. **Regular reviews** - Schedule periodic documentation audits

---

## Next Steps

- Review current documentation for accuracy
- Set up automated extraction scripts
- Schedule regular documentation reviews
- Train team on documentation standards

---

**Remember:** Good documentation is a living document that evolves with the codebase. Keep it updated, and it will serve as a valuable resource for the entire team.
