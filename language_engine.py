"""
Enhanced Language Engine - Version 2.0
支持动态翻译、上下文感知、变量插值和多语言格式化

Features:
- Context-aware translations
- Variable interpolation
- Number/Currency/Date formatting
- Pluralization support
- Caching for performance
- Fallback mechanisms
"""

import re
import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
try:
    from translations import TRANSLATIONS
except ImportError:
    # Fallback minimal translations
    TRANSLATIONS = {
        'zh': {'error': '错误'},
        'en': {'error': 'Error'}
    }

logger = logging.getLogger(__name__)

class LanguageEngine:
    """
    Advanced Language Engine with context awareness, variable interpolation,
    and dynamic translation capabilities
    """
    
    def __init__(self):
        self.translations = TRANSLATIONS
        self.default_lang = 'en'  # 默认英文
        self.current_lang = 'en'
        self.context_cache = {}
        self.format_cache = {}
        
        logger.info("Language Engine initialized with enhanced features")
        
    def set_language(self, lang: str):
        """设置当前语言"""
        old_lang = self.current_lang
        if lang in ['zh', 'en']:
            self.current_lang = lang
        else:
            self.current_lang = self.default_lang
            
        if old_lang != self.current_lang:
            logger.info(f"Language switched from {old_lang} to {self.current_lang}")
            # Clear cache when language changes
            self.context_cache.clear()
    
    def get_language(self) -> str:
        """获取当前语言"""
        return self.current_lang
    
    def translate(self, key: str, lang: Optional[str] = None, context: Optional[str] = None, **kwargs) -> str:
        """
        Enhanced translation with variable interpolation and context awareness
        
        Args:
            key: Translation key
            lang: Target language (zh/en)
            context: Context for specialized translations
            **kwargs: Variables for interpolation
        
        Returns:
            Translated and formatted string
        """
        target_lang = lang or self.current_lang
        
        # Check cache first
        cache_key = f"{key}_{target_lang}_{context}"
        if cache_key in self.context_cache and not kwargs:
            return self.context_cache[cache_key]
        
        # Get translation from dictionary
        if target_lang in self.translations and key in self.translations[target_lang]:
            text = self.translations[target_lang][key]
        elif self.default_lang in self.translations and key in self.translations[self.default_lang]:
            # Fallback to default language
            text = self.translations[self.default_lang][key]
            logger.warning(f"Translation not found for '{key}' in '{target_lang}', using default")
        else:
            # Ultimate fallback: return the key itself
            text = key
            logger.warning(f"Translation not found for '{key}', returning key")
        
        # Variable interpolation with safe formatting
        if kwargs:
            try:
                text = self._safe_format(text, **kwargs)
            except Exception as e:
                logger.error(f"Error formatting translation '{key}': {e}")
                # Return text without formatting if it fails
                pass
        
        # Cache the result if no variables were used
        if not kwargs:
            self.context_cache[cache_key] = text
        
        return text
    
    def _safe_format(self, text: str, **kwargs) -> str:
        """安全的字符串格式化，避免KeyError"""
        try:
            # First try standard .format()
            return text.format(**kwargs)
        except KeyError as e:
            # If a key is missing, try to provide a fallback
            logger.warning(f"Missing format key {e} in text: {text}")
            # Return original text if formatting fails
            return text
        except Exception as e:
            logger.error(f"Unexpected error in string formatting: {e}")
            return text
    
    def get_formatted_number(self, number: Union[int, float], lang: Optional[str] = None, decimal_places: int = 2) -> str:
        """格式化数字显示"""
        target_lang = lang or self.current_lang
        
        if number is None:
            return "0"
        
        try:
            if isinstance(number, (int, float)):
                if isinstance(number, float) and decimal_places > 0:
                    return f"{number:,.{decimal_places}f}"
                else:
                    return f"{int(number):,}"
            else:
                return str(number)
        except (ValueError, TypeError):
            logger.error(f"Error formatting number: {number}")
            return str(number)
    
    def get_formatted_currency(self, amount: Union[int, float], currency: str = "USD", lang: Optional[str] = None) -> str:
        """格式化货币显示"""
        target_lang = lang or self.current_lang
        
        if amount is None:
            amount = 0
            
        try:
            if currency.upper() == "USD":
                formatted_amount = self.get_formatted_number(amount, lang, 2)
                return f"${formatted_amount}"
            elif currency.upper() == "BTC":
                formatted_amount = self.get_formatted_number(amount, lang, 8)
                return f"{formatted_amount} BTC"
            elif currency.upper() == "SATS":
                formatted_amount = self.get_formatted_number(amount, lang, 0)
                if target_lang == 'zh':
                    return f"{formatted_amount} 聪"
                else:
                    return f"{formatted_amount} sats"
            else:
                formatted_amount = self.get_formatted_number(amount, lang, 2)
                return f"{formatted_amount} {currency}"
        except Exception as e:
            logger.error(f"Error formatting currency {amount} {currency}: {e}")
            return f"{amount} {currency}"
    
    def get_formatted_date(self, date: Union[datetime, str], lang: Optional[str] = None, format_type: str = "default") -> str:
        """格式化日期显示"""
        target_lang = lang or self.current_lang
        
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except ValueError:
                return str(date)
        
        if not isinstance(date, datetime):
            return str(date)
        
        try:
            if format_type == "short":
                if target_lang == 'zh':
                    return date.strftime('%m/%d %H:%M')
                else:
                    return date.strftime('%m/%d %H:%M')
            elif format_type == "date_only":
                if target_lang == 'zh':
                    return date.strftime('%Y年%m月%d日')
                else:
                    return date.strftime('%Y-%m-%d')
            else:  # default
                if target_lang == 'zh':
                    return date.strftime('%Y年%m月%d日 %H:%M')
                else:
                    return date.strftime('%Y-%m-%d %H:%M')
        except Exception as e:
            logger.error(f"Error formatting date {date}: {e}")
            return str(date)
    
    def get_formatted_percentage(self, value: Union[int, float], lang: Optional[str] = None, decimal_places: int = 2) -> str:
        """格式化百分比显示"""
        if value is None:
            return "0%"
            
        try:
            formatted = f"{float(value):.{decimal_places}f}%"
            return formatted
        except (ValueError, TypeError):
            logger.error(f"Error formatting percentage: {value}")
            return f"{value}%"
    
    def pluralize(self, key: str, count: int, lang: Optional[str] = None, **kwargs) -> str:
        """处理复数形式"""
        target_lang = lang or self.current_lang
        
        # Add count to kwargs for interpolation
        kwargs['count'] = count
        
        if target_lang == 'zh':
            # 中文没有复数形式，直接返回翻译
            return self.translate(key, lang, **kwargs)
        else:
            # 英文处理复数
            if count == 1:
                singular_key = f"{key}_singular"
                if singular_key in self.translations.get(target_lang, {}):
                    return self.translate(singular_key, lang, **kwargs)
            
            plural_key = f"{key}_plural"
            if plural_key in self.translations.get(target_lang, {}):
                return self.translate(plural_key, lang, **kwargs)
            
            # Fallback to regular translation
            return self.translate(key, lang, **kwargs)
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return list(self.translations.keys())
    
    def is_language_supported(self, lang: str) -> bool:
        """检查是否支持指定语言"""
        return lang in self.translations
    
    def get_language_name(self, lang_code: str, display_lang: Optional[str] = None) -> str:
        """获取语言的显示名称"""
        display_lang = display_lang or self.current_lang
        
        language_names = {
            'zh': {'zh': '中文', 'en': 'Chinese'},
            'en': {'zh': '英文', 'en': 'English'}
        }
        
        return language_names.get(lang_code, {}).get(display_lang, lang_code)
    
    def clear_cache(self):
        """清除所有缓存"""
        self.context_cache.clear()
        self.format_cache.clear()
        logger.info("Language engine cache cleared")

