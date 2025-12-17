import React from 'react';
import { useTranslation } from 'react-i18next';

export const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'zh' : 'en';
    i18n.changeLanguage(newLang);
    localStorage.setItem('language', newLang);
  };

  return (
    <button
      onClick={toggleLanguage}
      className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-gray-300 transition-colors"
    >
      {i18n.language === 'en' ? '中文' : 'EN'}
    </button>
  );
};
