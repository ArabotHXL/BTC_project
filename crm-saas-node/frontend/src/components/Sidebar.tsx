import React from 'react';
import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export const Sidebar: React.FC = () => {
  const { t } = useTranslation();

  const navItems = [
    { path: '/', label: t('nav.dashboard'), icon: '📊' },
    { path: '/leads', label: t('nav.leads'), icon: '👥' },
    { path: '/deals', label: t('nav.deals'), icon: '💼' },
    { path: '/invoices', label: t('nav.invoices'), icon: '🧾' },
    { path: '/assets', label: t('nav.assets'), icon: '🏗️' },
  ];

  return (
    <aside className="bg-gray-800 w-64 min-h-screen border-r border-gray-700">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-amber-500 mb-8">CRM</h1>
        <nav className="space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-amber-500 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`
              }
            >
              <span className="text-xl">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
};