# Create global instance
language_engine = LanguageEngine()

def get_translation(key: str, to_lang: Optional[str] = None, **kwargs) -> str:
    """
    Global translation function for backward compatibility
    
    Args:
        key: Translation key
        to_lang: Target language
        **kwargs: Variables for interpolation
    
    Returns:
        Translated string
    """
    return language_engine.translate(key, to_lang, **kwargs)

def set_language(lang: str):
    """设置全局语言"""
    language_engine.set_language(lang)

def get_current_language() -> str:
    """获取当前语言"""
    return language_engine.get_language()

# Convenient formatting functions
def format_currency(amount: Union[int, float], currency: str = "USD", lang: Optional[str] = None) -> str:
    """格式化货币"""
    return language_engine.get_formatted_currency(amount, currency, lang)

def format_number(number: Union[int, float], lang: Optional[str] = None, decimal_places: int = 2) -> str:
    """格式化数字"""
    return language_engine.get_formatted_number(number, lang, decimal_places)

def format_date(date: Union[datetime, str], lang: Optional[str] = None, format_type: str = "default") -> str:
    """格式化日期"""
    return language_engine.get_formatted_date(date, lang, format_type)

def format_percentage(value: Union[int, float], lang: Optional[str] = None, decimal_places: int = 2) -> str:
    """格式化百分比"""
    return language_engine.get_formatted_percentage(value, lang, decimal_places)

# Template helper functions
def create_template_helpers():
    """创建模板辅助函数"""
    return {
        't': get_translation,
        'tr': get_translation,  # Short alias
        'format_currency': format_currency,
        'format_number': format_number,
        'format_date': format_date,
        'format_percentage': format_percentage,
        'current_lang': get_current_language,
        'lang_name': language_engine.get_language_name
    }

logger.info("Enhanced Language Engine v2.0 loaded successfully")