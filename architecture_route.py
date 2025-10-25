"""
Architecture Diagram Route
系统架构图路由
"""
from flask import render_template, session
from app import app

@app.route('/architecture')
def architecture_diagram():
    """Display the system architecture diagram / 显示系统架构图"""
    # Get language from session
    current_lang = session.get('language', 'zh')
    
    return render_template(
        'architecture_diagram.html',
        current_lang=current_lang,
        t=lambda key: key  # Simple passthrough since we're using inline translations
    )

@app.route('/system-relationships')
def system_relationships():
    """Display the system relationship diagram / 显示系统关系图"""
    # Get language from session
    current_lang = session.get('language', 'zh')
    
    return render_template(
        'system_relationship_diagram.html',
        current_lang=current_lang,
        t=lambda key: key
    )

@app.route('/system-architecture-complete')
def system_architecture_complete():
    """Display the complete system architecture / 显示完整系统架构"""
    current_lang = session.get('language', 'zh')
    
    return render_template(
        'system_architecture_complete.html',
        current_lang=current_lang,
        t=lambda key: key  # Simple passthrough since we're using inline translations
    )