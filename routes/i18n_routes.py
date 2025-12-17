"""
HashInsight Enterprise - i18n (Internationalization) Routes
国际化路由

提供以下端点:
- /set_language - 设置界面语言
- /api/i18n/translations - 获取翻译数据
- /api/i18n/set-language - AJAX方式设置语言
"""

import logging
from datetime import datetime
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from flask import Blueprint, request, session, g, redirect, url_for, jsonify

logger = logging.getLogger(__name__)

i18n_bp = Blueprint('i18n', __name__)

_translation_data_cache = {
    'en': None,
    'zh': None
}
_translation_cache_time = {
    'en': None,
    'zh': None
}
TRANSLATION_CACHE_TTL = 300


def _is_safe_url(url):
    """验证URL是否安全（同站点或相对路径）"""
    if not url:
        return False
    parsed = urlparse(url)
    if not parsed.netloc:
        return True
    return (
        parsed.netloc == request.host or
        parsed.netloc.endswith('.replit.dev') or
        parsed.netloc.endswith('.repl.co')
    )


@i18n_bp.route('/set_language')
def set_language():
    """设置界面语言"""
    lang = request.args.get('lang', 'zh')
    if lang not in ['zh', 'en']:
        lang = 'zh'
    
    session.pop('language', None)
    session['language'] = lang
    session.modified = True
    g.language = lang
    
    return_url = request.args.get('return_url')
    
    if not _is_safe_url(return_url):
        return_url = None
    
    if not return_url:
        referrer = request.referrer
        if _is_safe_url(referrer):
            return_url = referrer
    
    if not return_url:
        return_url = url_for('index')
    
    parsed = urlparse(return_url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    query_params.pop('lang', None)
    
    new_query = urlencode(query_params, doseq=True)
    return_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    return redirect(return_url)


@i18n_bp.route('/api/i18n/translations')
def api_get_translations():
    """获取翻译数据 (JSON格式) - 返回双语翻译以支持无刷新切换"""
    from translations import TRANSLATIONS
    current_lang = session.get('language', g.get('language', 'zh'))
    
    now = datetime.now()
    translations_both = {}
    
    for lang in ['en', 'zh']:
        cache_time = _translation_cache_time.get(lang)
        cached_data = _translation_data_cache.get(lang)
        
        if cached_data and cache_time and (now - cache_time).total_seconds() < TRANSLATION_CACHE_TTL:
            translations_both[lang] = cached_data
        else:
            translations_both[lang] = TRANSLATIONS.get(lang, {})
            _translation_data_cache[lang] = translations_both[lang]
            _translation_cache_time[lang] = now
    
    return jsonify({
        'success': True,
        'current_lang': current_lang,
        'translations': translations_both
    })


@i18n_bp.route('/api/i18n/set-language', methods=['POST'])
def api_set_language():
    """设置语言 (AJAX方式，无刷新)"""
    try:
        data = request.get_json() or {}
        lang = data.get('lang', 'zh')
        
        if lang not in ['zh', 'en']:
            lang = 'zh'
        
        session['language'] = lang
        session.modified = True
        g.language = lang
        
        try:
            from language_engine import language_engine
            if language_engine:
                language_engine.set_language(lang)
        except ImportError:
            pass
        
        return jsonify({
            'success': True,
            'lang': lang,
            'message': 'Language updated successfully'
        })
    except Exception as e:
        logger.error(f"Error setting language via API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
