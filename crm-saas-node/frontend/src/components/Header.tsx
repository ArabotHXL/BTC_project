import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import { LanguageSwitcher } from './LanguageSwitcher';
import { Button } from './ui/Button';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();

  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };

  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <h2 className="text-xl font-semibold text-white">
            {t('app.name')}
          </h2>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-gray-300">{user?.email}</span>
          <LanguageSwitcher />
          <Button variant="secondary" onClick={handleLogout}>
            {t('nav.logout')}
          </Button>
        </div>
      </div>
    </header>
  );
};
