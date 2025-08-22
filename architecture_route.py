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